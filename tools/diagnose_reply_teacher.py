"""Compare frozen teachers on public roots, without importing recorded futures."""
import hashlib
import json
from pathlib import Path
import time

from ai_registry import ROOT, build_policy
from teacher_bot import TeacherBot
from reply_teacher_cycle import BASE, plan
from train_teacher_student import canonical_shuttle


def decide(case,identity,replies=None):
    executable,receipt=build_policy(identity)
    bot=TeacherBot(executable.parent/'observer',executable.parent/'teacher',samples=8,depth=4,
                   blend='correction',strategic=True,context=True,replies=replies)
    try:
        army=case['input']['army'];seed=case['source']['seed']*2+army+1
        bot.observer.send('seed '+str(seed));bot.observer.send('new '+('red','blue')[army])
        bot.observer.send('setup '+case['own_initial_setup'])
        for ply,event in enumerate(case['public_history']):
            if ply%2==army:
                bot.observer.ask('go','move');bot.observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
            bot.observer.send(event)
        side,board,lost,shuttle=bot.observer.ask('public','public').split()
        assert int(side)==army and board==case['input']['board_hex'] and lost==case['input']['enemy_lost_hex']
        expected=bytes(case['input']['shuttle'][str(a)][i] if case['input']['shuttle'][str(a)][i] is not None else 255 for i in range(3) for a in (0,1)).hex()
        assert canonical_shuttle(shuttle)==canonical_shuttle(expected)
        state=bot.observer.ask('strategy','strategy')
        bot.rng.seed(int(hashlib.sha256(('reply-review:'+case['id']).encode()).hexdigest()[:8],16))
        started=time.perf_counter();selected=bot.choose();elapsed=time.perf_counter()-started
        assert list(selected) in case['legal_moves']
        cells=bytes.fromhex(board);target=cells[selected[1]]
        kind='quiet' if target>=254 else 'attack-disclosed' if target&32 else 'scout-probe' if cells[selected[0]]&15==8 else 'attack-concealed'
        report=bot.last_report
        return dict(selected=list(selected),kind=kind,recorded_probe_selected=list(selected)==case['recorded_probe'],
            root_context_sha256=hashlib.sha256(bytes.fromhex(state)).hexdigest(),nodes=report['nodes'],
            effective_samples=report['effective_samples'],values=report['values'],elapsed_seconds=elapsed,
            policy_source_sha256=receipt['policy']['source_sha256'])
    finally:bot.close()


def diagnose():
    config=plan();cases=[json.loads(line) for line in (BASE/'public-cases.jsonl').read_text().splitlines()]
    rows=[]
    for index,case in enumerate(cases,1):
        public={key:case[key] for key in ('id','input','source','public_history','own_initial_setup','legal_moves','recorded_probe')}
        candidate=decide(public,config['candidate'],3);control=decide(public,config['control'])
        assert candidate['root_context_sha256']==control['root_context_sha256']
        rows.append(dict(id=case['id'],source=case['source'],recorded_probe=case['recorded_probe'],candidate=candidate,control=control))
        print(f'{index}/18 public cases',flush=True)
    return dict(scope='Forced public histories; identical own strategic contexts and sampled-world RNG seeds. Recorded future replies/outcomes are never passed to decide(). Changing a diagnostic move does not establish a stronger continuation.',
        cases_sha256=hashlib.sha256((BASE/'public-cases.jsonl').read_bytes()).hexdigest(),positions=rows,
        changed_decisions=sum(r['candidate']['selected']!=r['control']['selected'] for r in rows),
        candidate_recorded_probes=sum(r['candidate']['recorded_probe_selected'] for r in rows),
        control_recorded_probes=sum(r['control']['recorded_probe_selected'] for r in rows),
        candidate_nodes=sum(r['candidate']['nodes'] for r in rows),control_nodes=sum(r['control']['nodes'] for r in rows))


if __name__=='__main__':
    result=diagnose()
    (BASE/'diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='positions'},indent=2))
