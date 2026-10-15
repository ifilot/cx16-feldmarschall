"""Historical public-root mechanism for count versus joint immediate gain.

Both comparisons reuse exactly the same eight frozen joint-model worlds and
continuations. This is a root diagnostic, never a playing-strength claim.
"""
from collections import Counter
import hashlib
import json
import time

from ai_registry import ROOT,build_policy
from campaign_belief_values import adjustments
from feldmarschall import square_name
from teacher_bot import TeacherBot
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


def run():
    folder=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon'
    destination=folder/'belief-capture-values-mechanism.json'
    assert not destination.exists(),'preserve original mechanism evidence'
    previous=folder/'quiescence-mechanism.json';document=json.loads(previous.read_text())
    source=ROOT/document['source'];targets={}
    for row in document['roots']:targets.setdefault((row['game'],row['army']),{})[row['ply']]=row
    model_path=ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json'
    executable,_=build_policy('teacher-context-v1-normal')
    bot=TeacherBot(executable.parent/'observer',executable.parent/'teacher',samples=8,depth=4,
        blend='correction',strategic=True,context=True,joint_belief_model=model_path)
    roots=[]
    def send(command):
        bot.joint_model.observe(command.split());bot.observer.send(command)
    try:
        with Tournament(source) as tournament:
            for game_id,army in sorted(targets):
                game=tournament.game(game_id);states,_=replay(game);events=public_events(game,states)
                seed=game['seed']*2+army+1;bot.rng.seed(seed)
                for command in ('new '+('red','blue')[army],'rules 0','difficulty normal',
                                'seed '+str(seed),'setup '+game[('red_setup','blue_setup')[army]]):send(command)
                selected=targets[(game_id,army)]
                for ply,event in enumerate(events[:max(selected)+1]):
                    if ply%2==army:
                        if ply in selected:
                            public=bot.observer.ask('public','public')
                            assert hashlib.sha256(public.encode()).hexdigest()==selected[ply]['public_sha256']
                            _,board,lost,_=public.split();cells=list(bytes.fromhex(board));lost=list(bytes.fromhex(lost))
                            histories={square:list(map(int,bot.observer.ask('memory '+square_name(square),'history').split()))
                                for square,cell in enumerate(cells) if cell<254 and bool(cell&16)!=bool(army) and not cell&32}
                            started=time.perf_counter();bot.choose();search_seconds=time.perf_counter()-started
                            report=bot.last_report;parent=tuple(report['parent'])
                            scores={tuple(value['move']):value['parent_score'] for value in report['values']}
                            base={tuple(value['move']):value['value'] for value in report['values']}
                            wins=[move for move,score in scores.items() if score>=30000]
                            results={}
                            for mode in ('counts','joint'):
                                before=bot.rng.getstate();started=time.perf_counter()
                                delta,detail=adjustments(cells,army,lost,histories,scores,bot.joint_model,mode)
                                seconds=time.perf_counter()-started
                                assert bot.rng.getstate()==before
                                choices={move:value+delta.get(move,0) for move,value in base.items()}
                                choice=parent if parent in wins else max(wins or choices,
                                    key=lambda move:(choices[move],move==parent,-move[0],-move[1]))
                                results[mode]=dict(selected=choice,changed_from_joint_sampler_only=choice!=tuple(report['selected']),
                                                   seconds=seconds,detail=detail)
                            roots.append(dict(game=game_id,army=army,family=game['family'],ply=ply,
                                search_seconds=search_seconds,sampler_only_selected=report['selected'],results=results))
                            print('Historical belief-value root',len(roots),'/ 140',flush=True)
                        else:bot.observer.ask('go','move')
                        bot.observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
                    send(event)
    finally:bot.close()
    summary=dict(roots=len(roots),families=dict(Counter(row['family'] for row in roots)),
        roots_with_hidden_capture=sum(row['results']['joint']['detail']['hidden_capture_actions']>0 for row in roots),
        count_vs_joint_decision_changes=sum(row['results']['counts']['selected']!=row['results']['joint']['selected'] for row in roots),
        modes={mode:dict(changed_from_joint_sampler_only=sum(row['results'][mode]['changed_from_joint_sampler_only'] for row in roots),
            hidden_capture_actions=sum(row['results'][mode]['detail']['hidden_capture_actions'] for row in roots),
            changed_capture_values=sum(row['results'][mode]['detail']['changed_captures'] for row in roots),
            total_seconds=sum(row['results'][mode]['seconds'] for row in roots)) for mode in ('counts','joint')},
        total_search_seconds=sum(row['search_seconds'] for row in roots))
    result=dict(kind='historical-public-belief-to-capture-value-mechanism',strength_evidence=False,
        model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_roots_sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),
        sampled_worlds='Same frozen joint model, eight worlds, four plies; both root gains share all continuations.',
        analytic_root_marginals='Exact setup-style Flag/Bomb marginals, exchangeable remaining mobile ranks; encounter behavior factors omitted in both root controls.',
        caveat='Additive expected-capture-gain adjustment only: native goal selection, danger, mission/student terms and conditional near-Flag bonus are held fixed.',
        summary=summary,roots=roots)
    destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':run()
