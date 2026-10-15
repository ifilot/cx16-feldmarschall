"""Audit the frozen three-arm experiment and bind its complete evidence."""
from collections import defaultdict
import copy
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

import ai_registry
from ai_registry import ROOT, catalog, get_policy, receives_opponent_setup
from information_strategy_cycle import digest, validate_metadata
from restrained_search_cycle import OUT, config_path, matches, write
from root_policy import RootPolicy
from tournament_store import Tournament


def rebuild(out,plan):
    results={}
    for key in ('control','candidate'):
        spec=get_policy(plan[key])
        _,original=ai_registry.build_policy(spec['id'])
        with tempfile.TemporaryDirectory(prefix='restrained-clean-build-') as temp:
            isolated=Path(temp)
            target=isolated/spec['archive'];target.parent.mkdir(parents=True)
            shutil.copy2(ROOT/spec['archive'],target)
            try:
                ai_registry.ROOT=isolated
                _,receipt=ai_registry.build_policy(spec['id'],policy=spec)
            finally:ai_registry.ROOT=ROOT
            assert receipt['runtime_sha256']==original['runtime_sha256']
        results[spec['id']]=dict(exact_all_runtime_hashes=True,runtime_sha256=receipt['runtime_sha256'])
    write(out/'checks/clean-rebuild.json',results)
    return results


