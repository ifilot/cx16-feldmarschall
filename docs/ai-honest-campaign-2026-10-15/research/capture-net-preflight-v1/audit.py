"""Fixed C21 capture-net incidence and first20 public certificate preflight."""
import gzip,hashlib,json,shlex,sys,time
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from net import candidates,certificate
from feldmarschall import Position,COUNTS,LAKES,GLYPHS,Engine,square_name
from tournament_store import Tournament
from campaign_mobile_capture import _fork_own_moves,_fork_enemy_lost,_fork_shuttle,_fork_public_key
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
POLICY='student-template-flag-bomb-v1-normal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def public(p,army,lost):
 cells=[254 if s in LAKES else 255 if c is None else(c[1]if c[0]==army or c[3]else 12)|16*c[0]|32*c[3]|64*c[2]for s,c in enumerate(p.cells)]
 seen=Counter(c&15 for c in cells if c<254 and bool(c&16)!=bool(army)and c&32)
 remaining=[count-lost[1-army][rank]-seen[rank]for rank,count in enumerate(COUNTS)]
 assert _fork_enemy_lost(cells,army,remaining)==lost[1-army]
 return cells,remaining

def run():
 started=time.perf_counter();counts=Counter();records=[];selected=[];nibblechecks=0
 assert sha(COHORT)==json.loads((HERE/'PROTOCOL.json').read_text())['cohort_sha256']
 with Tournament(COHORT)as saved:games=[saved.game(row['id'])for row in saved.games()]
 for game in sorted(games,key=lambda g:g['id']):
  army=int(game['blue']==POLICY);p=Position();lost=[[0]*12 for _ in(0,1)]
  for owner in(0,1):p.place(owner,game[('red_setup','blue_setup')[owner]])
  for ply,move in enumerate(game['moves']):
   source,target=move
   if ply%2==army:
    cells,remaining=public(p,army,lost);moves=_fork_own_moves(cells,army,p.shuttle);assert set(moves)==set(p.moves(army))
    counts['roots']+=1;counts['quiet_moves']+=sum(cells[t]==255 for s,t in moves)
    found=candidates(cells,army,lost[1-army],remaining,moves,tuple(move),p.shuttle)
    counts['eligible_roots']+=bool(found);counts['eligible_candidates']+=len(found)
    if found:
     chosen=any(row['move']==list(move)for row in found);counts['native_selected_eligible_roots']+=chosen
     record=dict(game=game['id'],army=army,ply=ply,native=list(move),candidates=found,native_selected_eligible=chosen)
     records.append(record)
     if len(selected)<20:
      fixture=dict(cells=cells[:],lost=lost[1-army][:],remaining=remaining[:],shuttle={a:tuple(v)for a,v in p.shuttle.items()})
      selected.append(dict(**record,candidate=found[0],public_fixture=fixture,public_key=_fork_public_key(cells,army,fixture['lost'],remaining,p.shuttle)))
      for nibble in range(12):
       mutated=[(c&240)|nibble if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in cells]
       assert candidates(mutated,army,lost[1-army],remaining,moves,tuple(move),p.shuttle)==found
      nibblechecks+=1
   attacker,defender=p.cells[source],p.cells[target];assert tuple(move)in p.moves(ply%2)
   if defender is None:p.move(source,target)
   else:
    moved=defender[2];outcome,fallen=p.fight(source,target,attacker[1],defender[1])
    if outcome=='defender':p.cells[target][2]=moved
    for owner,rank,*_ in fallen:lost[owner][rank]+=1
  if game['id']%25==0:print(json.dumps(dict(games=game['id'],roots=counts['roots'],eligible=counts['eligible_roots'],seconds=time.perf_counter()-started)),flush=True)
 counts['games']=len(games);counts['eligible_games']=len({r['game']for r in records})
 gate=dict(kind='capture-net-fixed-public-gate',strength_evidence=False,counts=dict(counts),private_nibble_gate_roots=nibblechecks,elapsed_seconds=time.perf_counter()-started,records=records,first20=selected)
 (HERE/'gate.json').write_text(json.dumps(gate,indent=2)+'\n')
 # Verify every copied first20 fixture against a real frozen public observer.
 directory=ROOT/'build/ai-catalog'/POLICY;receipt=json.loads((directory/'build.json').read_text());observer=directory/'observer';assert sha(observer)==receipt['runtime_sha256']['observer']
 requests={}
 for row in selected:requests.setdefault(row['game'],{})[row['ply']]=row
 for game in games:
  if game['id']not in requests:continue
  positions=requests[game['id']];army=int(game['blue']==POLICY);native=Engine(shlex.quote(str(observer)))
  try:
   for line in('new '+('red','blue')[army],'rules 0','setup '+game[('red_setup','blue_setup')[army]]):native.send(line)
   p=Position();lost=[[0]*12 for _ in(0,1)]
   for owner in(0,1):p.place(owner,game[('red_setup','blue_setup')[owner]])
   for ply,(source,target)in enumerate(game['moves']):
    if ply in positions:
     side,board,fallen,history=native.ask('public','public').split();cells=list(bytes.fromhex(board));cells=[(c&240)|12 if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in cells]
     f=positions[ply]['public_fixture'];assert int(side)==army and cells==f['cells']and list(bytes.fromhex(fallen))==f['lost']and _fork_shuttle(history)==f['shuttle']
     assert _fork_public_key(cells,army,list(bytes.fromhex(fallen)),f['remaining'],_fork_shuttle(history))==positions[ply]['public_key'];positions[ply]['native_public_verified']=True
    if ply>=max(positions):break
    attacker,defender=p.cells[source],p.cells[target]
    native.send('moved '+square_name(source)+' '+square_name(target)if defender is None else'battle '+square_name(source)+' '+square_name(target)+' '+GLYPHS[attacker[1]]+' '+GLYPHS[defender[1]])
    if defender is None:p.move(source,target)
    else:
     moved=defender[2];outcome,fallen=p.fight(source,target,attacker[1],defender[1])
     if outcome=='defender':p.cells[target][2]=moved
  finally:native.close()
 proofs=[];summary=Counter()
 for index,row in enumerate(selected):
  f=row['public_fixture'];args=(f['cells'],row['army'],f['lost'],f['remaining'],f['shuttle']);budget=[0,20000];began=time.perf_counter()
  native=certificate(*args,tuple(row['native']),budget)
  net=certificate(*args,tuple(row['candidate']['move']),budget,row['candidate'])if not native.get('inconclusive')else dict(certified=False,inconclusive=True,reason='native-control-cap-no-candidate-query',enemy_nodes=0)
  def bound(p):return(float('inf')if p.get('terminal_win')else p['minimum_net_material'])if p['certified']else 0
  fallback=bool(native.get('inconclusive')or net.get('inconclusive'));incremental=not fallback and bound(net)>bound(native)
  summary['roots']+=1;summary['native_certified']+=native['certified'];summary['net_certified']+=net['certified'];summary['global_cap_fallbacks']+=fallback;summary['incremental_roots']+=incremental;summary['incremental_unselected_roots']+=incremental and row['native']!=row['candidate']['move']
  item=dict(**row,reports=dict(native=native,net=net),enemy_nodes=budget[0],elapsed_ms=1000*(time.perf_counter()-began),incremental=incremental,global_cap_fallback=fallback)
  proofs.append(item);print(json.dumps(dict(first20=index+1,game=row['game'],ply=row['ply'],native=native['certified'],net=net['certified'],incremental=incremental,nodes=budget[0])),flush=True)
  if index<3:
   mutated=[(c&240)|0 if c<254 and bool(c&16)!=bool(row['army'])and not c&32 else c for c in f['cells']];checkargs=(mutated,row['army'],f['lost'],f['remaining'],f['shuttle']);checkbudget=[0,20000]
   checknative=certificate(*checkargs,tuple(row['native']),checkbudget);assert checknative==native
   if not native.get('inconclusive'):assert certificate(*checkargs,tuple(row['candidate']['move']),checkbudget,row['candidate'])==net
   assert checkbudget==budget
 with gzip.GzipFile(filename=str(HERE/'first20-proofs.json.gz'),mode='wb',mtime=0)as archive:archive.write((json.dumps(proofs,separators=(',',':'))+'\n').encode())
 summary['incremental_games']=len({r['game']for r in proofs if r['incremental']})
 result=dict(kind='capture-net-first20-generalized-common-control',strength_evidence=False,summary=dict(summary),gate_counts=dict(counts),gate_seconds=gate['elapsed_seconds'],total_seconds=time.perf_counter()-started,first20_native_public_verified=len(selected),first3_proof_private_nibble_invariance=True,observer_sha256=sha(observer),cohort_sha256=sha(COHORT),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'net.py',HERE/'PROTOCOL.json',HERE/'SOURCE-FREEZE.json',ROOT/'tools/campaign_mobile_capture.py')},results=[{k:v for k,v in row.items()if k not in('public_fixture','public_key','reports','candidates')}for row in proofs])
 (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['summary'],indent=2));return result
if __name__=='__main__':run()
