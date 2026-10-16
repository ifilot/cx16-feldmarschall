"""All361 copied screening inputs: exact research/runtime mechanism parity."""
import gzip,hashlib,json,sys,time,statistics
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(ROOT/'tools'))
from campaign_capture_net import net_selection
from campaign_mobile_capture import _fork_own_moves
RESEARCH=HERE.parent/'capture-net-preflight-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 rows=json.loads(gzip.decompress((RESEARCH/'full361-proofs.json.gz').read_bytes()));counts=Counter();results=[];times=[];start=time.perf_counter()
 for index,row in enumerate(rows):
  f=row['public_fixture'];state={int(k):tuple(v)for k,v in f['shuttle'].items()};scores=dict.fromkeys(_fork_own_moves(f['cells'],row['army'],state),0);parent=tuple(row['native']);began=time.perf_counter()
  selected,report=net_selection(f['cells'],row['army'],f['lost'],f['remaining'],scores,parent,state);elapsed=1000*(time.perf_counter()-began);times.append(elapsed)
  assert report['first_candidate']==row['candidate'];assert report['native_certificate']==row['reports']['native']
  if not row['reports']['native'].get('inconclusive'):assert report['net_certificate']==row['reports']['net']
  assert report['enemy_nodes']==row['enemy_nodes']
  expected=tuple(row['candidate']['move'])if row['incremental']else parent;assert selected==expected
  if row['incremental']:assert report['witness_plan']=={r['public_key']:tuple(r['response'])for r in row['reports']['net']['responses']}
  else:assert not report.get('witness_plan')
  counts['roots']+=1;counts['overrides']+=selected!=parent;counts[report['reason']]+=1;counts['witness_states']+=len(report.get('witness_plan',{}))
  results.append(dict(game=row['game'],ply=row['ply'],native=parent,selected=selected,enemy_nodes=report['enemy_nodes'],reason=report['reason'],witness_states=len(report.get('witness_plan',{})),elapsed_ms=elapsed))
  if(index+1)%25==0:print(json.dumps(dict(roots=index+1,seconds=time.perf_counter()-start)),flush=True)
 result=dict(kind='all361-runtime-research-exact-parity',strength_evidence=False,all_candidates_proofs_nodes_witnesses_and_selected_moves_exact=True,counts=dict(counts),elapsed_seconds=time.perf_counter()-start,root_time_ms=dict(mean=statistics.mean(times),median=statistics.median(times),maximum=max(times)),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),RESEARCH/'full361-proofs.json.gz',ROOT/'tools/campaign_capture_net.py',ROOT/'tools/campaign_native_mobile.py',ROOT/'tools/campaign_mobile_capture.py')},results=results)
 (HERE/'runtime-parity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('results','sources')},indent=2))
if __name__=='__main__':run()
