"""Diagnostic coverage of observed replies, conditional on the public probe event."""
import hashlib
import json
import random
import subprocess

from ai_registry import build_policy
from feldmarschall import parse_square,square_name
from teacher_bot import TeacherBot
from train_ai_student import sample_world
from reply_teacher_cycle import BASE,plan


def profile(case):
    executable,_=build_policy(plan()['candidate'])
    bot=TeacherBot(executable.parent/'observer',executable.parent/'teacher',context=True,replies=3)
    try:
        army=case['input']['army'];observer=bot.observer
        observer.send('seed '+str(case['source']['seed']*2+army+1))
        observer.send('new '+('red','blue')[army]);observer.send('setup '+case['own_initial_setup'])
        for ply,event in enumerate(case['public_history']):
            if ply%2==army:
                observer.ask('go','move');observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
            observer.send(event)
        # This is a POST-PROBE diagnostic. Only that already public battle is
        # applied; the actual opponent reply is withheld until after prediction.
        observer.ask('go','move')
        observer.ask('played '+' '.join(map(square_name,case['recorded_probe'])),'playedok')
        observer.send(case['public_probe_event'])
        side,board,lost,shuttle=observer.ask('public','public').split();cells=list(bytes.fromhex(board))
        state=observer.ask('strategy','strategy')
        histories={sq:list(map(int,observer.ask('memory '+square_name(sq),'history').split()))
            for sq,c in enumerate(cells) if c<254 and bool(c&16)!=bool(army) and not c&32}
        rng=random.Random(int(hashlib.sha256(('reply-coverage:'+case['id']).encode()).hexdigest()[:8],16))
        predictions=[]
        for _ in range(8):
            world,weight=sample_world(cells,list(bytes.fromhex(lost)),histories,rng,army)
            output=subprocess.run([str(executable.parent/'teacher'),'--context','--strategic','--replies','3','--audit'],
                input=f'search {army} 4 {bytes(world).hex()} {shuttle} {state}\n',capture_output=True,text=True,check=True).stdout
            row=next(line.split() for line in output.splitlines() if line.startswith('replies '))
            entries=[list(map(int,row[i:i+4])) for i in range(2,len(row),4)]
            assert len(entries)==int(row[1])
            predictions.append(dict(sample_weight=weight,replies=entries))
        actual=list(map(parse_square,case['public_opponent_reply'].split()[1:3]))
        total=sum(p['sample_weight'] for p in predictions)
        parent=sum(p['sample_weight'] for p in predictions if p['replies'][0][:2]==actual)/total
        covered=sum(p['sample_weight'] for p in predictions if any(r[:2]==actual for r in p['replies']))/total
        return dict(id=case['id'],source=case['source'],actual_public_reply=actual,samples=predictions,
                    single_policy_coverage=parent,reply_set_coverage=covered)
    finally:bot.close()


def profiles():
    cases=[json.loads(line) for line in (BASE/'public-cases.jsonl').read_text().splitlines()]
    rows=[profile(case) for case in cases]
    return dict(scope='Post-probe public posterior, eight samples per case. The observed probe battle is conditioned on legitimately; the actual opponent reply is used only for scoring coverage after all predictions. This is hindsight diagnosis, never root input or strength evidence. Coverage is posterior sample mass containing the recorded reply, not its predicted choice probability.',
        positions=rows,single_policy_cases_covered=sum(r['single_policy_coverage']>0 for r in rows),
        reply_set_cases_covered=sum(r['reply_set_coverage']>0 for r in rows),
        total_reply_sets=sum(len(r['samples']) for r in rows),
        multiple_reply_sets=sum(len(s['replies'])>1 for r in rows for s in r['samples']))


if __name__=='__main__':
    report=profiles()
    (BASE/'reply-coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='positions'},indent=2))
