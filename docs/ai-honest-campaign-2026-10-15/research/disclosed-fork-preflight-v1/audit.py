"""Public disclosed-fork geometry preflight, not a conversion or strength test."""
import hashlib,json,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import Position,COUNTS,GLYPHS,LAKES,TWO_SQUARES,battle
from tournament_store import Tournament
HERE=Path(__file__).resolve().parent
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
POLICY='student-template-flag-bomb-v1-normal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def adjacent(square):
 row,col=divmod(square,10)
 return [10*r+c for r,c in((row-1,col),(row,col-1),(row+1,col),(row,col+1))if 0<=r<10 and 0<=c<10 and 10*r+c not in LAKES]
def unsafe(cells,army,remaining,actor_square,actor_rank,shuttle):
 last_src,last_dst,count=shuttle
 row,col=divmod(actor_square,10)
 for dr,dc in((-1,0),(0,1),(1,0),(0,-1)):
  r,c=row,col;distance=0
  while True:
   r+=dr;c+=dc;distance+=1
   if not(0<=r<10 and 0<=c<10):break
   sq=10*r+c;cell=cells[sq]
   if cell==255:continue
   if cell==254 or bool(cell&16)==bool(army):break
   if count>=TWO_SQUARES and sq==last_dst and actor_square==last_src:break
   ranks=[cell&15]if cell&32 else[r for r,n in enumerate(remaining[:10])if n]
   if any(rank<10 and(distance==1 or rank==8)and battle(rank,actor_rank)!='defender'for rank in ranks):return True
   break
 return False

def candidates(cells,army,lost,moves,enemy_shuttle):
 seen=Counter(c&15 for c in cells if c<254 and bool(c&16)!=bool(army)and c&32)
 remaining=[max(0,n-l-s)for n,l,s in zip(COUNTS,lost,[seen[r]for r in range(12)])]
 geometry=[];eligible=[]
 for source,target in moves:
  if cells[target]!=255:continue
  rank=cells[source]&15
  victims=[sq for sq in adjacent(target)if cells[sq]<254 and bool(cells[sq]&16)!=bool(army)and cells[sq]&32 and cells[sq]&15<10 and battle(rank,cells[sq]&15)=='attacker']
  if len(victims)<2:continue
  record=dict(move=[source,target],rank=rank,victims=[dict(square=sq,rank=cells[sq]&15)for sq in victims]);geometry.append(record)
  after=cells[:];after[target]=after[source]|64;after[source]=255
  if not unsafe(after,army,remaining,target,rank,enemy_shuttle):eligible.append(record)
 return geometry,eligible

def run():
 start=time.perf_counter();counts=Counter();records=[];orientations=Counter();nibblechecks=0
 with Tournament(COHORT)as saved:games=[saved.game(row['id'])for row in saved.games()]
 for game in games:
  army=int(game['blue']==POLICY);assert game[('red','blue')[army]]==POLICY
  position=Position();lost=[[0]*12 for _ in(0,1)]
  for owner in(0,1):position.place(owner,game[('red_setup','blue_setup')[owner]])
  for ply,(source,target)in enumerate(game['moves']):
   if ply%2==army:
    cells=[254 if sq in LAKES else 255 if cell is None else(cell[1]if cell[0]==army or cell[3]else 12)|16*cell[0]|32*cell[3]|64*cell[2]for sq,cell in enumerate(position.cells)]
    moves=position.moves(army);geometry,eligible=candidates(cells,army,lost[1-army],moves,position.shuttle[1-army])
    counts['roots']+=1;counts['quiet_moves']+=sum(cells[t]==255 for s,t in moves)
    counts['geometry_roots']+=bool(geometry);counts['geometry_moves']+=len(geometry)
    counts['eligible_roots']+=bool(eligible);counts['eligible_moves']+=len(eligible)
    chosen=[source,target];selected=any(row['move']==chosen for row in eligible)
    counts['selected_eligible_roots']+=selected
    if eligible:
     orientations[army]+=1
     if nibblechecks<20:
      for nibble in range(12):
       changed=[(c&240)|nibble if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in cells]
       assert candidates(changed,army,lost[1-army],moves,position.shuttle[1-army])==(geometry,eligible)
      nibblechecks+=1
     records.append(dict(game=game['id'],army=army,ply=ply,selected=chosen,selected_eligible=selected,candidates=eligible))
   assert(source,target)in position.moves(ply%2)
   attacker,defender=position.cells[source],position.cells[target]
   if defender is None:position.move(source,target)
   else:
    _,fallen=position.fight(source,target,attacker[1],defender[1])
    for owner,rank,*_ in fallen:lost[owner][rank]+=1
 counts['games']=len(games);counts['eligible_games']=len({r['game']for r in records})
 return dict(kind='disclosed-fork-public-geometric-upper-bound',strength_evidence=False,forcing_certificate=False,cohort=str(COHORT.relative_to(ROOT)),cohort_sha256=sha(COHORT),counts=dict(counts),eligible_orientations=dict(orientations),private_nibble_invariance_roots=nibblechecks,elapsed_seconds=time.perf_counter()-start,sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'PROTOCOL.json',ROOT/'src/core/ai.c',ROOT/'src/core/ai_mission.c',ROOT/'tools/feldmarschall.py')},records=records)
if __name__=='__main__':
 result=run();(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('records','sources')},indent=2))
