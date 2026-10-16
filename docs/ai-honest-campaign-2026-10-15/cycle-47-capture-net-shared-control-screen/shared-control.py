"""Explicit prospective reuse of C43's frozen control, never new control games."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools'))
from tournament_store import Tournament
HERE=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(prepare):
 plan=json.loads((HERE/'plan.json').read_text());shared=plan['shared_control'];identity=shared['policy']
 source=HERE.parent/shared['directory'];origin=source/(identity+'.fmtour');destination=HERE/origin.name
 assert shared['source_games_at_design']==0 and shared['seed']==plan['seed']==2530001
 sourceplan=json.loads((source/'plan.json').read_text())
 for field in('baseline','opponent','seed','rounds','families','max_plies','backend','setup_mode'):
  assert sourceplan[field]==plan[field],field
 for identity in(plan['baseline'],plan['opponent']):
  assert json.loads((source/'frozen-policies.json').read_text())[identity]==json.loads((HERE/'frozen-policies.json').read_text())[identity]
 with Tournament(origin)as saved:
  assert saved.metadata()['status']=='complete'and len(saved.games())==1000
  before=[saved.game(row['id'])for row in saved.games()]
 if prepare:
  assert not destination.exists()
  assert origin.stat().st_mtime>=json.loads((HERE/'registration.json').read_text())['epoch']
  shutil.copy2(origin,destination)
  shutil.copy2(origin.with_suffix('.log'),destination.with_suffix('.log'))
 with Tournament(destination)as saved:
  assert saved.metadata()['status']=='complete'
  after=[saved.game(row['id'])for row in saved.games()]
 assert before==after and len(before)==1000
 # Read-only reviews preserve the entire saved database, including execution metadata.
 assert digest(origin)==digest(destination)
 receipt=dict(passed=True,prospective=True,shared_control_games=1000,new_control_games=0,
  source=str(origin.relative_to(ROOT)),destination=str(destination.relative_to(ROOT)),
  source_sha256=digest(origin),destination_sha256=digest(destination),
  source_plan_sha256=digest(source/'plan.json'),destination_plan_sha256=digest(HERE/'plan.json'),
  declaration=shared,all_saved_game_fields_exactly_equal=True,
  interpretation='Same physical control execution, counted once in campaign execution totals; neither independent replication nor a fresh validation cohort.')
 (HERE/'shared-control-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 if not prepare:
  result=json.loads((HERE/'result.json').read_text())
  assert result['attempts']==2000 and result['verified_games']==2000
  result.update(new_attempts=1000,reused_control_attempts=1000,shared_control_receipt_sha256=digest(HERE/'shared-control-receipt.json'),shared_control=shared)
  (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','audit'])
 run(parser.parse_args().action=='prepare')
