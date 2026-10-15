"""Verify the complete scope of the single linked-scouting experiment."""
import hashlib
import json
import zipfile

from ai_cycle import evidence, matched
from ai_registry import ROOT, build_policy, get_policy
from analyze_linked_scouting import analyze
from evaluate_ai_mission_cases import decide
from linked_scouting_cycle import BASE, plan, sha
from review_linked_scouting import review
from tournament_store import Tournament, verify


def audit_report(stage):
    config=plan();report=json.loads((BASE/(stage+'.json')).read_text())
    candidate,baseline=config['candidate'],config['baseline']
    assert report['plan_sha256']==sha(BASE/'plan.json') and report['policy']==get_policy(candidate)
    head=report['head_to_head']
    assert head==evidence(ROOT/head['path'],candidate)
    candidates={opponent:BASE/f'tournaments/{stage}-league/{candidate}--{opponent}.fmtour' for opponent in config['opponents']}
    controls={opponent:BASE/f'tournaments/{stage}-control/{baseline}--{opponent}.fmtour' for opponent in config['opponents']}
    assert report['league']==matched(candidates,controls,candidate,baseline)
    assert report['proceed_to_validation']==(head['score']>=.52 and report['league']['difference']>=0 and report['tactical_and_fairness_pass'])
    if stage=='validation':
        assert report['strength_gate']==(head['paired_95'][0]>.5 and report['league']['block_95'][0]>0 and report['tactical_and_fairness_pass'])
    expected=[(ROOT/head['path'],candidate,baseline,'head')]
    expected.extend((path,candidate,opponent,'league') for opponent,path in candidates.items())
    expected.extend((path,baseline,opponent,'league') for opponent,path in controls.items())
    schedule=None
    for path,first,second,kind in expected:
        with Tournament(path) as tournament:
            meta=tournament.metadata()
            assert meta['status']=='complete' and meta['rules']=='classic' and meta['backend']=='openmp'
            assert meta['seed']==config['seeds'][stage+'_'+kind]
            assert meta['rounds']==config[stage+'_'+kind+'_rounds']
            assert meta['families']==config['families'] and meta['max_plies']==config['max_plies']
            assert meta['requested_workers']==config['workers']
            assert [p['policy'] for p in meta['participants']]==[get_policy(first),get_policy(second)]
            if kind=='league':
                actual=[]
                for row in tournament.games():
                    game=tournament.game(row['id'])
                    actual.append(tuple(game[key] for key in ('id','pair_id','family','seed','red_setup','blue_setup')))
                if schedule is None:schedule=actual
                assert schedule==actual
    return report


def audit():
    config=plan();candidate=config['candidate']
    policy=get_policy(candidate);assert sha(ROOT/policy['archive'])==policy['source_sha256']
    with zipfile.ZipFile(ROOT/policy['archive']) as bundle:
        for name in ('src/core/ai.c','src/core/ai.h'):
            assert bundle.read(name)==(ROOT/name).read_bytes(),name
    provenance=json.loads((BASE/'checks/frozen-tactics-provenance.json').read_text())
    assert provenance['policy']==policy
    assert provenance['test_source_sha256']==sha(ROOT/'tests/ai_test.c')
    assert all('-D'+define in provenance['command'] for define in policy['defines']+['AI_TEST'])
    with zipfile.ZipFile(BASE/'checks/frozen-tactics.zip') as bundle:
        assert bundle.read('tests/ai_test.c')==(ROOT/'tests/ai_test.c').read_bytes()
        assert hashlib.sha256(bundle.read('test')).hexdigest()==provenance['test_binary_sha256']
        assert bundle.read('log.txt')==(BASE/'checks/frozen-tactics.log').read_bytes()
        assert sha(BASE/'checks/frozen-tactics.log')==provenance['log_sha256']
        assert json.loads(bundle.read('provenance.json'))==provenance
    baseline=get_policy(config['baseline'])
    with zipfile.ZipFile(ROOT/baseline['archive']) as bundle:
        assert bundle.read('src/core/ai_student_model_production.h')==(ROOT/'src/core/ai_student_model_production.h').read_bytes()
    assert json.loads((BASE/'review.json').read_text())==review()
    for image in ('review-decoy.png','review-scout-loss.png','review-opportunity.png',
                  'followup-not-taken-head.png','followup-not-taken-league.png'):
        assert (BASE/image).read_bytes().startswith(b'\x89PNG')
    for name,markers in {'tactics.log':['AI: passed;','15163 hidden-permutation','3836 Silent Defense'],
                         'frozen-tactics.log':['AI: passed;','15163 hidden-permutation','3836 Silent Defense'],
                         'production.log':['AI: passed;','native information: all disclosure/casualty checks passed'],
                         'production-equivalence.log':['3901 decisions: identical moves']}.items():
        log=(BASE/'checks'/name).read_text()
        assert 'FAIL' not in log and all(marker in log for marker in markers)
    diagnostics=json.loads((BASE/'diagnostics/summary.json').read_text())
    cases_path=ROOT/'docs/ai-cycle-2026-10-15/public-cases.jsonl'
    cases=[json.loads(line) for line in cases_path.read_text().splitlines()]
    assert diagnostics['cases_sha256']==sha(cases_path) and len(diagnostics['positions'])==len(cases)==18
    for name,identity in (('candidate',candidate),('baseline','guard-diagnostics-v1-normal')):
        executable,receipt=build_policy(identity)
        copied=BASE/'diagnostics'/name
        assert sha(copied)==receipt['executable_sha256']==diagnostics['engine_sha256'][name]
        for case,row in zip(cases,diagnostics['positions']):
            assert row['id']==case['id'] and decide(case,copied)==row[name]
    development=audit_report('development')
    if development['proceed_to_validation']:
        validation=audit_report('validation')
        assert not validation['strength_gate'],'Complete the real X16 adoption gate before closing a successful runtime candidate.'
        decision='rejected at independent strength gate'
    else:
        assert not (BASE/'validation.json').exists()
        assert not list((BASE/'tournaments').glob('validation*'))
        decision='rejected at development gate; production remains Guarded Student v1'
    assert json.loads((BASE/'activity.json').read_text())==analyze()
    tournaments=[];games=0
    for path in sorted((BASE/'tournaments').rglob('*.fmtour')):
        report=verify(path);assert report['status']=='complete'
        games+=report['games'];tournaments.append(dict(path=str(path.relative_to(BASE)),sha256=sha(path),games=report['games']))
    assert len(tournaments)==(18 if development['proceed_to_validation'] else 9)
    assert games==(5040 if development['proceed_to_validation'] else 1400)
    return dict(schema=1,status='complete',decision=decision,plan_sha256=sha(BASE/'plan.json'),
        policy=policy,reviewed_positions=18,gui_captures=5,diagnostic_positions=18,
        total_games=games,tournaments=tournaments,production_equivalent_decisions=3901,
        root_hidden_permutation_checks=15163,silent_inventory_checks=3836,
        requirement_status=dict(public_match_review='complete',one_named_frozen_candidate='complete',
            production_and_league_development='complete',fresh_validation='not triggered' if not development['proceed_to_validation'] else 'complete',
            public_information_and_cooperation='passed',no_teacher_or_student_fit='complete'),
        evidence_sha256={str(path.relative_to(BASE)):sha(path) for path in sorted(BASE.rglob('*'))
            if path.is_file() and path.name!='audit.json' and path.suffix not in ('.fmtour',)},
        auditor_sha256=sha(__file__))


if __name__=='__main__':
    result=audit()
    (BASE/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('tournaments','evidence_sha256','policy')},indent=2))
