"""Saved full361 summary only: no new game, gate or proof queries."""
import gzip,json,hashlib,sys
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(ROOT/'tools'))
from campaign_mobile_capture import _fork_public_key,_fork_record,_fork_enemy_lost,_fork_own_moves
rows=json.loads(gzip.decompress((HERE/'full361-proofs.json.gz').read_bytes()));result=json.loads((HERE/'full361-result.json').read_text());first20=json.loads(gzip.decompress((HERE/'first20-proofs.json.gz').read_bytes()));original={(r['game'],r['ply']):r for r in first20};comparisons=Counter();games=Counter();witness=Counter();positive=[]
for row in rows:
 f=row['public_fixture'];state={int(k):tuple(v)for k,v in f['shuttle'].items()};army=row['army']
 assert _fork_enemy_lost(f['cells'],army,f['remaining'])==f['lost'];assert row['native_public_verified']
 if(row['game'],row['ply'])in original:
  before=original[row['game'],row['ply']]
  assert before['reports']==row['reports']and before['enemy_nodes']==row['enemy_nodes']and before['public_fixture']==row['public_fixture']
 if not row['incremental']:continue
 def afterkey(move):
  source,target=move;cells=f['cells'][:];moving=cells[source]|64
  if abs(source//10-target//10)+abs(source%10-target%10)>1:moving|=32
  cells[source]=255;cells[target]=moving
  return _fork_public_key(cells,army,f['lost'],f['remaining'],_fork_record(state,army,source,target))
 candidate=row['candidate'];key=hashlib.sha256(json.dumps([afterkey(row['native']),afterkey(candidate['move']),candidate['victim'],candidate['ally']],separators=(',',':')).encode()).hexdigest();comparisons[key]+=1;games[row['game']]+=1
 proof=row['reports']['net'];states=proof.get('responses',[])
 for response in states:
  owner,cells,lost,remaining,red,blue=json.loads(response['public_key']);move=tuple(response['response'])
  assert _fork_enemy_lost(cells,owner,remaining)==lost and move in _fork_own_moves(cells,owner,{0:tuple(red),1:tuple(blue)})
  witness['all']+=1;witness['victim_dead']+=response.get('victim_alive')is False
  if response.get('victim_alive')is False:
   witness['victim_dead_quiet']+=cells[move[1]]==255
   witness['victim_dead_uncertain_capture']+=cells[move[1]]<254 and not cells[move[1]]&32
 positive.append(dict(game=row['game'],ply=row['ply'],native=row['native'],candidate=candidate,bound=proof['minimum_net_material'],normalized_comparison_sha256=key))
summary=dict(kind='saved-full361-normalized-comparison-diagnostics',new_gate_or_proof_queries=0,incremental_roots=len(positive),incremental_games=len(games),normalized_after_action_public_comparisons=len(comparisons),largest_normalized_repeat=max(comparisons.values(),default=0),comparison_definition='Pair of complete masked public states AFTER nativequiet and netquiet, plus net victim/ally roles; drops prior ownshuttle facts forgotten by both actions.',game_distribution=dict(games),incremental_witness_kinds=dict(witness),first20_outputs_inputs_nodes_still_equal=True,positive_roots=positive)
(HERE/'full361-diagnostics.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k!='positive_roots'},indent=2))
