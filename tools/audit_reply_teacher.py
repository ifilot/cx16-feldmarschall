"""Requirement audit for the single desktop reply-branch experiment."""
import hashlib
import json
import zipfile

from ai_registry import ROOT,build_policy,get_policy
from ai_cycle import evidence,matched
from diagnose_reply_teacher import decide
from profile_teacher_replies import profile
from reply_teacher_cycle import BASE,plan,sha
from review_reply_teacher import review
from tournament_store import Tournament,verify


def check_stage(stage):
    config=plan();candidate,control=config['candidate'],config['control']
    report=json.loads((BASE/(stage+'.json')).read_text())
    assert report['plan_sha256']==sha(BASE/'plan.json') and report['policy']==get_policy(candidate)
    head=report['head_to_head'];assert head==evidence(ROOT/head['path'],candidate)
    candidates={opponent:BASE/f'tournaments/{stage}-league/{candidate}--{opponent}.fmtour' for opponent in config['opponents']}
    controls={opponent:BASE/f'tournaments/{stage}-control/{control}--{opponent}.fmtour' for opponent in config['opponents']}
    assert report['league']==matched(candidates,controls,candidate,control)
    assert report['production']==evidence(candidates[config['production']],candidate)
    assert report['proceed_to_validation']==(head['score']>=.52 and report['league']['difference']>=0 and report['production']['score']>.5)
    assert report['privacy_and_state_tests_pass']
    if stage=='validation':
        assert report['strength_gate']==(head['paired_95'][0]>.5 and report['league']['block_95'][0]>0 and report['production']['paired_95'][0]>.5)
    paths=[(ROOT/head['path'],candidate,control,'head')]
    paths.extend((path,candidate,opponent,'league') for opponent,path in candidates.items())
    paths.extend((path,control,opponent,'league') for opponent,path in controls.items())
    common=None
    for path,first,second,kind in paths:
        with Tournament(path) as tournament:
            metadata=tournament.metadata()
            assert metadata['rules']=='classic' and metadata['status']=='complete' and metadata['backend']=='openmp'
            assert metadata['seed']==config['seeds'][stage+'_'+kind]
            assert metadata['rounds']==config[stage+'_'+kind+'_rounds']
            assert metadata['families']==config['families'] and metadata['max_plies']==config['max_plies']
            assert metadata['requested_workers']==config['workers']
            assert [p['policy'] for p in metadata['participants']]==[get_policy(first),get_policy(second)]
            if kind=='league':
                schedule=[]
                for row in tournament.games():
                    game=tournament.game(row['id'])
                    schedule.append(tuple(game[key] for key in ('id','pair_id','family','seed','red_setup','blue_setup')))
                if common is None:common=schedule
                assert schedule==common
    return report


def without_timing(value):
    return {key:item for key,item in value.items() if key!='elapsed_seconds'}


