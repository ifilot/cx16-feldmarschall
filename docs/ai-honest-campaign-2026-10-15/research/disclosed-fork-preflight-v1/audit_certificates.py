"""Exactly first20 prespecified public fork candidates; no new games."""
import hashlib,json,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from audit import HERE,COHORT,POLICY,sha
from certificate import certify
from feldmarschall import Position,COUNTS,LAKES
from tournament_store import Tournament

def run():
 incidence=json.loads((HERE/'result.json').read_text())
 selected=sorted([(row['game'],row['ply'],tuple(c['move']),c['victims'],row['selected'])for row in incidence['records']for c in row['candidates']],key=lambda x:(x[0],x[1],x[2]))[:20]
 selection=[dict(game=game,ply=ply,move=list(move))for game,ply,move,_,_ in selected]
 (HERE/'certificate-selection.json').write_text(json.dumps(selection,indent=2)+'\n')
 requests={}
 for entry in selected:requests.setdefault(entry[0],{}).setdefault(entry[1],[]).append(entry)
 results=[];counts=Counter();start=time.perf_counter()
 with Tournament(COHORT)as saved:
  for identity,positions in requests.items():
   game=saved.game(identity);army=int(game['blue']==POLICY);position=Position();lost=[[0]*12 for _ in(0,1)]
   for owner in(0,1):position.place(owner,game[('red_setup','blue_setup')[owner]])
   for ply,(source,target)in enumerate(game['moves']):
    if ply in positions:
     assert ply%2==army
     cells=[254 if sq in LAKES else 255 if cell is None else(cell[1]if cell[0]==army or cell[3]else 12)|16*cell[0]|32*cell[3]|64*cell[2]for sq,cell in enumerate(position.cells)]
     seen=Counter(c&15 for c in cells if c<254 and bool(c&16)!=bool(army)and c&32)
     remaining=[count-lost[1-army][r]-seen[r]for r,count in enumerate(COUNTS)]
     for _,_,move,victims,actual in positions[ply]:
      began=time.perf_counter();proof=certify(cells,army,lost[1-army],remaining,position.shuttle,move,[v['square']for v in victims]);elapsed=time.perf_counter()-began
      counts['candidates']+=1;counts['certified']+=proof['certified'];counts['inconclusive']+=proof.get('inconclusive',False)
      counts['certified_already_selected']+=proof['certified']and list(move)==actual
      if not proof['certified']:counts[proof['reason']]+=1
      results.append(dict(game=identity,army=army,ply=ply,move=list(move),saved_selected=actual,already_selected=list(move)==actual,victims=victims,proof=proof,elapsed_ms=elapsed*1000,
                          public_fixture=dict(cells=cells,lost=lost[1-army],remaining=remaining,shuttle=position.shuttle)))
    if ply>=max(positions):break
    attacker,defender=position.cells[source],position.cells[target]
    assert(source,target)in position.moves(ply%2)
    if defender is None:position.move(source,target)
    else:
     _,fallen=position.fight(source,target,attacker[1],defender[1])
     for owner,rank,*_ in fallen:lost[owner][rank]+=1
 return dict(kind='fixed-public-bounded-fork-conversion-audit',strength_evidence=False,selection=selection,nodecap=20000,depth_plies=4,counts=dict(counts),elapsed_seconds=time.perf_counter()-start,cohort_sha256=sha(COHORT),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'certificate.py',HERE/'CERTIFICATE-PROTOCOL.json',HERE/'result.json',ROOT/'tools/feldmarschall.py',ROOT/'tools/campaign_belief_values.py')},results=results)
if __name__=='__main__':
 result=run();(HERE/'certificate-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts'],indent=2));print('seconds',result['elapsed_seconds'])
