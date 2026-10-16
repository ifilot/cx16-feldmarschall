"""Independent inner-guard SQL/integer arithmetic and saved-evidence review."""
import hashlib,json,math,random,sqlite3,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import get_policy,receives_opponent_setup
from tournament_store import verify

BASE=ROOT/'docs/ai-honest-campaign-2026-10-16';HERE=BASE/'research/evaluation';factor=BASE/'research/inner-guard/factorial-result.json'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def refresh(directory):
 manifest={str(p.relative_to(directory)):sha(p)for p in sorted(directory.rglob('*'))if p.is_file()and p.name!='manifest.json'}
 (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def run():
 joint=json.loads(factor.read_text());raw={};reviews={}
 for cycle in(110,114):
  directory=next(BASE.glob('cycle-'+str(cycle)+'*'));plan=json.loads((directory/'plan.json').read_text());result=json.loads((directory/'result.json').read_text());frozen=json.loads((directory/'frozen-policies.json').read_text());audit=json.loads((directory/'audit.json').read_text());assert audit['passed']
  for identity,policy in frozen.items():assert get_policy(identity)==policy;assert sha(ROOT/policy['archive'])==policy['source_sha256']
  for identity in plan['policies']:
   assert not receives_opponent_setup(frozen[identity]);path=directory/(identity+'.fmtour');verify(path)
   report=json.loads(path.with_suffix('.report.json').read_text());assert report['tournament_sha256']==sha(path)
   assert report['verification']['python_replayed']==256 and report['verification']['native_replayed_all_states']==256
   assert path.with_suffix('.png').is_file()
   own=json.loads(path.with_suffix('.setups-audit.json').read_text());dos=json.loads(path.with_suffix('.original-dos-setups-audit.json').read_text())
   assert own['passed']and own['tournament_sha256']==sha(path)and own['verified_games']==256 and own['no_opponent_input']and own['all_streams_repeatable']
   assert dos['passed']and dos['regenerated_records']==256 and dos['matched_game_armies']==256
   connection=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);connection.row_factory=sqlite3.Row
   data=[dict(row)for row in connection.execute('SELECT id,pair_id,red,blue,seed,red_setup,blue_setup,result FROM games ORDER BY id')];connection.close()
   rows={}
   for row in data:
    side='red'if row['red']==identity else'blue';units=None if row['result']=='error'else 1 if row['result']=='draw'else 2 if row[row['result']]==identity else 0
    rows[row['pair_id'],side]=(units,row)
   raw[identity]=rows
  baseline,candidate=plan['baseline'],plan['contrasts'][0][0];effects=[]
  for pair_id in range(1,129):
   units=[raw[identity][pair_id,side][0]for identity in(candidate,baseline)for side in('red','blue')]
   if None not in units:effects.append((sum(units[:2])-sum(units[2:]))/4)
  saved=result['comparisons'][candidate+' minus '+baseline]['metrics']['score'];assert abs(sum(effects)/len(effects)-saved['mean'])<1e-12
  divergence=json.loads((directory/'divergence.json').read_text());assert divergence['summary']['excluded_different_own_armies']==256 and divergence['summary']['trajectory_comparable_games']==0
  assert 'original-dos'in result['family_standings'][baseline]
  with zipfile.ZipFile(ROOT/frozen[candidate]['archive'])as archive:
   source=archive.read('tools/new_campaign_inner_guard_deploy.c').decode();assert'AI_FORTRESS_INNER_GUARD'in source and'21 / BOARD_SIZE'in source and'34 / BOARD_SIZE'in source
  refresh(directory)
  review=dict(passed=True,cycle=cycle,attempts=512,errors_preserved_unscored=result['errors'],full_independent_python_replays=512,native_all_state_report_hashes_checked=512,
   own_deployment_streams_reproduced=2,original_dos_armies_reproduced=512,immutable_honest_policy_checks=True,same_root_trajectory_games=0,placement_treatment_games_excluded_from_same_root_claims=256,
   own_complete_pairs=len(effects),independent_integer_score_mean=sum(effects)/len(effects),manifest_files_verified=len(json.loads((directory/'manifest.json').read_text())),manifest_sha256=sha(directory/'manifest.json'))
  reviews[cycle]=review;(HERE/f'cycle-{cycle}-independent-review.json').write_text(json.dumps(review,indent=2)+'\n')
 # Separate direct SQL integer reconstruction; never use helper arm means or its pair interactions.
 labels=('book_base','book_guard','native_base','native_guard');signs=(-1,1,1,-1);values=[];lower=upper=0;arm_common={label:[]for label in labels}
 for pair_id in range(1,129):
  block={label:[raw[joint['sources'][label]['policy']][pair_id,side][0]for side in('red','blue')]for label in labels}
  for label in labels:
   source=joint['sources'][label];assert sha(source['path'])==source['sha256']
  known=all(None not in block[label]for label in labels)
  if known:
   values.append(sum(sign*sum(block[label])for label,sign in zip(labels,signs)))
   for label in labels:arm_common[label].append(sum(block[label])/4)
  for label,sign in zip(labels,signs):
   for units in block[label]:
    lower+=sign*((0 if sign>0 else 2)if units is None else units)
    upper+=sign*((2 if sign>0 else 0)if units is None else units)
 assert len(values)==joint['common_four_arm_complete_pairs'];mean=sum(values)/(4*len(values));bounds=[lower/(4*128),upper/(4*128)]
 assert mean==joint['common_complete_case_interaction']['mean']and bounds==joint['all_planned_pairs_arbitrary_error_bounds']
 rng=random.Random(3110114);n=len(values);sample=sorted(sum(values[rng.randrange(n)]for _ in range(n))/(4*n)for _ in range(20000));interval=[sample[math.floor(.025*19999)],sample[math.ceil(.975*19999)]];assert interval==joint['common_complete_case_interaction']['interval_95']
 assert sha(ROOT/'tools/new_campaign_inner_guard_factorial.py')==joint['helper_sha256']
 assert sha(joint['protocol']['path'])==joint['protocol']['sha256']
 review=dict(passed=True,source='Independent SQL scores represented as integer half-point units; no helper analysis functions imported',actual_distinct_policy_executions=4,total_attempts=1024,common_four_arm_complete_pairs=n,
  identical_within_placement_own_armies_verified_by_frozen_helper=True,common_four_arm_interaction=mean,independent_20000_bootstrap_interval_95=interval,
  arbitrary_error_bounds_all128pairs=bounds,common_cohort_arm_scores={label:sum(v)/len(v)for label,v in arm_common.items()},factorial_result_sha256=sha(factor),protocol_sha256=joint['protocol']['sha256'],helper_source_sha256=joint['helper_sha256'],
  conclusion='No established interaction. Distinct within-study complete-case means were never subtracted; errors remain unscored and bounded separately.')
 (HERE/'inner-guard-factorial-independent-review.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(dict(studies=reviews,joint=review),indent=2))
if __name__=='__main__':run()