def audit():
    config=plan();requirements={}
    candidate=get_policy(config['candidate']);control=get_policy(config['control'])
    assert sha(ROOT/candidate['archive'])==candidate['source_sha256']
    assert sha(ROOT/control['archive'])==control['source_sha256']
    assert candidate['defines']==control['defines'] and candidate['sources']==control['sources']
    assert candidate['teacher_sources']==control['teacher_sources']
    assert candidate['teacher_defines']==control['teacher_defines']+['AI_REPLY_BRANCHES','AI_TRACE']
    assert candidate['driver_args']==control['driver_args']+['--replies','3']
    for option,key in (('--samples','samples'),('--depth','depth'),('--replies','reply_limit')):
        assert int(candidate['driver_args'][candidate['driver_args'].index(option)+1])==config[key]
    with zipfile.ZipFile(ROOT/candidate['archive']) as bundle:
        for name in ('src/native/teacher_rollout.c','tools/teacher_bot.py','tools/test_teacher_replies.py'):
            assert bundle.read(name)==(ROOT/name).read_bytes(),name
        native=bundle.read('src/native/teacher_rollout.c').decode()
        assert f'#define MAX_REPLIES {config["reply_limit"]}' in native
        assert f'#define REPLY_GAP {config["reply_score_gap"]}' in native
        with zipfile.ZipFile(ROOT/control['archive']) as previous:
            for name in candidate['sources']:
                if name!='src/core/ai.c':
                    # ai.h gained only the opt-in linked-scouting test getter;
                    # source lists contain C files, and all other C is identical.
                    assert bundle.read(name)==previous.read(name),name
    requirements['one_frozen_desktop_candidate']='complete'
    for name,markers in {'teacher-tests.log':['Ran 6 tests','\nOK'],
                         'legacy-teacher.log':['Ran 4 tests','\nOK'],
                         'production.log':['AI: passed;','native information: all disclosure/casualty checks passed']}.items():
        log=(BASE/'checks'/name).read_text();assert all(marker in log for marker in markers) and 'FAIL' not in log
    requirements['privacy_branch_restoration_legacy_compatibility']='passed'
    cases=[json.loads(line) for line in (BASE/'public-cases.jsonl').read_text().splitlines()]
    assert cases==review() and len(cases)==18
    review_report=json.loads((BASE/'review.json').read_text())
    assert review_report['cases']==18 and review_report['cases_sha256']==sha(BASE/'public-cases.jsonl')
    for name in ('review-attacker-removed.png','review-target-retreat.png','review-flag-loss.png'):
        assert (BASE/name).read_bytes().startswith(b'\x89PNG')
    requirements['all_eighteen_public_losses_and_gui_review']='complete'
    diagnostics=json.loads((BASE/'diagnostics.json').read_text())
    assert diagnostics['cases_sha256']==sha(BASE/'public-cases.jsonl')
    assert len(diagnostics['positions'])==18
    for case,row in zip(cases,diagnostics['positions']):
        assert row['id']==case['id']
        public={key:case[key] for key in ('id','input','source','public_history','own_initial_setup','legal_moves','recorded_probe')}
        for role,identity,replies in (('candidate',config['candidate'],3),('control',config['control'],None)):
            actual=json.loads(json.dumps(decide(public,identity,replies)))
            assert without_timing(actual)==without_timing(row[role])
        assert row['candidate']['root_context_sha256']==row['control']['root_context_sha256']
    assert diagnostics['changed_decisions']==sum(r['candidate']['selected']!=r['control']['selected'] for r in diagnostics['positions'])
    for role in ('candidate','control'):
        assert diagnostics[role+'_recorded_probes']==sum(row[role]['recorded_probe_selected'] for row in diagnostics['positions'])
        assert diagnostics[role+'_nodes']==sum(row[role]['nodes'] for row in diagnostics['positions'])
    coverage=json.loads((BASE/'reply-coverage.json').read_text())
    for case,row in zip(cases,coverage['positions']):assert profile(case)==row
    assert len(coverage['positions'])==18 and coverage['total_reply_sets']==144
    assert coverage['single_policy_cases_covered']==sum(r['single_policy_coverage']>0 for r in coverage['positions'])
    assert coverage['reply_set_cases_covered']==sum(r['reply_set_coverage']>0 for r in coverage['positions'])
    requirements['masked_root_diagnostics_and_post_probe_coverage']='reproduced'
    development=check_stage('development')
    if development['proceed_to_validation']:
        validation=check_stage('validation')
        decision='accepted desktop reference' if validation['strength_gate'] else 'rejected at independent validation'
    else:
        assert not (BASE/'validation.json').exists() and not list((BASE/'tournaments').glob('validation*'))
        decision='rejected at development gate'
    requirements['production_and_preserved_league']='complete'
    requirements['fresh_validation']='complete' if development['proceed_to_validation'] else 'not triggered by development gate'
    with zipfile.ZipFile(ROOT/get_policy(config['production'])['archive']) as old:
        assert old.read('src/core/ai_student_model_production.h')==(ROOT/'src/core/ai_student_model_production.h').read_bytes()
    with zipfile.ZipFile(ROOT/get_policy('linked-scouting-v1-normal')['archive']) as preceding:
        for name in preceding.namelist():
            if name.startswith('src/core/') or name=='src/native/engine.c':
                assert preceding.read(name)==(ROOT/name).read_bytes(),name
    assert not list(BASE.glob('*model*'))
    requirements['no_student_fit_or_x16_policy_change']='complete'
    files=[];games=0
    for path in sorted((BASE/'tournaments').rglob('*.fmtour')):
        summary=verify(path);assert summary['status']=='complete'
        games+=summary['games'];files.append(dict(path=str(path.relative_to(BASE)),sha256=sha(path),games=summary['games']))
    assert games==(5180 if development['proceed_to_validation'] else 980)
    assert len(files)==(22 if development['proceed_to_validation'] else 11)
    return dict(schema=1,status='complete',decision=decision,requirements=requirements,plan_sha256=sha(BASE/'plan.json'),
        policy=candidate,total_games=games,tournaments=files,auditor_sha256=sha(__file__),
        evidence_sha256={str(path.relative_to(BASE)):sha(path) for path in sorted(BASE.rglob('*')) if path.is_file() and path.name!='audit.json' and path.suffix!='.fmtour'})


if __name__=='__main__':
    result=audit();(BASE/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('tournaments','evidence_sha256','policy')},indent=2))
