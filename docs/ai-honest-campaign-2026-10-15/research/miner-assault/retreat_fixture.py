"""Public-only sufficient proof of a two-own-turn Miner retreat preparation.

Research mechanical fixture, not a selectable policy. Ignoring blockers enlarges
one-step fighters' reach, so distance safety is conservative. Scouts cannot kill
Miners or ranks0..6; avoid applying this proof to Scout/Spy blocker movements.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import Position,COUNTS,battle
from tournament_store import Tournament


def neighbors(sq):
 for dc,dr in ((-1,0),(1,0),(0,-1),(0,1)):
  c,r=sq%10+dc,sq//10+dr
  if 0<=c<10 and 0<=r<10:yield r*10+c


def inventory(p,army,lost):
 remaining=[count-dead for count,dead in zip(COUNTS,lost)]
 for c in p.cells:
  if c and c[0]!=army and c[3]:remaining[c[1]]-=1
 assert min(remaining)>=0;return remaining


def possible(cell,remaining):
 if cell[3]:return [cell[1]]
 return [rank for rank,n in enumerate(remaining) if n and (not cell[2] or rank<10)]


def safe_one_step_fighters(p,army,target,own_rank,enemy_turns,remaining):
 assert own_rank<8 # Scout can kill equalScouts and Spies over long rays.
 threats=[]
 for sq,c in enumerate(p.cells):
  if c is None or c[0]==army:continue
  lethal=[rank for rank in possible(c,remaining) if rank<10 and battle(rank,own_rank)!='defender']
  assert 8 not in lethal
  if lethal:
   distance=abs(sq//10-target//10)+abs(sq%10-target%10)
   if distance<=enemy_turns:threats.append(sq)
 return not threats


def prove(p,army,lost,miner,blocker,vacate):
 remaining=inventory(p,army,lost);minercell=p.cells[miner];blockercell=p.cells[blocker]
 assert minercell and minercell[:2]==[army,7] and blockercell and blockercell[0]==army and blockercell[1]<7
 assert sum(c and c[0]==army and c[1]==7 for c in p.cells if c)==1
 assert (blocker,vacate) in p.moves(army) and p.cells[vacate] is None
 assert blocker in neighbors(miner)
 assert safe_one_step_fighters(p,army,miner,7,1,remaining)
 assert safe_one_step_fighters(p,army,blocker,7,2,remaining)
 assert safe_one_step_fighters(p,army,vacate,blockercell[1],2,remaining)
 flag=next(sq for sq,c in enumerate(p.cells) if c and c[:2]==[army,11])
 assert all(p.cells[sq] and p.cells[sq][:2]==[army,10] for sq in neighbors(flag))
 assert all(abs(sq//10-flag//10)+abs(sq%10-flag%10)>2 for sq,c in enumerate(p.cells)
            if c and c[0]!=army and 7 in possible(c,remaining))
 # Own first move resets army-wide shuttle; the planned adjacent retreat is
 # not its reverse. An enemy Scout/Spy occupying the retreat is safely captured.
 assert miner!=vacate;p.move(blocker,vacate);assert (miner,blocker) in p.moves(army)
 return dict(proved=True,prep=[blocker,vacate],retreat=[miner,blocker],horizon='survive first2enemy turns',
             strategy_fusion=False,material_cost_within_horizon=0,
             qualification='Retreat may capture a nonlethal Scout/Spy occupant. Every lethal attacker is a one-step piece and too far away. No long-term escape or winning plan is proved.')


def fixture():
 path=ROOT/'docs/ai-fair-information-2026-10-15/validation/dos--teacher-context-v1-normal.fmtour'
 with Tournament(path) as t:g=t.game(24)
 p=Position();p.place(0,g['red_setup']);p.place(1,g['blue_setup']);army=1;lost=[0]*12
 for src,dst in g['moves'][:223]:
  a,d=p.cells[src],p.cells[dst]
  if d is None:p.move(src,dst)
  else:
   _,fallen=p.fight(src,dst,a[1],d[1])
   for cell in fallen:
    if cell[0]!=army:lost[cell[1]]+=1
 for c in p.cells:
  if c and c[0]!=army and not c[3]:c[1]=12
 return p,army,lost,path


def run():
 p,army,lost,path=fixture();result=prove(p,army,lost,59,49,39)
 # Independent input-invariance repetitions: hidden low nibbles never authorize
 # rank inference in inventory(), possible() or the proof.
 for rank in range(12):
  q,side,counts,_=fixture()
  for c in q.cells:
   if c and c[0]!=side and not c[3]:c[1]=rank
  assert prove(q,side,counts,59,49,39)==result
 result.update(game=24,ply=223,hidden_nibble_variants=12,
               public_cells=[c for c in fixture()[0].cells],public_enemy_lost=lost,
               tournament_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 return result

if __name__=='__main__':print(json.dumps(run(),indent=2))
