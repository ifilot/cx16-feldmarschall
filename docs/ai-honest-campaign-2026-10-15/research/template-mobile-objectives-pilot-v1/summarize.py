"""Saved-data diagnostics separating goal, route and score-component changes."""
import gzip,json,hashlib,sys
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from component import route
rows=json.loads(gzip.decompress((HERE/'public-component-fixtures.json.gz').read_bytes()));counts=Counter();games={name:set()for name in('goal','strict_goal','hidden_strict_goal','route','disjoint_route')};sourceactors=set()
for row in rows:
 f=row['public_fixture'];cells=f['cells'];army=row['army'];scores={tuple(v['move']):v['score']for v in f['native_scores']}
 assert all(c&15==12 for c in cells if c<254 and bool(c&16)!=bool(army)and not c&32)
 for actor in row['actor_diagnostics']:
  source=actor['source'];sourceactors.add((row['game'],source));old=actor['oldgoal'];new=actor['newgoal']
  if old==new:continue
  counts['changed_actor_goals']+=1;games['goal'].add(row['game'])
  if old==255 or new==255:counts['goal_appeared_or_disappeared']+=1;continue
  oldrow=next(v for v in actor['rows']if v['target']==old);newrow=next(v for v in actor['rows']if v['target']==new)
  strict=(oldrow['oldutility']>newrow['oldutility']and oldrow['newutility']<newrow['newutility'])
  rejection=oldrow['oldaccepted']!=oldrow['newaccepted']or newrow['oldaccepted']!=newrow['newaccepted']
  if strict or rejection:counts['strict_goal_order_or_rejection_changes']+=1;games['strict_goal'].add(row['game'])
  if cells[old]&32 or cells[new]&32:continue
  counts['changed_both_hidden_goals']+=1
  if strict or rejection:counts['strict_both_hidden_goal_changes']+=1;games['hidden_strict_goal'].add(row['game'])
  quiet=[move for move in scores if move[0]==source and cells[move[1]]==255]
  if not quiet:continue
  maps=[route(cells,army,g,source)for g in(old,new)]
  progress=[{move:(d[source]-d[move[1]])if d[source]!=255 and d[move[1]]!=255 else 0 for move in quiet}for d in maps]
  best=[{move for move,p in values.items()if p==max(values.values())}for values in progress]
  if best[0]!=best[1]:counts['best_quiet_progress_sets_differ']+=1;games['route'].add(row['game'])
  if not(best[0]&best[1]):counts['best_quiet_progress_sets_disjoint']+=1;games['disjoint_route'].add(row['game'])
result=dict(kind='saved-component-opportunity-diagnostics',new_queries=0,counts=dict(counts),games={k:len(v)for k,v in games.items()},strict_quiet_argmax_interpretation='Distance-progress-only component diagnostic using captured native score/RNG terms; NOT actual counterfactual native policy selection or a playing-strength result.',coefficient=6,signed_integer_division='Truncate toward zero; stable_trunc within1e-9of integer only for floating posterior expectation.',baseline_persistence='Every prior ownnativego was executed and corrected to actualsavedmove before publicevent; previousgoal matched pre-root native strategy bytes.',privacy='Stored enemy hidden nibbles all12; model receives ownsetup and publicevents only.',source_sha256={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()for p in(HERE/'component.py',HERE/'public-component-fixtures.json.gz',Path(__file__))})
(HERE/'diagnostics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
