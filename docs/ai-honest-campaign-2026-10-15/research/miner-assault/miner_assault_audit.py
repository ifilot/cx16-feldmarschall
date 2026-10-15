"""Research-only Miner assault incidence; no policy implementation or shared edits."""
import sys,json,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import Position,battle,GLYPHS
from tournament_store import Tournament
P=ROOT/Path('docs/ai-fair-information-2026-10-15/validation/dos--teacher-context-v1-normal.fmtour')
def clone(p):
 q=Position();q.cells=[list(c) if c else None for c in p.cells];q.shuttle=dict(p.shuttle);return q
count=Counter();cases=[];previous=None
with Tournament(P) as tour:
 for entry in tour.games():
  if entry['result']=='error':continue
  g=tour.game(entry['id']);side=int(g['blue']=='teacher-context-v1-normal');p=Position();p.place(0,g['red_setup']);p.place(1,g['blue_setup']);previous=None
  count['games']+=1
  result='draw' if g['result']=='draw' else 'win' if g['result']==('red','blue')[side] else 'loss'
  count['games_'+result]+=1
  for ply,(s,t) in enumerate(g['moves']):
   a,d=p.cells[s],p.cells[t];prior=clone(p)
   if a[0]==side and a[1]==7 and d and d[1]==10:
    count['miner_bomb_defuses']+=1;count['known_bomb_defuses' if d[3] else 'concealed_bomb_defuses']+=1
   if d and d[0]==side and d[1]==7 and a[0]!=side and battle(a[1],7)!='defender':
    count['miner_defending_deaths']+=1
    if previous:
     root,our_s,our_t,our_rank,our_target=previous
     known=root.cells[s] is not None and root.cells[s][0]!=side and root.cells[s][3]
     if known:count['miner_defending_deaths_attacker_known_preceding_root']+=1
     if our_rank==7 and our_t==t:
      count['miner_killed_immediately_after_own_move']+=1
      if known:count['moved_miner_killed_by_previously_known_enemy']+=1
      if our_target and our_target[1]==10:
       count['miner_recaptured_immediately_after_bomb_defuse']+=1
       count['bomb_defuse_recapture_'+result]+=1
       if our_target[3]:count['recapture_after_known_bomb_defuse']+=1
       adjacent=abs(s//10-t//10)+abs(s%10-t%10)==1
       escorts=[q for q,c in enumerate(root.cells) if c and c[0]==side and c[1]<10 and c[1]!=7 and battle(c[1],a[1])=='attacker'] if known else []
       immediate=[m for m in root.moves(side) if m[1]==s and m[0] in escorts]
       rear=t>=80 if side else t<20
       next_own=g['moves'][ply+1] if ply+1<len(g['moves']) else None
       recapture=next_own is not None and next_own[1]==t and p.cells[next_own[0]] is not None and battle(p.cells[next_own[0]][1],a[1])!='defender'
       if recapture:count['actual_immediate_escort_recaptures']+=1
       cases.append(dict(game=g['id'],result=result,actual_next_own_recapture=recapture,ply=ply,root_move=[our_s,our_t],bomb_known=bool(our_target[3]),attacker_previously_known=known,enemy_attacker_rank=GLYPHS[a[1]],enemy_square=s,bomb_in_native_rear_region=rear,adjacent_enemy=adjacent,own_strict_winning_escort_squares=escorts,legal_immediate_escort_captures=immediate,existing_escort_trigger_shape=known and bool(our_target[3]) and adjacent and rear and bool(escorts)))
   if a[0]==side:previous=(prior,s,t,a[1],list(d) if d else None)
   if d is None:p.move(s,t)
   else:p.fight(s,t,a[1],d[1])
print(json.dumps(dict(kind='old-baseline-miner-breach-attrition',strength_evidence=False,counters=dict(count),cases=cases,tournament=str(P.relative_to(ROOT)),tournament_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),limits=['Actual loss labels and combat ranks come from offline referee replay; escort eligibility reads enemy ranks only when publicly disclosed at the preceding own root.','Repeated support cannot prevent a legal enemy capture merely by threatening recapture; Stratego has no zone of control.','Public-rank-capable escort squares are not proof of reachable or safe supporting routes.','An immediate recapture can be an intentional favorable trade; Miner death does not establish a strategic error.','Only one archived stress-family baseline cohort examined; no active campaign validation.']),indent=2))
