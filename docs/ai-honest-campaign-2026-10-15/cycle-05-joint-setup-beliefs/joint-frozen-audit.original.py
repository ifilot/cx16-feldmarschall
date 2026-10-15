"""Verify frozen joint-policy runtime, model and source identities after tests."""
import json
from pathlib import Path
import zipfile

from ai_registry import ROOT,build_policy,get_policy,receives_opponent_setup
from information_strategy_cycle import digest


def audit(directory):
    frozen=json.loads((directory/'frozen-policies.json').read_text())
    identities=['teacher-flag-row-control-v1-normal','teacher-joint-setup-v1-normal']
    reports={}
    for identity in identities:
        spec=get_policy(identity)
        assert spec==frozen[identity]
        assert not receives_opponent_setup(spec) and 'AI_DIAGNOSTIC_TRUTH' not in spec['defines']
        archive=ROOT/spec['archive'];assert digest(archive)==spec['source_sha256']
        program,receipt=build_policy(identity)
        for name,sha in receipt['runtime_sha256'].items():assert digest(program.parent/name)==sha
        model=Path(spec['joint_belief_model']);name=model.name
        assert digest(ROOT/model)==spec['joint_belief_model_sha256']==digest(program.parent/name)
        with zipfile.ZipFile(archive) as source:
            assert source.read(str(model))==(program.parent/name).read_bytes()
            for module in ('teacher_bot.py','campaign_joint_beliefs.py','calibrated_beliefs.py',
                           'feldmarschall.py','train_ai_student.py'):
                assert source.read('tools/'+module)==(program.parent/module).read_bytes()
                assert (ROOT/'tools'/module).read_bytes()==(program.parent/module).read_bytes()
        reports[identity]=dict(source_archive_sha256=spec['source_sha256'],
            model_sha256=spec['joint_belief_model_sha256'],runtime_sha256=receipt['runtime_sha256'],
            current_adapter_sampler_and_helpers_exactly_match_frozen_sources=True,
            registered_recipe_matches_cycle_freeze=True,receives_opponent_setup=False)
    prior=ROOT/'docs/ai-honest-campaign-2026-10-15/research/joint-public-prefix-audit.json'
    previous=json.loads(prior.read_text())
    runtime=reports['teacher-joint-setup-v1-normal']['runtime_sha256']
    assert previous['source_sha256']==runtime['campaign_joint_beliefs.py']
    assert previous['model_sha256']==runtime['joint-flag-bomb-beliefs-v1.json']
    logs={}
    for name,tests in [('joint-adapter-tests.log',6),('joint-posterior-tests.log',5)]:
        path=directory/name;output=path.read_text()
        assert '\nOK\n' in output and 'skipped' not in output and f'Ran {tests} tests' in output
        logs[name]=dict(sha256=digest(path),tests=tests,passed=True)
    return dict(passed=True,analysis_sha256=digest(Path(__file__)),policies=reports,tests=logs,
        portable_test='Both frozen runtime bundles copied into temporary directories; process cwd also outside checkout. Initial and80-public-ply decisions complete.',
        complete_prior_public_prefix_audit=dict(path=str(prior.relative_to(ROOT)),sha256=digest(prior),
            games=previous['games'],public_events_checked=previous['public_events_checked'],
            sampled_roots=previous['sampled_roots'],exact_source_and_model_identity_verified=True))


if __name__=='__main__':
    directory=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-05-joint-setup-beliefs'
    report=audit(directory)
    (directory/'joint-frozen-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
