"""All fixed335 public gate roots, unchanged common certificate; no games."""
import json,sys,time
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from audit import HERE,COHORT,POLICY,sha
from certificate_common import certify_common
from certificate import own_moves,successors
from campaign_belief_values import worths
from feldmarschall import Position,COUNTS,LAKES
from tournament_store import Tournament

def run():
 incidence=json.loads((HERE/'result.json').read_text());requests={}
 for row in incidence['records']:requests.setdefault(row['game'],{})[row['ply']]=row
 preserved=json.loads((HERE/'common-result.json').read_text())
 controls={(r['game'],r['ply'],tuple(r['fork'])):r for r in preserved['results']}
 results=[];counts=Counter();start=time.perf_counter()
 with Tournament(COHORT)as saved:
  for identity,positions in sorted(requests.items()):
   game=saved.game(identity);army=int(game['blue']==POLICY);p=Position();lost=[[0]*12 for _ in(0,1)]
   for owner in(0,1):p.place(owner,game[('red_setup','blue_setup')[owner]])
   for ply,(source,target)in enumerate(game['moves']):
    if ply in positions:
     request=positions[ply];assert ply%2==army
     cells=[254 if sq in LAKES else 255 if cell is None else(cell[1]if cell[0]==army or cell[3]else 12)|16*cell[0]|32*cell[3]|64*cell[2]for sq,cell in enumerate(p.cells)]
     seen=Counter(c&15 for c in cells if c<254 and bool(c&16)!=bool(army)and c&32)
     remaining=[count-lost[1-army][r]-seen[r]for r,count in enumerate(COUNTS)];args=(cells,army,lost[1-army],remaining,p.shuttle)
     native=request['selected'];native_quiet=cells[native[1]]==255
     flagwin=any(cells[t]<254 and cells[t]&32 and cells[t]&15==11 for s,t in own_moves(cells,army,p.shuttle))
     flagthreat=any(o['flag_loss']for o in successors(cells,army,remaining,p.shuttle,worths(lost[1-army]),[0,20000]))
     began=time.perf_counter();nativeproof=certify_common(*args,tuple(native))if native_quiet else dict(certified=False,preserve_native_capture=True,enemy_nodes=0);native_ms=1000*(time.perf_counter()-began)
     counts['roots']+=1;counts['native_quiet_roots']+=native_quiet;counts['native_capture_preserved_roots']+=not native_quiet
     counts['native_positive_roots']+=nativeproof['certified'];counts['native_inconclusive_roots']+=nativeproof.get('inconclusive',False)
     counts['root_flagwin_filtered']+=flagwin;counts['root_flagthreat_filtered']+=flagthreat
     forks=[]
     for candidate in sorted(request['candidates'],key=lambda c:c['move']):
      began=time.perf_counter();proof=certify_common(*args,tuple(candidate['move']));elapsed_ms=1000*(time.perf_counter()-began)
      opportunity=(native_quiet and not flagwin and not flagthreat and not nativeproof['certified']and not nativeproof.get('inconclusive')and proof['certified'])
      key=(identity,ply,tuple(candidate['move']))
      if key in controls:
       old=controls[key];assert old['reports']['fork']==proof,(key,'fork');assert old['reports']['native']==nativeproof,(key,'native');counts['first20_exact_parity']+=1
      forks.append(dict(move=candidate['move'],victims=candidate['victims'],proof=proof,elapsed_ms=elapsed_ms,new_opportunity=opportunity))
      counts['candidate_moves']+=1;counts['fork_positive_candidates']+=proof['certified'];counts['fork_inconclusive_candidates']+=proof.get('inconclusive',False);counts['new_opportunity_candidates']+=opportunity
     nodes=nativeproof['enemy_nodes']+sum(f['proof']['enemy_nodes']for f in forks)
     root_opportunity=any(f['new_opportunity']for f in forks)
     within_budget=nodes<=20000 and not nativeproof.get('inconclusive')and not any(f['proof'].get('inconclusive')for f in forks)
     counts['new_opportunity_roots']+=root_opportunity;counts['new_opportunity_roots_within_proposed_global_budget']+=root_opportunity and within_budget
     results.append(dict(game=identity,army=army,ply=ply,native=native,native_quiet=native_quiet,native_proof=nativeproof,native_elapsed_ms=native_ms,root_flagwin=flagwin,root_flagthreat=flagthreat,forks=forks,new_opportunity=root_opportunity,combined_enemy_nodes=nodes,within_proposed_global_budget=within_budget))
     if counts['roots']%20==0:
      progress=dict(completed_roots=counts['roots'],elapsed_seconds=time.perf_counter()-start,counts=dict(counts));(HERE/'all-progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress),flush=True)
    if ply>=max(positions):break
    attacker,defender=p.cells[source],p.cells[target];assert(source,target)in p.moves(ply%2)
    if defender is None:p.move(source,target)
    else:
     _,fallen=p.fight(source,target,attacker[1],defender[1])
     for owner,rank,*_ in fallen:lost[owner][rank]+=1
 assert counts['roots']==335 and counts['candidate_moves']==336 and counts['first20_exact_parity']==20
 counts['new_opportunity_games']=len({r['game']for r in results if r['new_opportunity']})
 counts['new_opportunity_games_within_proposed_global_budget']=len({r['game']for r in results if r['new_opportunity']and r['within_proposed_global_budget']})
 return dict(kind='all-fixed-gate-common-control-proof-audit',strength_evidence=False,counts=dict(counts),cohort_sha256=sha(COHORT),elapsed_seconds=time.perf_counter()-start,sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'EXPANSION-PROTOCOL.json',HERE/'certificate.py',HERE/'certificate_common.py',HERE/'result.json',HERE/'common-result.json')},results=results)
if __name__=='__main__':
 result=run();(HERE/'all-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts'],indent=2));print('seconds',result['elapsed_seconds'])
