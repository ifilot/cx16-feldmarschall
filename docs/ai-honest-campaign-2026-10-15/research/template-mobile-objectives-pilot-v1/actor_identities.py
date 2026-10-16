"""Track legitimate own initial identities in the same fixed40 public histories."""
import gzip,json,sys
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from feldmarschall import setup_squares,battle,GLYPHS
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
records=json.loads(gzip.decompress((HERE/'public-component-fixtures.json.gz').read_bytes()));results=json.loads((HERE/'result.json').read_text());requests={}
for row in records:requests.setdefault(row['game'],{})[row['ply']]=row
mapping={};armies=Counter();sampled=Counter()
cohort=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
with Tournament(cohort)as saved:
 for identity,positions in requests.items():
  game=saved.game(identity);army=next(iter(positions.values()))['army'];armies[army]+=1
  own={s:s for s in setup_squares(army)};states,_=replay(game);events=public_events(game,states)
  for ply,event in enumerate(events):
   if ply in positions:
    sampled[army]+=1
    for actor in positions[ply]['actor_diagnostics']:
     source=actor['source'];assert source in own;mapping[identity,ply,source]=own[source]
   if ply>=max(positions):break
   words=event.split();source,target=game['moves'][ply]
   if words[0]=='moved':
    if source in own:own[target]=own.pop(source)
   else:
    outcome=battle(GLYPHS.index(words[3]),GLYPHS.index(words[4]))
    if source in own:
     token=own.pop(source)
     if outcome=='attacker':own[target]=token
    elif target in own and outcome!='defender':own.pop(target)
changed={(row['game'],mapping[row['game'],row['ply'],actor['source']])for row in records for actor in row['actor_diagnostics']if actor['oldgoal']!=actor['newgoal']}
opportunities=results['opportunities'];actors={(r['game'],mapping[r['game'],r['ply'],r['source']])for r in opportunities}
result=dict(kind='fixed-sample-color-and-own-identity-diagnostics',game_armies=dict(armies),sampled_root_armies=dict(sampled),red_only_sample=True,color_limitation='All preregisteredodd IDsselectRed in swappedpairs; noBlueplaying-history/generalcolorclaim. Sample preserved unchanged; future bothcolorstudy must be preregistered.',goal_change_unique_own_piece_identities=len(changed),quiet_component_opportunity_unique_own_piece_identities=len(actors),quiet_component_opportunity_repeated_actor_roots=len(opportunities)-len(actors),opportunity_identities=[dict(game=r['game'],ply=r['ply'],source=r['source'],own_initial_square=mapping[r['game'],r['ply'],r['source']])for r in opportunities],no_new_root_selection=True,privacy='Own identity tracked from own initial deployment and public movement/combat outcomes only.')
(HERE/'identity-and-color.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
