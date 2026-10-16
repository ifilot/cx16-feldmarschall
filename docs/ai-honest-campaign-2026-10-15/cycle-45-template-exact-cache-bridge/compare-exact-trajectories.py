"""Compare every saved native-cache bridge trajectory, including DOS errors."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from tournament_store import Tournament
HERE=Path(__file__).resolve().parent
plan=json.loads((HERE/'plan.json').read_text())
assert plan['cycle']==45 and len(plan['policies'])==2
paths=[HERE/(identity+'.fmtour') for identity in plan['policies']]
normalized=[]
for identity,path in zip(plan['policies'],paths):
 with Tournament(path)as saved:
  assert saved.metadata()['status']=='complete'
  games=[saved.game(row['id'])for row in saved.games()]
  assert len(games)==400
  for game in games:
   for side in('red','blue'):
    if game[side]==identity:game[side]='candidate'
  normalized.append(games)
assert len(normalized[0])==len(normalized[1])
differences=[]
for before,after in zip(*normalized):
 changed=[key for key in set(before)|set(after)if before.get(key)!=after.get(key)]
 if changed:differences.append(dict(game=before['id'],changed=sorted(changed)))
result=dict(passed=not differences,attempts_per_arm=400,all_setups_moves_outcomes_and_error_reasons_compared=True,exactly_identical_games=400-len(differences),differences=differences,tournament_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},scope='Exact fixed-cohort regression bridge. Not a statistical equivalence claim or target-average performance measurement.')
(HERE/'exact-trajectories.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));assert result['passed']
