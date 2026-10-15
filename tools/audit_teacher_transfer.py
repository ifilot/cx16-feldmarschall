"""Verify bounded transfer trial sources, model metrics, gates and retained probes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from ai_registry import ROOT, build_policy, get_policy
from train_ranking_student import metrics

BASE=ROOT/'docs/ai-transfer-2026-10-15'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def header(model,version):
    lines=[f'/* Ranking Student v{version}: additive desktop model; immutable trial. */','#define ENSEMBLE_TREES 64','#define ENSEMBLE_SCALE 1000','static const ensemble_node_t ensemble_nodes[] = {']
    offsets=[];n=0
    for tree in model['trees']:
        offsets.append(n);n+=len(tree)
        assert len(tree)<=255
        for node in tree:
            assert node['feature']==255 or 0<=node['feature']<16
            lines.append('    {'+','.join(str(node[k]) for k in ('feature','threshold','left','right','value'))+'},')
    lines+=['};','static const unsigned int ensemble_offsets[] = {'+','.join(map(str,offsets))+'};']
    return ('\n'.join(lines)+'\n').encode()

def audit():
    started=datetime(2026,10,15,11,8,tzinfo=timezone.utc)
    policies=[];root_sets=[]
    for version,folder,planfile,policyfile,runtimefile in (
        (1,'model','plan.json','policy.json','ranking-runtime.json'),
        (2,'coverage-repair-model','coverage-repair-plan.json','coverage-repair-policy.json','ranking-v2-runtime.json')):
        identity=f'ranking-student-v{version}-normal';policy=get_policy(identity)
        assert policy==json.loads((BASE/policyfile).read_text()) and policy['status']=='rejected-offline'
        assert sha(ROOT/policy['archive'])==policy['source_sha256']
        model=json.loads((BASE/folder/'model.json').read_text())
        assert model['plan_sha256']==sha(BASE/planfile)
        assert model['corpus_sha256']==sha(ROOT/'docs/ai-cycle-2026-10-15/student-model/training-evidence.zip')
        assert model['input_sha256']==sha(BASE/folder/'ranking-inputs.zip')
        with zipfile.ZipFile(BASE/folder/'ranking-inputs.zip') as bundle:
            raw=bundle.read('roots.jsonl');roots=[json.loads(l) for l in raw.splitlines()]
        root_sets.append(raw)
        training=[r for r in roots if not r['validation']];held=[r for r in roots if r['validation']]
        assert len(roots)==320 and len(training)==267 and len(held)==53
        assert not {r['group'] for r in training}&{r['group'] for r in held}
        assert metrics(training,model['trees'])==model['training']
        assert metrics(held,model['trees'])==model['held_out']
        assert not model['offline_gate_passed']
        gate=model['held_out' if version==1 else 'training']['mean_improvement']>0
        assert not gate
        expected=header(model,version)
        assert expected==(BASE/folder/'ai_student_ensemble.h').read_bytes()
        with zipfile.ZipFile(ROOT/policy['archive']) as bundle:
            assert bundle.read(f'docs/ai-transfer-2026-10-15/{folder}/ai_student_ensemble.h')==expected
            assert bundle.read('src/core/ai_student_model_production.h')==(ROOT/'src/core/ai_student_model_production.h').read_bytes()
            for name in ('src/core/ai_student.c','src/core/ai_mission.c','src/core/ai_mission.h','src/native/engine.c'):
                assert bundle.read(name)==(ROOT/name).read_bytes()
        executable,receipt=build_policy(identity)
        runtime=json.loads((BASE/'checks'/runtimefile).read_text())
        assert runtime['policy']==policy and runtime['runtime']==receipt
        assert runtime['counts']['held_out_positions']==53
        assert runtime['counts']['full_history_actions']==1246
        assert runtime['counts']['cold_actions']==1246
        assert abs(runtime['native_mean_regret_improvement']-model['held_out']['mean_improvement'])<1e-10
        probe='ensemble-runtime-probes.zip' if version==1 else 'ranking-v2-runtime-probes.zip'
        with zipfile.ZipFile(BASE/'checks'/probe) as bundle:
            assert bundle.testzip() is None
            report=json.loads(bundle.read('report.json'))
            assert report==runtime
        policies.append(dict(id=identity,source_sha256=policy['source_sha256'],model_sha256=sha(BASE/folder/'model.json'),header_sha256=sha(BASE/folder/'ai_student_ensemble.h'),executable_sha256=sha(executable),nodes=model['node_count'],training_regret=model['training']['student_regret'],old_held_out_regret=model['held_out']['student_regret'],offline_gate_passed=False))
    assert root_sets[0]==root_sets[1]
    original_plan=json.loads((BASE/'plan.json').read_text());repair_plan=json.loads((BASE/'coverage-repair-plan.json').read_text())
    assert repair_plan['original_plan_sha256']==sha(BASE/'plan.json')
    assert original_plan['tournament']['league_seed']!=repair_plan['tournament']['league_seed']
    assert not list(BASE.rglob('*.fmtour'))
    stability=json.loads((BASE/'checks/stability.json').read_text())
    assert stability['summary']['positions']==32 and stability['summary']['agreed_choices']==23
    assert stability['summary']['observer_production_parity']==32
    objective=json.loads((BASE/'checks/ranking-objective-audit.json').read_text())
    assert objective['frozen_observer_parity']['positions']==320 and objective['frozen_observer_parity']['actions']==7754 and objective['frozen_observer_parity']['all_match']
    representability=json.loads((BASE/'checks/representability.json').read_text())
    assert representability['all']['teacher_best_reachable']==318
    production_log=(BASE/'checks/production.log').read_text()
    for expected in ('15163 hidden-permutation decisions','3836 Silent Defense','native information: all disclosure/casualty checks passed'):
        assert expected in production_log
    # The original production header itself is immutable, not merely unchanged
    # relative to these experimental source archives.
    production=get_policy('student-guard-v1-normal')
    with zipfile.ZipFile(ROOT/production['archive']) as bundle:
        assert bundle.read('src/core/ai_student_model_production.h')==(ROOT/'src/core/ai_student_model_production.h').read_bytes()
    now=datetime.now(timezone.utc)
    # Re-auditing later must not rewrite when the bounded work completed.
    completion_path=BASE/'completion.json'
    if completion_path.exists():
        completed=datetime.fromisoformat(json.loads(completion_path.read_text())['completed_utc'])
    else:
        completed=now
        completion_path.write_text(json.dumps(dict(started_utc=started.isoformat(),completed_utc=completed.isoformat(),requested_limit_seconds=2400),indent=2)+'\n')
    evidence={str(p.relative_to(BASE)):sha(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name!='audit.json'}
    report=dict(status='COMPLETE',started_utc=started.isoformat(),completed_utc=completed.isoformat(),audited_utc=now.isoformat(),elapsed_seconds=(completed-started).total_seconds(),requested_limit_seconds=2400,within_requested_limit=(completed-started).total_seconds()<=2400,policies=policies,source_positions=320,source_actions=7754,teacher_stability=dict(positions=32,agreement=23),production_unchanged=True,new_strength_games=0,tournament_gate='Both offline gates failed; original and repair strength cohorts unused.',fits='Two distinct fixed model designs. The original deterministic fit reran unchanged after a JSON scalar serialization failure. One explicit all-action coverage repair, no further fits.',scope='No playing-strength gain, no X16 feasibility claim, no promotion. V2 old heldout is development only.',evidence_sha256=evidence,audit_source_sha256=sha(Path(__file__)))
    (BASE/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='evidence_sha256'},indent=2))

if __name__=='__main__':audit()