def audit(out=OUT):
    plan=json.loads((out/'plan.json').read_text())
    frozen=json.loads((out/'frozen-policies.json').read_text())
    before=json.loads((out/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)]==before
    assert all(get_policy(p)==spec for p,spec in frozen.items())
    report=json.loads((out/'strength-report.json').read_text())
    result=json.loads((out/'result.json').read_text())
    settings={}
    external={}
    playing_source=None
    for key in ('control','candidate'):
        spec=frozen[plan[key]]
        assert not receives_opponent_setup(spec)
        assert spec['difficulty']=='normal'
        assert spec['defines']==frozen[plan['baseline']]['defines']
        assert spec['teacher_defines']==frozen[plan['baseline']]['teacher_defines']
        assert spec['driver_args'][:-2]==frozen[plan['baseline']]['driver_args']
        assert spec['driver_args'][-2]=='--root-policy'
        for forbidden in ('--belief-model','--diagnostic-truth','--information-strategy'):
            assert forbidden not in spec['driver_args']
        assert 'AI_DIAGNOSTIC_TRUTH' not in spec['defines']
        assert digest(ROOT/spec['archive'])==spec['source_sha256']
        assert digest(ROOT/spec['root_policy'])==spec['root_policy_sha256']
        settings[key]=json.loads((ROOT/spec['root_policy']).read_text())
        assert settings[key]['calibration_roots_sha256']==digest(out/'development-roots.json')
        external[spec['archive']]=spec['source_sha256']
        external[spec['root_policy']]=spec['root_policy_sha256']
        with zipfile.ZipFile(ROOT/spec['archive']) as archive:
            source={name:archive.read('tools/'+name) for name in ('teacher_bot.py','root_policy.py','train_ai_student.py')}
            if playing_source is None:playing_source=source
            assert playing_source==source,'control/restraint playing code differs'
            assert archive.read(spec['root_policy'])==(ROOT/spec['root_policy']).read_bytes()
            receipt=json.loads((ROOT/'build/ai-catalog'/spec['id']/'build.json').read_text())
            assert receipt['policy']==spec
            for name,sha in receipt['runtime_sha256'].items():
                runtime=ROOT/'build/ai-catalog'/spec['id']/name
                assert digest(runtime)==sha
                if name in source:assert runtime.read_bytes()==source[name]
    control=copy.deepcopy(settings['control']);candidate=copy.deepcopy(settings['candidate'])
    assert control.pop('mode')=='probability-control'
    assert candidate.pop('mode')=='kl-restrained'
    assert control==candidate,'settings differ beyond presence of KL constraint'
    calibration=json.loads((out/'calibration.json').read_text())
    assert calibration['roots']==280 and calibration['nonwinning_roots']>0
    roots=json.loads((out/'development-roots.json').read_text())
    assert len(roots['roots'])==280
    assert set(roots['families'])==set(plan['families'])
    assert all(value==40 for value in roots['families'].values())
    assert roots['samples']==8 and roots['depth']==4
    # Recompute every diagnostic from its retained, common rollout values.
    original_mechanism=json.loads((out/'mechanism.json').read_text())
    policies={key:RootPolicy(settings[key]) for key in ('control','candidate')}
    eligible=[r for r in roots['roots'] if max(v['parent_score'] for v in r['report']['values'])<30000]
    assert original_mechanism['roots']==len(eligible)
    for row,saved in zip(eligible,original_mechanism['records']):
        scores={tuple(v['move']):v['parent_score'] for v in row['report']['values']}
        corrections={tuple(v['move']):v['correction'] for v in row['report']['values']}
        for key,policy in policies.items():
            actual=policy.distribution(scores,corrections)
            retained=saved['policies'][policy.mode]
            assert actual['probabilities']==retained['probabilities']
            assert actual['kl']==retained['kl']
    development=json.loads((out/'development-verification.json').read_text())
    assert development['tournament_sha256']==digest(out/'development.fmtour')
    assert development['verification']['python_replayed']==140
    assert development['verification']['native_replayed_all_states']==140
    seen_development=set()
    with Tournament(out/'development.fmtour') as tournament:
        assert tournament.metadata()['seed']==plan['development']['seed']
        for row in tournament.games():
            game=tournament.game(row['id'])
            seen_development.add((game['family'],game['seed'],game['red_setup'],game['blue_setup']))
    games,states,errors=0,0,0
    signatures={}
    for match in matches(plan):
        path=out/'validation'/(match['name']+'.fmtour')
        validate_metadata(path,match,plan,frozen)
        analysis=report['matches'][match['name']]
        assert analysis['tournament_sha256']==digest(path)
        expected=match['rounds']*14
        assert analysis['verification']['python_replayed']==expected
        assert analysis['verification']['native_replayed_all_states']==expected
        assert path.with_suffix('.png').is_file()
        assert path.with_suffix('.review.log').is_file()
        signatures[match['name']]=[]
        with Tournament(path) as tournament:
            for row in tournament.games():
                game=tournament.game(row['id'])
                signature=(game['family'],game['seed'],game['red_setup'],game['blue_setup'])
                assert signature not in seen_development,'development game reused in validation'
                signatures[match['name']].append(signature)
                games+=1;states+=game['plies']+1;errors+=game['result']=='error'
    assert games==2100 and result['validation_attempts']==games
    assert errors==result['unscored_errors']
    dos_signatures=[signatures['dos--'+plan[key]] for key in ('baseline','control','candidate')]
    assert dos_signatures[0]==dos_signatures[1]==dos_signatures[2]
    head_signatures=[signatures[m['name']] for m in matches(plan) if m['group']=='head']
    assert head_signatures[0]==head_signatures[1]==head_signatures[2]
    for log in ('root-policy.log','adapter.log','truth-boundary.log','tournaments.log','original-knowledge.log'):
        text=(out/'checks'/log).read_text()
        assert '\nOK\n' in text and 'FAILED' not in text and 'skipped=' not in text,log
    parity=json.loads((out/'checks/frozen-parent-parity.json').read_text())
    assert parity['passed'] and parity['tested_decisions']>=140 and parity['samples']==8
    rebuilds=json.loads((out/'checks/clean-rebuild.json').read_text())
    assert all(rebuilds[plan[k]]['exact_all_runtime_hashes'] for k in ('control','candidate'))
    assert result['strength_gate_passed']==report['strength_gate_passed']
    outcome=dict(passed=True,previous_policies_unchanged=len(before),new_policies=[plan['control'],plan['candidate']],
                 settings_differ_only_in_constraint=True,development_public_roots=280,exact_frozen_parent_parity_roots=parity['tested_decisions'],
                 original_sampler_eight_worlds=True,unchanged_four_ply_search=True,separate_selection_rng=True,
                 runtime_hashes_reproduced_from_clean_archives=True,validation_games=games,
                 replayed_validation_states=states,unscored_original_dos_errors=errors,
                 fresh_cohorts=True,matched_dos_armies_and_seeds=True,matched_head_armies_and_seeds=True,
                 qt6_validation_captures=6,development_games_replayed=140,
                 original_flag_spy_knowledge_rechecked_both_orientations=True,
                 mechanism_supported=result['mechanism_supported'],practical_gain_supported=result['practical_gain_supported'],
                 strength_gate_passed=result['strength_gate_passed'])
    write(out/'completion-audit.json',outcome)
    # Archive the full final Python framework. Immutable playing archives also
    # preserve the exact earlier registration-time framework and settings.
    with zipfile.ZipFile(out/'framework-source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT/'tools').glob('*.py')):archive.write(path,'tools/'+path.name)
    manifest={str(path.relative_to(out)):digest(path) for path in sorted(out.rglob('*'))
              if path.is_file() and path.name!='manifest.json'}
    write(out/'manifest.json',dict(sha256=manifest,external_sha256=external))
    return outcome


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild-only',action='store_true')
    args=parser.parse_args()
    plan=json.loads((OUT/'plan.json').read_text())
    print(json.dumps(rebuild(OUT,plan) if args.rebuild_only else audit(),indent=2))
