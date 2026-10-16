"""Fixed335-root actor-specific executable-witness runtime audit; no games."""
import gzip,hashlib,json,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_mobile_capture import fork_selection,_fork_enemy_lost,_fork_own_moves
from feldmarschall import Position,COUNTS,LAKES
from tournament_store import Tournament
HERE=Path(__file__).resolve().parent
RESEARCH=HERE.parent/'disclosed-fork-preflight-v1'
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
POLICY='student-template-flag-bomb-v1-normal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 incidence=json.loads((RESEARCH/'result.json').read_text());requests={}
 for row in incidence['records']:requests.setdefault(row['game'],{})[row['ply']]=row
 counts=Counter();rows=[];full=[];start=time.perf_counter()
 with Tournament(COHORT)as saved:
  for identity,positions in sorted(requests.items()):
   game=saved.game(identity);army=int(game['blue']==POLICY);p=Position();lost=[[0]*12 for _ in(0,1)]
   for owner in(0,1):p.place(owner,game[('red_setup','blue_setup')[owner]])
   for ply,(source,target)in enumerate(game['moves']):
    if ply in positions:
     request=positions[ply]
     cells=[254 if sq in LAKES else 255 if cell is None else(cell[1]if cell[0]==army or cell[3]else 12)|16*cell[0]|32*cell[3]|64*cell[2]for sq,cell in enumerate(p.cells)]
     seen=Counter(c&15 for c in cells if c<254 and bool(c&16)!=bool(army)and c&32)
     remaining=[count-lost[1-army][r]-seen[r]for r,count in enumerate(COUNTS)];moves=p.moves(army)
     began=time.perf_counter();selected,report=fork_selection(cells,army,lost[1-army],remaining,dict.fromkeys(moves,0),tuple(request['selected']),p.shuttle);elapsed=1000*(time.perf_counter()-began)
     states=report.pop('witness_plan',{});overridden=list(selected)!=request['selected']
     counts['roots']+=1;counts['overrides']+=overridden;counts[report['reason']]+=1;counts['witness_states']+=len(states)
     if overridden:
      for key,move in states.items():
       side,board,fallen,hidden,red,blue=json.loads(key)
       assert _fork_enemy_lost(board,side,hidden)==fallen
       assert tuple(move)in _fork_own_moves(board,side,{0:tuple(red),1:tuple(blue)})
     item=dict(game=identity,army=army,ply=ply,native=request['selected'],selected=list(selected),overridden=overridden,reason=report['reason'],enemy_nodes=report['enemy_nodes'],elapsed_ms=elapsed,witness_states=len(states),native_bound=report.get('native_bound'),selected_bound=report.get('selected_bound'))
     rows.append(item);full.append(dict(**item,public_fixture=dict(cells=cells,lost=lost[1-army][:],remaining=remaining[:],shuttle=dict(p.shuttle)),report=report,witness_plan=states))
     if counts['roots']%25==0:print(json.dumps(dict(completed=counts['roots'],overrides=counts['overrides'],elapsed_seconds=time.perf_counter()-start)),flush=True)
    if ply>=max(positions):break
    attacker,defender=p.cells[source],p.cells[target];assert(source,target)in p.moves(ply%2)
    if defender is None:p.move(source,target)
    else:
     defender_moved=defender[2]
     outcome,fallen=p.fight(source,target,attacker[1],defender[1])
     if outcome=='defender':p.cells[target][2]=defender_moved
     for owner,rank,*_ in fallen:lost[owner][rank]+=1
 assert counts['roots']==335
 counts['override_games']=len({r['game']for r in rows if r['overridden']})
 with gzip.GzipFile(filename=str(HERE/'full-public-proofs.json.gz'),mode='wb',mtime=0)as f:f.write((json.dumps(full,separators=(',',':'))+'\n').encode())
 return dict(kind='fixed-gate-narrowed-runtime-qualification',strength_evidence=False,equal_score_tie_diagnostic=True,counts=dict(counts),elapsed_seconds=time.perf_counter()-start,cohort_sha256=sha(COHORT),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'NARROW-AUDIT-PROTOCOL.json',HERE/'FOLLOWTHROUGH-AMENDMENT.json',ROOT/'tools/campaign_mobile_capture.py',ROOT/'tools/campaign_native_mobile.py',RESEARCH/'result.json')},results=rows)
if __name__=='__main__':
 result=run();(HERE/'runtime-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts'],indent=2));print('seconds',result['elapsed_seconds'])
