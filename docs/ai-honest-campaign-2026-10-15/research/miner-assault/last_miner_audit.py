"""Public last-Miner resource opportunity audit; truth confined to offline labels."""
from collections import Counter,deque
import hashlib
import heapq
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import Position,GLYPHS,LAKES,battle
from tournament_store import Tournament
P=ROOT/'docs/ai-fair-information-2026-10-15/validation/dos--teacher-context-v1-normal.fmtour'

def clone(p):
 q=Position();q.cells=[list(c) if c else None for c in p.cells];q.shuttle=dict(p.shuttle);return q

def adjacent(sq):
 for dc,dr in ((-1,0),(1,0),(0,-1),(0,1)):
  c,r=sq%10+dc,sq//10+dr;dst=r*10+c
  if 0<=c<10 and 0<=r<10 and dst not in LAKES:yield dst

def reachable(starts,blocked):
 seen=set(starts);queue=deque(starts)
 while queue:
  for dst in adjacent(queue.popleft()):
   if dst not in blocked and dst not in seen:seen.add(dst);queue.append(dst)
 return seen

def shortest(p,start,bombs):
 dist={start:(0,0)};queue=[(0,0,start)]
 while queue:
  b,d,sq=heapq.heappop(queue)
  if dist[sq]!=(b,d):continue
  for dst in adjacent(sq):
   value=(b+int(dst in bombs),d+1)
   if value<dist.get(dst,(999,999)):dist[dst]=value;heapq.heappush(queue,(*value,dst))
 return dist

def analyze():
 count=Counter();rows=[]
 with Tournament(P) as tour:
  for entry in tour.games():
   if entry['result']=='error':continue
   game=tour.game(entry['id']);side=int(game['blue']=='teacher-context-v1-normal');p=Position();p.place(0,game['red_setup']);p.place(1,game['blue_setup']);previous=None
   count['games']+=1;result='draw' if game['result']=='draw' else 'win' if game['result']==('red','blue')[side] else 'loss'
   for ply,(src,dst) in enumerate(game['moves']):
    a,d=p.cells[src],p.cells[dst];outcome=battle(a[1],d[1]) if d else 'attacker'
    miners=[sq for sq,c in enumerate(p.cells) if c and c[0]==side and c[1]==7]
    dead=bool(d) and ((a[0]==side and a[1]==7 and outcome!='attacker') or (d[0]==side and d[1]==7 and outcome!='defender'))
    row=None
    if dead and len(miners)==1:
     count['last_miner_deaths']+=1;count['last_miner_death_'+result]+=1
     defending=a[0]!=side;root,ownsrc,owndst,ownrank,owntarget=previous if defending else (clone(p),src,dst,a[1],list(d))
     candidates={sq for sq,c in enumerate(root.cells) if c and c[0]!=side and ((c[3] and c[1]==11) or (not c[3] and not c[2]))}
     public_bombs={sq for sq,c in enumerate(root.cells) if c and c[0]!=side and c[3] and c[1]==10}
     own_others=[sq for sq,c in enumerate(root.cells) if c and c[0]==side and c[1]<10 and c[1]!=7]
     reached=reachable(own_others,public_bombs)
     certain=bool(candidates) and bool(own_others) and not candidates&reached
     breach=defending and ownrank==7 and owndst==dst and owntarget is not None and owntarget[1]==10
     known_killer=root.cells[src][3] if defending and root.cells[src] and root.cells[src][0]!=side else bool(d[3]) if not defending else False
     row=dict(game=game['id'],family=game['family'],ply=ply,result=result,reason=game['reason'],defending=defending,own_preceding_move=[ownsrc,owndst],killer_previously_disclosed=known_killer,after_bomb_defuse=breach,bomb_previously_disclosed=bool(owntarget[3]) if breach else None,
              public_flag_candidates=len(candidates),public_known_bombs=len(public_bombs),public_all_flag_candidates_separated_by_known_bombs=certain)
     if certain:count['last_miner_deaths_with_public_necessary_breach']+=1
     if breach:
      count['last_miner_death_after_bomb_defuse']+=1
      target=owndst;row['bomb_adjacent_to_any_public_flag_candidate']=bool(set(adjacent(target))&candidates)
      actual_flag=next(sq for sq,c in enumerate(root.cells) if c and c[0]!=side and c[1]==11)
      true_bombs={sq for sq,c in enumerate(root.cells) if c and c[0]!=side and c[1]==10}
      source_distance=shortest(root,ownsrc,true_bombs);via_distance=shortest(root,target,true_bombs)
      route=source_distance[actual_flag];via=tuple(x+y for x,y in zip(source_distance[target],via_distance[actual_flag]))
      row['offline_true_flag_bomb_distance']=abs(target//10-actual_flag//10)+abs(target%10-actual_flag%10)
      row['offline_bomb_on_minimum_breach_then_step_true_flag_route']=route==via
     rows.append(row)
    if a[0]==side:previous=(clone(p),src,dst,a[1],list(d) if d else None)
    if d is None:p.move(src,dst)
    else:p.fight(src,dst,a[1],d[1])
    if row is not None:
     actual_flag=next((sq for sq,c in enumerate(p.cells) if c and c[0]!=side and c[1]==11),None)
     true_bombs={sq for sq,c in enumerate(p.cells) if c and c[0]!=side and c[1]==10}
     own_survivors=[sq for sq,c in enumerate(p.cells) if c and c[0]==side and c[1]<10]
     screened=actual_flag is not None and bool(own_survivors) and actual_flag not in reachable(own_survivors,true_bombs)
     row['offline_remaining_flag_unreachable_without_defusing_enemy_bomb']=screened
     if screened:count['last_miner_deaths_leaving_true_bomb_screened_flag']+=1
 return dict(kind='last-miner-resource-constraint-feasibility',strength_evidence=False,counters=dict(count),rows=rows,tournament_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),limits=['True Flag/Bomb ranks are used ONLY for explicitly labeled offline followup outcomes and shortest-route labels.','Policy-visible flag candidates are disclosed Flag or unmoved undisclosed enemy occupancy; known Bomb cuts are exact public geometry.','Reachability optimistically clears every mobile and own immobile blocker. Enemy Bombs alone remain impassable; no hidden rank inference enters the public gate.','Zero public gates means this conservative condition finds no supported decision opportunity; it does not refute weaker belief-based resource plans.'])

if __name__=='__main__':print(json.dumps(analyze(),indent=2))
