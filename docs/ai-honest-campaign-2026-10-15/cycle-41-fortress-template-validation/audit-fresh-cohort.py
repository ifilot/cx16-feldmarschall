import json,hashlib
from pathlib import Path
from feldmarschall import new_rng
b=Path('docs/ai-honest-campaign-2026-10-15');p=b/'cycle-41-fortress-template-validation'
def cohort(plan):
 assert plan['families']==['original-dos']
 rng=new_rng(plan['seed']);rows=[]
 for pair in range(plan['rounds']):
  a=rng.getrandbits(32);enemy=rng.getrandbits(32);move=rng.randrange(1,60000)
  rows.append((enemy,move))
 return rows
current=json.loads((p/'plan.json').read_text());rows=cohort(current);checks=[]
assert len(set(rows))==len(rows)
for q in sorted(b.glob('cycle-*/plan.json')):
 old=json.loads(q.read_text())
 if old['cycle']>=41 or old.get('families')!=['original-dos']:continue
 previous=cohort(old);overlap=set(rows)&set(previous);assert not overlap,(old['cycle'],overlap)
 checks.append(dict(cycle=old['cycle'],pairs=len(previous),joint_private_dos_setup_seed_and_move_seed_overlap=0))
record=dict(master_seed=current['seed'],planned_pairs=len(rows),unique_joint_draws=len(set(rows)),compared_prior_original_dos_only_plans=checks,cohort_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),scope='Design-only reconstruction of RNG draws, without opening any trajectories or outcomes. Matches tournament original-dos-only family loop (two private32bit setup draws, then move seed). Fresh independent cohort with no joint B-private-setup/move draw repeated among these prior plans. Move seeds alone have a deliberately limited16bit range and need not be globally unique; army layouts can repeat under the population by design. Exact frozen runner still generates and audits all armies at execution.')
(p/'fresh-cohort-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS',len(rows),'freshjointdraws vs',len(checks),'priorplans')
