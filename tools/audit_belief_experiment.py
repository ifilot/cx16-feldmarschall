"""Completion audit binding the calibrated-belief model, sources and evidence."""
import hashlib
import json
from pathlib import Path
import zipfile

from ai_registry import ROOT, catalog, digest, get_policy, receives_opponent_setup
from belief_experiment import OUT, rows, write
from tournament_store import Tournament


def audit(out=OUT):
    plan=json.loads((out/'plan.json').read_text())
    frozen=json.loads((out/'frozen-policies.json').read_text())
    before=json.loads((out/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)]==before
    assert all(get_policy(p)==spec for p,spec in frozen.items())
    policy=frozen[plan['candidate']]
    assert not receives_opponent_setup(policy)
    assert 'AI_DIAGNOSTIC_TRUTH' not in policy['defines']
    assert '--diagnostic-truth' not in policy['driver_args']
    assert policy['defines']==frozen[plan['baseline']]['defines']
    assert policy['teacher_defines']==frozen[plan['baseline']]['teacher_defines']
    assert policy['driver_args'][:-2]==frozen[plan['baseline']]['driver_args']
    assert digest((ROOT/policy['archive']).read_bytes())==policy['source_sha256']
    with zipfile.ZipFile(ROOT/policy['archive']) as source:
        for name in ('tools/teacher_bot.py','tools/calibrated_beliefs.py',policy['belief_model']):
            assert source.read(name)==(ROOT/name).read_bytes(),name
    model=json.loads((ROOT/policy['belief_model']).read_text())
    assert digest((ROOT/policy['belief_model']).read_bytes())==policy['belief_model_sha256']
    assert model['training_corpus_sha256']==digest((out/'development.jsonl.gz').read_bytes())
    assert set(model['training_games']).isdisjoint(model['calibration_games'])
    assert json.loads((out/'checks/refit.json').read_text())['exact_model_reproduced']
    rebuild=json.loads((out/'checks/clean-rebuild.json').read_text())
    assert rebuild['passed'] and rebuild['all_runtime_hashes_reproduced']
    corpus=list(rows(out/'development.jsonl.gz'))
    partitions={name:{r['pair'] for r in corpus if r['partition']==name} for name in ('train','calibration')}
    assert partitions['train'].isdisjoint(partitions['calibration'])
    strength=json.loads((out/'strength-report.json').read_text())
    decision=json.loads((out/'result.json').read_text())
    assert decision['policy']==plan['candidate']
    assert decision['supported_dos_gain']==strength['supported_dos_gain']
    assert decision['supported_head_gain']==strength['supported_head_gain']
    development=json.loads((out/'development-verification.json').read_text())
    assert development['tournament_sha256']==digest((out/'development.fmtour').read_bytes())
    assert development['verification']['python_replayed']==plan['development']['rounds']*14
    assert development['verification']['native_replayed_all_states']==plan['development']['rounds']*14
    games,states,errors=0,0,0
    signatures={}
    development_pairs=set()
    with Tournament(out/'development.fmtour') as tournament:
        assert tournament.metadata()['seed']==plan['development']['seed']
        for row in tournament.games():
            game=tournament.game(row['id'])
            development_pairs.add((game['family'],game['seed'],game['red_setup'],game['blue_setup']))
    for name, report in strength['matches'].items():
        path=out/'validation'/(name+'.fmtour')
        assert report['tournament_sha256']==digest(path.read_bytes())
        with Tournament(path) as tournament:
            metadata=tournament.metadata()
            assert metadata['status']=='complete' and metadata['rules']=='classic'
            assert metadata['max_plies']==plan['max_plies'] and metadata['families']==plan['families']
            expected=plan['validation']['head_rounds' if name.startswith('head--') else 'dos_rounds']*14
            assert len(tournament.games())==expected
            assert [p['policy'] for p in metadata['participants']]==[frozen[report['match']['policy']],frozen[report['match']['opponent']]]
            assert report['verification']['python_replayed']==expected
            assert report['verification']['native_replayed_all_states']==expected
            signatures[name]=[]
            for row in tournament.games():
                game=tournament.game(row['id'])
                signature=(game['family'],game['seed'],game['red_setup'],game['blue_setup'])
                assert signature not in development_pairs,'development/validation game reused'
                signatures[name].append(signature)
                games+=1;states+=game['plies']+1;errors+=game['result']=='error'
            assert path.with_suffix('.png').is_file()
            assert path.with_suffix('.review.log').is_file()
    assert signatures['dos--'+plan['baseline']]==signatures['dos--'+plan['candidate']]
    assert decision['strength_attempts']==games and decision['unscored_errors']==errors
    validation=json.loads((out/'validation-prediction.json').read_text())
    assert validation['model_sha256']==policy['belief_model_sha256']
    assert validation['partition']=='validation'
    assert validation['corpus_sha256']==digest((out/'validation.jsonl.gz').read_bytes())
    for log in ('calibrated-beliefs.log','truth-boundary.log','tournaments.log','adapter.log'):
        text=(out/'checks'/log).read_text()
        assert '\nOK\n' in text and 'FAILED' not in text,log
    parity=json.loads((out/'checks/native-parent-parity.json').read_text())
    assert parity['passed'] and parity['tested_decisions']>=140
    adapter_parity=json.loads((out/'checks/frozen-adapter-parity.json').read_text())
    assert adapter_parity['passed'] and adapter_parity['tested_decisions']>=140
    for policy_id,spec in frozen.items():
        receipt=json.loads((ROOT/'build/ai-catalog'/policy_id/'build.json').read_text())
        assert receipt['policy']==spec
        for name,sha in receipt['runtime_sha256'].items():
            assert digest((ROOT/'build/ai-catalog'/policy_id/name).read_bytes())==sha
    result=dict(passed=True,previous_policies_unchanged=len(before),new_policy=plan['candidate'],
                model_sha256=policy['belief_model_sha256'],source_sha256=policy['source_sha256'],
                training_games=len(model['training_games']),calibration_games=len(model['calibration_games']),
                no_pair_leakage=True,exact_model_refit=True,fresh_validation=True,
                clean_build_reproduced_all_runtime_hashes=True,
                strength_games=games,replayed_strength_states=states,unscored_strength_errors=errors,
                development_games_verified=development['summary']['games'],
                qt6_captures=len(strength['matches']),native_parent_parity_decisions=parity['tested_decisions'],
                frozen_adapter_parity_decisions=adapter_parity['tested_decisions'],
                supported_dos_gain=strength['supported_dos_gain'],supported_head_gain=strength['supported_head_gain'],
                promote=strength['promote'])
    write(out/'completion-audit.json',result)
    # Save the final analysis/reproduction framework separately from immutable
    # playing sources. Registration-time analysis is retained under checks/.
    with zipfile.ZipFile(out/'framework-source.zip','w',compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in ('belief_experiment.py','audit_belief_experiment.py','calibrated_beliefs.py',
                     'teacher_bot.py','test_calibrated_beliefs.py','ai_registry.py',
                     'information_strategy_cycle.py','analyze_info_activity.py','tournament.py','tournament_store.py'):
            bundle.write(ROOT/'tools'/name,'tools/'+name)
    manifest={str(p.relative_to(out)):digest(p.read_bytes()) for p in sorted(out.rglob('*'))
              if p.is_file() and p.name!='manifest.json'}
    write(out/'manifest.json',dict(sha256=manifest,
                                  external_sha256={policy['archive']:policy['source_sha256'],
                                                   policy['belief_model']:policy['belief_model_sha256']}))
    return result


if __name__=='__main__':print(json.dumps(audit(),indent=2))
