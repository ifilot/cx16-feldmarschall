"""No new proofs: validate saved metadata, witness coverage and correction parity."""
import gzip,hashlib,json,sys,statistics
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_mobile_capture import _fork_enemy_lost,_fork_own_moves,_fork_public_key,_fork_record
from tournament_store import Tournament
HERE=Path(__file__).resolve().parent
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 data=json.loads((HERE/'runtime-audit.json').read_text());before=json.loads((HERE/'initial-input-aliasing/runtime-audit.json').read_text())
 assert data['counts']==before['counts']
 full=json.loads(gzip.decompress((HERE/'full-public-proofs.json.gz').read_bytes()));old=json.loads(gzip.decompress((HERE/'initial-input-aliasing/full-public-proofs.json.gz').read_bytes()))
 guard_before=json.loads(gzip.decompress((HERE/'before-input-guard/full-public-proofs.json.gz').read_bytes()))
 assert len(full)==len(old)==len(guard_before)==335
 for a,b in zip(full,guard_before):
  assert a['report']==b['report']and a['witness_plan']==b['witness_plan']and a['public_fixture']==b['public_fixture']
 assert data['counts']==json.loads((HERE/'before-input-guard/runtime-audit.json').read_text())['counts']
 metadata=Counter();game_counts=Counter();comparison_counts=Counter();nodes=[];times=[];response_states=0;requests={}
 for row in full:requests.setdefault(row['game'],{})[row['ply']]=row
 for a,b in zip(full,old):
  assert(a['game'],a['ply'])==(b['game'],b['ply'])
  assert a['report']==b['report']and a['witness_plan']==b['witness_plan']
  for name in('lost','shuttle','remaining','cells'):
   if a['public_fixture'][name]!=b['public_fixture'][name]:metadata[name]+=1
  fixture=a['public_fixture'];state={int(k):tuple(v)for k,v in fixture['shuttle'].items()}
  assert _fork_enemy_lost(fixture['cells'],a['army'],fixture['remaining'])==fixture['lost']
  nodes.append(a['enemy_nodes']);times.append(a['elapsed_ms'])
  if a['overridden']:
   game_counts[a['game']]+=1
   proof=next(entry['proof']for entry in a['report']['fork_certificates']if entry['move']==a['selected'])
   assert len(a['witness_plan'])==len(proof['responses'])==proof['first_public_outcomes']
   for response in proof['responses']:
    key=response['public_key'];move=a['witness_plan'][key];assert move==response['response']
    army,cells,lost,remaining,red,blue=json.loads(key)
    assert _fork_enemy_lost(cells,army,remaining)==lost
    assert tuple(move)in _fork_own_moves(cells,army,{0:tuple(red),1:tuple(blue)})
    response_states+=1
   def afterkey(move):
    source,target=move;cells=fixture['cells'][:];moving=cells[source]|64
    if abs(source//10-target//10)+abs(source%10-target%10)>1:moving|=32
    cells[target]=moving;cells[source]=255
    return _fork_public_key(cells,a['army'],fixture['lost'],fixture['remaining'],_fork_record(state,a['army'],source,target))
   key=hashlib.sha256((afterkey(a['native'])+'|'+afterkey(a['selected'])).encode()).hexdigest();comparison_counts[key]+=1
 with Tournament(COHORT)as saved:
  for identity,positions in requests.items():
   game=saved.game(identity);state={0:(None,None,0),1:(None,None,0)}
   for ply,(source,target)in enumerate(game['moves']):
    if ply in positions:
     actual={int(k):tuple(v)for k,v in positions[ply]['public_fixture']['shuttle'].items()}
     assert actual==state,(identity,ply,actual,state)
    if ply>=max(positions):break
    state=_fork_record(state,ply%2,source,target)
 return dict(kind='saved-runtime-evidence-integrity',new_proof_queries=0,all335_counts_reports_plans_identical_after_metadata_fix=True,all335_inputs_counts_reports_plans_identical_after_input_guard=True,corrected_metadata_fields=dict(metadata),all335_inventory_and_recorded_public_shuttles_valid=True,witness_states_verified=response_states,all_selected_plans_cover_every_public_enemy_outcome=True,override_games=dict(game_counts),distinct_public_comparisons=len(comparison_counts),largest_repeated_comparison=max(comparison_counts.values(),default=0),timing_ms=dict(mean=statistics.mean(times),median=statistics.median(times),maximum=max(times)),enemy_outcome_attempts=dict(mean=statistics.mean(nodes),maximum=max(nodes),cap_note='A cap reports attempted20001; only20000successors are yielded.'),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'runtime-audit.json',HERE/'full-public-proofs.json.gz',HERE/'initial-input-aliasing/runtime-audit.json')})
if __name__=='__main__':
 result=run();(HERE/'runtime-integrity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
