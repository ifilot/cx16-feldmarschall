"""Is an imaginary-pass correction reference affecting root ranking via clips?

Historical development diagnostic only. Replays the frozen native observer to
recover exact public capture credits, then reuses already evaluated eight-world
continuations. No new enemy information or campaign validation data enters.
"""
from collections import Counter
import hashlib
import json

from ai_registry import ROOT,build_policy
from feldmarschall import Engine,parse_square
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


def clipped(value):return max(-192,min(192,value))


def choose(values,parent,scores):
    wins=[move for move,score in scores.items() if score>=30000]
    if wins and parent in wins:return parent
    return max(wins or values,key=lambda move:(round(values[move],9),move==parent,-move[0],-move[1]))


def analyze(report,credits):
    parent=tuple(report['parent'])
    scores={tuple(row['move']):row['parent_score'] for row in report['values']}
    residual={tuple(row['move']):row['sample_mean'][0]-row['sample_mean'][1]+credits.get(tuple(row['move']),0)
              for row in report['values']}
    reference=report['values'][0]['sample_mean'][2]
    old={move:scores[move]+clipped(value-reference) for move,value in residual.items()}
    centered={move:scores[move]+clipped(value-residual[parent]) for move,value in residual.items()}
    unbounded_old={move:scores[move]+value-reference for move,value in residual.items()}
    unbounded_centered={move:scores[move]+value-residual[parent] for move,value in residual.items()}
    assert choose(unbounded_old,parent,scores)==choose(unbounded_centered,parent,scores)
    for row in report['values']:
        assert abs(row['correction']-clipped(residual[tuple(row['move'])]-reference))<1e-8
    assert choose(old,parent,scores)==tuple(report['selected'])
    selected=choose(centered,parent,scores)
    return dict(parent=parent,selected_original=report['selected'],selected_centered=selected,
        changed=selected!=tuple(report['selected']),reference=reference,parent_residual=residual[parent],
        parent_original_correction=clipped(residual[parent]-reference),parent_centered_correction=0,
        original_saturated_actions=sum(abs(value-reference)>=192 for value in residual.values()),
        centered_saturated_actions=sum(abs(value-residual[parent])>=192 for value in residual.values()),
        unclipped_ranking_invariant=True,
        values=[dict(move=move,native_score=scores[move],credit=credits.get(move,0),
                     residual=value,original=old[move],centered=centered[move])
                for move,value in residual.items()])


def run():
    folder=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon'
    destination=folder/'parent-centering-mechanism.json'
    assert not destination.exists(),'preserve existing diagnostic'
    previous=folder/'quiescence-mechanism.json'
    document=json.loads(previous.read_text())
    source=ROOT/document['source']
    targets={}
    for row in document['roots']:
        targets.setdefault((row['game'],row['army']),{})[row['ply']]=row
    executable,_=build_policy('teacher-context-v1-normal')
    observer=Engine(str(executable.parent/'observer'))
    records=[]
    try:
        with Tournament(source) as tournament:
            for game_id,army in sorted(targets):
                game=tournament.game(game_id);states,_=replay(game);events=public_events(game,states)
                seed=game['seed']*2+army+1
                for command in ('new '+('red','blue')[army],'rules 0','difficulty normal',
                                'seed '+str(seed),'setup '+game[('red_setup','blue_setup')[army]]):observer.send(command)
                selected=targets[(game_id,army)]
                for ply,event in enumerate(events[:max(selected)+1]):
                    if ply%2==army:
                        if ply in selected:
                            row=selected[ply];report=row['reports']['fixed4']
                            public=observer.ask('public','public')
                            assert hashlib.sha256(public.encode()).hexdigest()==row['public_sha256']
                            observer.send('ranked');credits={};scores={}
                            while True:
                                words=observer.read().split()
                                assert words[0]!='error'
                                if words[0]=='move':
                                    parent=tuple(map(parse_square,words[1:3]));break
                                if words[0] in ('credit','candidate'):
                                    (credits if words[0]=='credit' else scores)[tuple(map(int,words[1:3]))]=int(words[3])
                            assert parent==tuple(report['parent'])
                            assert scores=={tuple(v['move']):v['parent_score'] for v in report['values']}
                            result=analyze(report,credits)
                            records.append(dict(game=game_id,army=army,ply=ply,family=game['family'],**result))
                        else:observer.ask('go','move')
                        observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
                    observer.send(event)
    finally:observer.close()
    result=dict(kind='historical-public-parent-centering',strength_evidence=False,
        algebra='score(a)=native(a)+clip(d(a)-R,[-192,192]); d(a)=E[future-immediate]+credit(a). R is constant over actions. Alternative R=d(native_parent) changes no unbounded ranking; only clipping can change a choice.',
        reference_line='At depth4 the pass reference alternates opponent,root,opponent from the unchanged initial board; it does not contain two consecutive opponent moves within the line.',
        input='Frozen historical development continuations plus exact frozen native public capture credits; no referee rank features or campaign validation outcomes.',
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        previous_diagnostic_sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),
        summary=dict(roots=len(records),changed_decisions=sum(r['changed'] for r in records),
            roots_with_original_saturation=sum(r['original_saturated_actions']>0 for r in records),
            original_saturated_actions=sum(r['original_saturated_actions'] for r in records),
            centered_saturated_actions=sum(r['centered_saturated_actions'] for r in records),
            total_actions=sum(len(r['values']) for r in records),
            mean_absolute_parent_original_correction=sum(abs(r['parent_original_correction']) for r in records)/len(records),
            families=dict(Counter(r['family'] for r in records))),records=records)
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':run()
