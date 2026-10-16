"""Prespecified full361 same-screening-cohort extension; no runtime/matches."""
import gzip,hashlib,json,shlex,sys,time,statistics
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from audit import COHORT,POLICY,sha,public
from net import candidates,certificate,own_outcomes
from feldmarschall import Position,GLYPHS,Engine,square_name
from tournament_store import Tournament
from campaign_mobile_capture import _fork_own_moves,_fork_enemy_lost,_fork_shuttle,_fork_public_key
from campaign_belief_values import worths

def run():
 start=time.perf_counter();protocol=json.loads((HERE/'EXPANSION-PROTOCOL.json').read_text())
 for name,expected in protocol['source_sha256'].items():assert sha(HERE/name)==expected
 gate=json.loads((HERE/'gate.json').read_text());requests={}
 for row in gate['records']:requests.setdefault(row['game'],{})[row['ply']]=row
 directory=ROOT/'build/ai-catalog'/POLICY;receipt=json.loads((directory/'build.json').read_text());observer=directory/'observer';assert sha(observer)==receipt['runtime_sha256']['observer']
 first20=json.loads(gzip.decompress((HERE/'first20-proofs.json.gz').read_bytes()));original={(r['game'],r['ply']):r for r in first20};equal=0;full=[];counts=Counter();nodes=[];times=[];witnesses=0;comparisons=Counter();positive_games=Counter();orientations=Counter()
 with Tournament(COHORT)as saved:
  for identity,positions in sorted(requests.items()):
   game=saved.game(identity);army=int(game['blue']==POLICY);p=Position();lost=[[0]*12 for _ in(0,1)]
   for owner in(0,1):p.place(owner,game[('red_setup','blue_setup')[owner]])
   native=Engine(shlex.quote(str(observer)))
   try:
    for line in('new '+('red','blue')[army],'rules 0','setup '+game[('red_setup','blue_setup')[army]]):native.send(line)
    for ply,(source,target)in enumerate(game['moves']):
     if ply in positions:
      row=positions[ply];cells,remaining=public(p,army,lost);moves=_fork_own_moves(cells,army,p.shuttle);assert set(moves)==set(p.moves(army))
      found=candidates(cells,army,lost[1-army],remaining,moves,(source,target),p.shuttle);assert found==row['candidates'];candidate=found[0]
      fixture=dict(cells=cells[:],lost=lost[1-army][:],remaining=remaining[:],shuttle={a:tuple(v)for a,v in p.shuttle.items()})
      publickey=_fork_public_key(cells,army,fixture['lost'],remaining,p.shuttle)
      side,board,fallen,history=native.ask('public','public').split();actual=[(c&240)|12 if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in bytes.fromhex(board)]
      assert int(side)==army and actual==cells and list(bytes.fromhex(fallen))==fixture['lost']and _fork_shuttle(history)==p.shuttle
      assert _fork_public_key(actual,army,list(bytes.fromhex(fallen)),remaining,_fork_shuttle(history))==publickey
      began=time.perf_counter();budget=[0,20000];args=(cells,army,fixture['lost'],remaining,p.shuttle)
      control=certificate(*args,(source,target),budget)
      net=certificate(*args,tuple(candidate['move']),budget,candidate)if not control.get('inconclusive')else dict(certified=False,inconclusive=True,reason='native-control-cap-no-candidate-query',enemy_nodes=0)
      elapsed=1000*(time.perf_counter()-began)
      def bound(proof):return(float('inf')if proof.get('terminal_win')else proof['minimum_net_material'])if proof['certified']else 0
      fallback=bool(control.get('inconclusive')or net.get('inconclusive'));incremental=not fallback and bound(net)>bound(control)
      item=dict(game=identity,army=army,ply=ply,native=[source,target],candidate=candidate,public_fixture=fixture,public_key=publickey,native_public_verified=True,reports=dict(native=control,net=net),enemy_nodes=budget[0],elapsed_ms=elapsed,incremental=incremental,global_cap_fallback=fallback)
      if(identity,ply)in original:
       old=original[identity,ply]
       assert old['reports']==item['reports']and old['enemy_nodes']==budget[0]and old['candidate']==candidate and old['public_key']==publickey
       assert json.loads(json.dumps(old['public_fixture']))==json.loads(json.dumps(fixture));equal+=1
      for proof in(control,net):
       if not proof['certified']:continue
       responses=proof.get('responses',[]);assert len(responses)==proof['first_public_outcomes'];assert len({r['public_key']for r in responses})==len(responses)
       for response in responses:
        owner,board,fallen,hidden,red,blue=json.loads(response['public_key']);state={0:tuple(red),1:tuple(blue)};action=tuple(response['response'])
        assert owner==army and _fork_enemy_lost(board,army,hidden)==fallen and action in _fork_own_moves(board,army,state)
        assert list(own_outcomes(board,army,hidden,state,action,worths(fixture['lost'])))
        witnesses+=1
      counts['roots']+=1;counts['native_certified']+=control['certified'];counts['net_certified']+=net['certified'];counts['global_cap_fallbacks']+=fallback;counts['incremental_roots']+=incremental;counts['incremental_unselected_roots']+=incremental and row['native']!=candidate['move']
      if incremental:
       positive_games[identity]+=1;orientations[army]+=1
       key=hashlib.sha256((publickey+'|'+json.dumps([row['native'],candidate],sort_keys=True)).encode()).hexdigest();comparisons[key]+=1
      nodes.append(budget[0]);times.append(elapsed);full.append(item)
      if counts['roots']%25==0:print(json.dumps(dict(roots=counts['roots'],incremental=counts['incremental_roots'],caps=counts['global_cap_fallbacks'],seconds=time.perf_counter()-start)),flush=True)
     if ply>=max(positions):break
     attacker,defender=p.cells[source],p.cells[target]
     native.send('moved '+square_name(source)+' '+square_name(target)if defender is None else'battle '+square_name(source)+' '+square_name(target)+' '+GLYPHS[attacker[1]]+' '+GLYPHS[defender[1]])
     if defender is None:p.move(source,target)
     else:
      moved=defender[2];outcome,fallen=p.fight(source,target,attacker[1],defender[1])
      if outcome=='defender':p.cells[target][2]=moved
      for owner,rank,*_ in fallen:lost[owner][rank]+=1
   finally:native.close()
 assert counts['roots']==361 and equal==20
 with gzip.GzipFile(filename=str(HERE/'full361-proofs.json.gz'),mode='wb',mtime=0)as archive:archive.write((json.dumps(full,separators=(',',':'))+'\n').encode())
 result=dict(kind='same-screening-cohort-full361-extension',strength_evidence=False,independent_validation=False,summary=dict(counts),first20_inputs_proofs_nodes_exactly_equal=equal,all361_native_public_keys_verified=True,legal_public_witnesses_verified=witnesses,incremental_game_distribution=dict(positive_games),incremental_armies=dict(orientations),distinct_incremental_public_comparisons=len(comparisons),largest_repeated_incremental_comparison=max(comparisons.values(),default=0),root_time_ms=dict(mean=statistics.mean(times),median=statistics.median(times),maximum=max(times)),root_enemy_outcome_attempts=dict(mean=statistics.mean(nodes),maximum=max(nodes)),total_seconds=time.perf_counter()-start,observer_sha256=sha(observer),cohort_sha256=sha(COHORT),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'net.py',HERE/'EXPANSION-PROTOCOL.json',HERE/'EXPANSION-SOURCE-FREEZE.json',HERE/'gate.json',HERE/'first20-proofs.json.gz',ROOT/'tools/campaign_mobile_capture.py')},results=[{k:v for k,v in r.items()if k not in('public_fixture','public_key','reports')}for r in full])
 (HERE/'full361-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('results','sources')},indent=2))
if __name__=='__main__':run()
