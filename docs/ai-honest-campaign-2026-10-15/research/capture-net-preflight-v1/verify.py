"""Verify preserved copies and public witnesses; no new proof or cohort queries."""
import gzip,json,hashlib,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from campaign_mobile_capture import _fork_valid_inventory,_fork_own_moves,_fork_public_key
from net import own_outcomes
from campaign_belief_values import worths
proofs=json.loads(gzip.decompress((HERE/'first20-proofs.json.gz').read_bytes()));gate=json.loads((HERE/'gate.json').read_text());freeze=json.loads((HERE/'SOURCE-FREEZE.json').read_text())
for name,expected in freeze['files'].items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==expected
verified=0;positive=[]
for row in proofs:
 f=row['public_fixture'];state={int(k):tuple(v)for k,v in f['shuttle'].items()};army=row['army']
 assert row['native_public_verified'];assert _fork_valid_inventory(f['cells'],army,f['lost'],f['remaining'])
 assert _fork_public_key(f['cells'],army,f['lost'],f['remaining'],state)==row['public_key']
 assert tuple(row['native'])in _fork_own_moves(f['cells'],army,state)
 for proof in row['reports'].values():
  if not proof['certified']:continue
  responses=proof.get('responses',[]);assert len(responses)==proof['first_public_outcomes']
  assert len({r['public_key']for r in responses})==len(responses)
  for r in responses:
   side,board,lost,remaining,red,blue=json.loads(r['public_key']);shuttle={0:tuple(red),1:tuple(blue)}
   assert side==army and _fork_valid_inventory(board,side,lost,remaining)
   move=tuple(r['response']);assert move in _fork_own_moves(board,side,shuttle)
   assert list(own_outcomes(board,side,remaining,shuttle,move,worths(f['lost'])))
   verified+=1
 if row['incremental']:positive.append(row)
result=dict(kind='saved-capture-net-evidence-integrity',new_proof_queries=0,source_freeze_verified=True,all20_copied_inventory_public_keys_and_native_replays_verified=True,legal_public_witnesses_verified=verified,all_positive_proofs_cover_every_first_public_outcome=True,positive_roots=[dict(game=r['game'],ply=r['ply'],candidate=r['candidate'],bound=r['reports']['net']['minimum_net_material'])for r in positive],distinct_positive_public_roots=len({r['public_key']for r in positive}),root_time_ms=dict(mean=statistics.mean(r['elapsed_ms']for r in proofs),median=statistics.median(r['elapsed_ms']for r in proofs),maximum=max(r['elapsed_ms']for r in proofs)),root_enemy_outcome_attempts=dict(mean=statistics.mean(r['enemy_nodes']for r in proofs),maximum=max(r['enemy_nodes']for r in proofs)),gate_unselected_roots=sum(not r['native_selected_eligible']for r in gate['records']))
(HERE/'integrity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
