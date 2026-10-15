"""Count exact public last-Miner/Flag-Bomb-operator gates on OLD cohorts only."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import Position,COUNTS,LAKES
from tournament_store import Tournament
from last_miner_audit import reachable
PATHS=['docs/ai-fair-information-2026-10-15/validation/dos--teacher-context-v1-normal.fmtour',
       'docs/ai-vs-msdos-2026-10-15/teacher-context-v1-normal.fmtour',
       'docs/ai-restrained-search-2026-10-15/development.fmtour']

def gate(p,army):
 miners=[sq for sq,c in enumerate(p.cells) if c and c[0]==army and c[1]==7]
 if len(miners)!=1:return None
 flags={sq for sq,c in enumerate(p.cells) if c and c[0]!=army and ((c[3] and c[1]==11) or (not c[3] and not c[2]))}
 if len(flags)!=1:return None
 bombs={sq for sq,c in enumerate(p.cells) if c and c[0]!=army and c[3] and c[1]==10}
 others=[sq for sq,c in enumerate(p.cells) if c and c[0]==army and c[1]<10 and c[1]!=7]
 if not others or flags&reachable(others,bombs):return None
 return dict(miner=miners[0],flag=next(iter(flags)),known_bombs=sorted(bombs))

def public_hex(p,army):
 return bytes(254 if sq in LAKES else 255 if c is None else c[0]*16|(c[1] if c[0]==army or c[3] else 12)|(64 if c[2] else 0)|(32 if c[3] else 0)for sq,c in enumerate(p.cells)).hex()

def audit():
 count=Counter();rows=[];sources=[];games=set()
 for path in PATHS:
  path=ROOT/path;sources.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  with Tournament(path) as t:
   for entry in t.games():
    if entry['result']=='error':continue
    g=t.game(entry['id']);p=Position();p.place(0,g['red_setup']);p.place(1,g['blue_setup']);losses=[[0]*12 for _ in (0,1)];count['games']+=1
    for ply,(src,dst) in enumerate(g['moves']):
     army=ply%2;identity=g[('red','blue')[army]]
     if 'msdos' not in identity and '1990' not in identity:
      count['honest_roots']+=1;result=gate(p,army)
      if result:
       count['resource_gate_roots']+=1;games.add((str(path),g['id']))
       if src==result['miner']:count['resource_gate_actual_miner_moves']+=1
       state=bytes(p.shuttle[a][i] if p.shuttle[a][i] is not None else 255 for i in range(3)for a in(0,1)).hex()
       rows.append(dict(source=str(path.relative_to(ROOT)),game=g['id'],ply=ply,army=army,policy=identity,actual_move=[src,dst],actual_mover_is_miner=src==result['miner'],public_board_hex=public_hex(p,army),lost=losses[1-army][:],shuttle=state,**result))
     a,d=p.cells[src],p.cells[dst]
     if d is None:p.move(src,dst)
     else:
      _,fallen=p.fight(src,dst,a[1],d[1])
      for c in fallen:losses[c[0]][c[1]]+=1
 count['games_with_resource_gate']=len(games)
 return dict(kind='old-public-last-miner-resource-gate-incidence',strength_evidence=False,counters=dict(count),
             gate='Exactlyone ownMiner; exactlyone publicFlagcandidate (disclosedFlag or unmovedundisclosed enemy); at leastone ownnonMinermobile; knownenemyBombs disconnect thatFlag from every nonMiner under optimistic terrain-only movement.',
             argument='All other pieces are treated as eventually clearable. If known Bombs still separate the sole Flag, a surviving Miner is necessary for Flag capture. No claim that Flag capture is the only possible winning terminal.',
             sources=sources,rows=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

if __name__=='__main__':print(json.dumps(audit(),indent=2))
