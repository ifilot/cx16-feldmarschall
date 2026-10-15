"""Historical sampled-world incidence before a capable-route policy is built."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from ai_registry import ROOT, build_policy
from campaign_routes import geometric_pursuit, capable_pursuit
from feldmarschall import Engine, square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay
from train_ai_student import sample_world


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(destination):
    source=ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour'
    historical=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon/quiescence-mechanism.json'
    document=json.loads(historical.read_text())
    assert document['source_sha256']==digest(source)
    targets={}
    for row in document['roots']:
        targets.setdefault((row['game'],row['army']),{})[row['ply']]=row['public_sha256']
    executable,receipt=build_policy('teacher-context-v1-normal')
    observer=Engine(str(executable.parent/'observer'))
    records=[]
    try:
        with Tournament(source) as tournament:
            for game_id,army in sorted(targets):
                game=tournament.game(game_id)
                states,_=replay(game)
                events=public_events(game,states)
                seed=game['seed']*2+army+1
                rng=random.Random(seed)
                for command in ('new '+('red','blue')[army],'rules 0','difficulty normal',
                                'seed '+str(seed),'setup '+game[('red_setup','blue_setup')[army]]):
                    observer.send(command)
                selected=targets[(game_id,army)]
                for ply,event in enumerate(events[:max(selected)+1]):
                    if ply%2==army:
                        if ply in selected:
                            public=observer.ask('public','public')
                            assert hashlib.sha256(public.encode()).hexdigest()==selected[ply]
                            _,board,lost,_=public.split()
                            cells=list(bytes.fromhex(board))
                            histories={square:list(map(int,observer.ask('memory '+square_name(square),'history').split()))
                                for square,cell in enumerate(cells)
                                if cell<254 and bool(cell&16)!=bool(army) and not cell&32}
                            worlds=[]
                            for sample in range(8):
                                world,weight=sample_world(cells,list(bytes.fromhex(lost)),histories,rng,army)
                                sides=[]
                                for owner in (0,1):
                                    old=geometric_pursuit(world,owner)
                                    new=capable_pursuit(world,owner)
                                    assert new<=old,(old,new)
                                    sides.append(dict(geometric=old,capable=new,gap=old-new))
                                worlds.append(dict(weight=weight,sides=sides))
                            records.append(dict(game=game_id,army=army,family=game['family'],ply=ply,worlds=worlds))
                            print('Historical route root',len(records),'/ 140',flush=True)
                        observer.ask('go','move')
                        observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
                    observer.send(event)
    finally:observer.close()
    sides=[side for row in records for world in row['worlds'] for side in world['sides']]
    result=dict(kind='historical-sampled-world-route-incidence',strength_evidence=False,
        public_input='Own setup, public histories and eight sampled armies; no enemy setup or referee-rank features.',
        mechanism='Compare current two-pass pursuit with rank-specific surviving-attacker routes. Friendly mobile blockers remain removable as in current pursuit.',
        source_sha256=digest(source),historical_roots_sha256=digest(historical),baseline_receipt=receipt,
        summary=dict(roots=len(records),worlds=len(records)*8,side_evaluations=len(sides),
                     changed_side_evaluations=sum(side['gap']>0 for side in sides),
                     geometric_open_but_no_capable_route=sum(side['geometric']>-400 and side['capable']==-400 for side in sides),
                     mean_pursuit_gap=sum(side['gap'] for side in sides)/len(sides),
                     roots_with_gap=sum(any(side['gap']>0 for world in row['worlds'] for side in world['sides']) for row in records),
                     families=dict(Counter(row['family'] for row in records))),records=records)
    assert not destination.exists(),'preserve original incidence evidence'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary'],indent=2),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon/capable-route-incidence.json')
    run(parser.parse_args().out)
