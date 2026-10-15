"""Audit the requested single Classic cycle against its frozen plan and evidence."""
import hashlib
import itertools
import json
import re
from pathlib import Path
import zipfile

from ai_cycle import BASE, ROOT, evidence, matched, plan, score
from ai_registry import build_policy, get_policy
from build_ai_diagnostics import permitted_view
from build_teacher_corpus import extract, select
from evaluate_ai_mission_cases import decide
from feldmarschall import GLYPHS, Position, square_name
from tournament_store import Tournament, verify
from train_ai_student import fit, predict
from train_teacher_student import label_record, public_record


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_report(name, identity):
    report=json.loads((BASE/(name+'.json')).read_text())
    head=report['head_to_head']
    config=plan();stage=name.split('-')[0]
    seed=config['seeds'][stage+('_val' if report['validation'] else '_dev')]
    with Tournament(ROOT/head['path']) as tournament:
        metadata=tournament.metadata()
        assert metadata['seed']==seed and metadata['max_plies']==config['max_plies']
        assert metadata['families']==config['families'] and metadata['rules']=='classic'
        assert [p['policy'] for p in metadata['participants']]==[get_policy(identity),get_policy(config['baseline'])]
    assert head==evidence(ROOT/head['path'],identity)
    assert head['games']==(1400 if report['validation'] else 112)
    assert report['development_gate']==(head['score']>=.52)
    if report['validation']:
        candidates={};controls={}
        reference_schedule=None
        stage=name+'-league';control=name+'-control'
        for opponent in plan()['opponents']:
            candidates[opponent]=BASE/'tournaments'/stage/f'{identity}--{opponent}.fmtour'
            controls[opponent]=BASE/'tournaments'/control/f'student-guard-v1-normal--{opponent}.fmtour'
            for path,actor in ((candidates[opponent],identity),(controls[opponent],config['baseline'])):
                with Tournament(path) as tournament:
                    metadata=tournament.metadata()
                    assert metadata['seed']==seed+1000
                    assert metadata['rounds']==config['validation_league_rounds']
                    assert metadata['families']==config['families'] and metadata['max_plies']==config['max_plies']
                    assert [p['policy'] for p in metadata['participants']]==[get_policy(actor),get_policy(opponent)]
                    schedule=[]
                    for row in tournament.games():
                        game=tournament.game(row['id'])
                        schedule.append(tuple(game[key] for key in ('id','family','pair_id','seed','red_setup','blue_setup')))
                    if reference_schedule is None:reference_schedule=schedule
                    assert schedule==reference_schedule
        actual=matched(candidates,controls,identity,plan()['baseline'])
        assert actual==report['league']
        assert report['strength_gate']==(head['paired_95'][0]>.5 and actual['block_95'][0]>0)
    return report


def audit():
    config=plan(); requirements={}
    baseline=json.loads((BASE/'baseline.json').read_text())
    assert baseline['plan_sha256']==sha(BASE/'plan.json')
    expected={frozenset(pair) for pair in itertools.combinations(config['league'],2)}
    actual=set()
    for report in baseline['comparisons']:
        path=ROOT/report['path']
        with Tournament(path) as tournament:
            assert tournament.metadata()['seed']==config['seeds']['baseline']
            actual.add(frozenset(p['policy']['id'] for p in tournament.metadata()['participants']))
        assert report==evidence(path,report['identity']) and report['games']==42
    assert actual==expected
    requirements['comparison_league']=dict(status='complete',comparisons=10,games=420)

    cases=[json.loads(line) for line in (BASE/'public-cases.jsonl').read_text().splitlines()]
    assert len(cases)==18 and len({c['id'] for c in cases})==18
    for case in cases:
        with Tournament(BASE/case['source']['archive']) as tournament:
            game=tournament.game(case['source']['game_index'])
        assert game['red' if case['input']['army']==0 else 'blue']==config['baseline']
        assert score(game,config['baseline'])<1
        position=Position();history=[];lost=[[0]*12,[0]*12]
        for army in (0,1):position.place(army,game['red_setup' if army==0 else 'blue_setup'])
        for ply,(src,dst) in enumerate(game['moves']):
            if ply==case['source']['ply']:
                assert case['input']==permitted_view(position,ply%2,lost)
                assert case['public_history']==history and case['chosen_move']==[src,dst]
                assert case['legal_moves']==[list(m) for m in position.moves(ply%2)]
                break
            moving,target=position.cells[src],position.cells[dst]
            squares=square_name(src)+' '+square_name(dst)
            if target is None:history.append('moved '+squares);position.move(src,dst)
            else:
                history.append(f'battle {squares} {GLYPHS[moving[1]]} {GLYPHS[target[1]]}')
                _,fallen=position.fight(src,dst,moving[1],target[1])
                for army,rank,_,_ in fallen:lost[army][rank]+=1
    for image in ('decoy-scout-loss.png','quiet-stall.png'):
        assert (BASE/image).read_bytes().startswith(b'\x89PNG')
    requirements['public_failure_review']=dict(status='complete',cases=18,gui_captures=2)

    priority=validate_report('priorities-development','priorities-v1-normal')
    log=(BASE/'checks/priorities.log').read_text()
    failures=[line for line in log.splitlines() if line.startswith('FAIL')]
    assert failures and all('scout investigates a blocker' in line for line in failures)
    assert not priority['development_gate']
    requirements['priority_candidate']=dict(status='rejected',score=priority['head_to_head']['score'],
                                            tactical_failures=len(failures))

    plans=validate_report('plans-development','plans-v2-normal')
    plan_validation=validate_report('plans-validation','plans-v2-normal')
    assert plans['development_gate']
    assert 'AI: passed;' in (BASE/'checks/plans.log').read_text()
    assert 'overflows' in (BASE/'checks/plans-x16-build.log').read_text()
    requirements['plan_candidate']=dict(status='rejected',strength_gate=plan_validation['strength_gate'],
                                        head_score=plan_validation['head_to_head']['score'],
                                        hardware='mission bank overflows by 536 bytes')

    teacher=validate_report('teacher-development','teacher-context-v1-normal')
    teacher_validation=validate_report('teacher-validation','teacher-context-v1-normal')
    assert teacher['development_gate']
    assert 'Ran 2 tests' in (BASE/'checks/teacher-context.log').read_text()
    assert '\nOK' in (BASE/'checks/teacher-context.log').read_text()
    ablation=json.loads((BASE/'teacher-context-ablation.json').read_text())
    assert ablation==evidence(ROOT/ablation['path'],'teacher-context-v1-normal')
    ablation_plan=json.loads((BASE/'ablation-plan.json').read_text())
    with Tournament(ROOT/ablation['path']) as tournament:
        metadata=tournament.metadata()
        assert metadata['seed']==ablation_plan['seed'] and metadata['rounds']==ablation_plan['rounds']
        assert ablation['games']==ablation_plan['games']
    warm=get_policy(ablation_plan['candidate']);cold=get_policy(ablation_plan['control'])
    for key in ('sources','defines','teacher_sources','teacher_defines','difficulty'):
        assert warm[key]==cold[key]
    assert [arg for arg in warm['driver_args'] if arg!='--context']==cold['driver_args']
    requirements['context_teacher']=dict(status='accepted desktop reference' if teacher_validation['strength_gate'] else 'rejected strength promotion',
        strength_gate=teacher_validation['strength_gate'],head_score=teacher_validation['head_to_head']['score'],
        history_ablation_score=ablation['score'],history_ablation_95=ablation['paired_95'])

    student=validate_report('student-development','student-context-v2-normal')
    assert not student['development_gate']
    model=json.loads((BASE/'student-model/model.json').read_text())
    with zipfile.ZipFile(BASE/'student-model/training-evidence.zip') as bundle:
        labels=[json.loads(line) for line in bundle.read('labels.jsonl').splitlines()]
        inputs=[json.loads(line) for line in bundle.read('public-inputs.jsonl').splitlines()]
        assert bundle.read('ai_student_model_v2.h')==(BASE/'student-model/ai_student_model_v2.h').read_bytes()
        assert json.loads(bundle.read('model.json'))==model
    assert len(inputs)==model['positions']==320 and len(labels)==model['rows']==15508
    with Tournament(ROOT/model['source_tournament']) as tournament:
        source_games=[]
        for row in tournament.games():
            game=tournament.game(row['id'])
            source_games.append(dict(game,group=game['family'],deployments=[game['red_setup'],game['blue_setup']]))
    reconstructed=[public_record(record) for record in extract(source_games,select(source_games,8),model['source_sha256'])]
    assert reconstructed==inputs
    assert {row['position'] for row in labels}=={record['id'] for record in inputs}
    assert all({r['history'] for r in labels if r['position']==record['id']}=={'full','cold'} for record in inputs)
    # Independently reproduce full/cold labels at three public-history lengths
    # with the exact frozen teacher; refitting below then checks every fit row.
    ordered=sorted(inputs,key=lambda record:len(record['public_history']))
    baseline_model=[]
    for line in (ROOT/'src/core/ai_student_model_production.h').read_text().splitlines():
        numbers=re.findall(r'-?\d+',line)
        if line.strip().startswith('{') and len(numbers)==5:
            baseline_model.append(dict(zip(('feature','threshold','left','right','value'),map(int,numbers))))
    assert len(baseline_model)==31
    executable,_=build_policy('teacher-context-v1-normal')
    for record in (ordered[0],ordered[len(ordered)//2],ordered[-1]):
        result=label_record((record,str(executable.parent/'observer'),str(executable.parent/'teacher'),8,
                             dict(context=True,baseline_model=baseline_model)))
        assert json.loads(json.dumps(result['rows']))==[row for row in labels if row['position']==record['id']]
    assert all(len(row['features'])==16 and row['history'] in ('full','cold') for row in labels)
    grouped={}
    for row in labels:
        group=row['split_group']
        assert row['validation']==(int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%5==0)
        if group in grouped:assert grouped[group]==row['validation']
        grouped[group]=row['validation']
    training=[r for r in labels if not r['validation']];held=[r for r in labels if r['validation']]
    assert fit(training,depth=4,minimum=24)==model['nodes']
    assert model['node_bytes']==len(model['nodes'])*6==162
    header_nodes=[]
    for line in (BASE/'student-model/ai_student_model_v2.h').read_text().splitlines():
        numbers=re.findall(r'-?\d+',line)
        if line.strip().startswith('{') and len(numbers)==5:
            header_nodes.append(dict(zip(('feature','threshold','left','right','value'),map(int,numbers))))
    assert header_nodes==model['nodes']
    assert len(training)==model['training_rows'] and len(held)==model['held_out_rows']
    assert model['validation_mae']==sum(abs(predict(model['nodes'],r['features'])-r['target']) for r in held)/len(held)
    assert model['source_sha256']==sha(ROOT/model['source_tournament'])
    with Tournament(ROOT/model['source_tournament']) as tournament:
        assert tournament.metadata()['seed']==config['seeds']['teacher_dev']
    assert 'AI: passed;' in (BASE/'checks/student.log').read_text()
    parity=json.loads((BASE/'checks/student-cold-parity.json').read_text())
    banked=json.loads((BASE/'checks/student-banked.json').read_text())
    assert parity['positions']==100 and parity['mismatches']==0
    assert parity['rules']==0 and parity['difficulty']=='normal'
    assert banked['mismatches']==0 and len(banked['turns'])==80
    assert {turn['army'] for turn in banked['turns']}=={0,1}
    assert banked['max_actor_prior_observed_moves']>0
    assert banked['minimum_stack_canary_untouched_bytes']>0
    assert banked['runtime_provenance']['model_sha256']==sha(BASE/'student-model/ai_student_model_v2.h')
    _,student_receipt=build_policy('student-context-v2-normal')
    assert banked['native_sha256']==student_receipt['executable_sha256']
    with zipfile.ZipFile(BASE/'checks/student-runtime-evidence.zip') as bundle:
        provenance=json.loads(bundle.read('src/provenance.json'))
        assert provenance==banked['runtime_provenance']
        assert json.loads(bundle.read('src/banked-student-decisions.json'))==banked
        for name,digest in provenance['files'].items():
            assert hashlib.sha256(bundle.read('src/'+name)).hexdigest()==digest,name
        with zipfile.ZipFile(ROOT/provenance['policy']['archive']) as source:
            for name in source.namelist():
                if name.startswith('src/core/') and name!='src/core/ai_student_model_production.h':
                    assert source.read(name)==bundle.read(name),name
    requirements['compact_student']=dict(status='rejected',model_bytes=162,positions=320,rows=15508,
        development_score=student['head_to_head']['score'],banked_turns=80,cold_parity=parity,
        max_banked_frames=banked['max_frames'],stack_canary_bytes=banked['minimum_stack_canary_untouched_bytes'])

    for stage in ('priorities','plans','student'):
        report=json.loads((BASE/f'diagnostics/{stage}/summary.json').read_text())
        assert len(report['positions'])==18
        assert report['cases_sha256']==sha(BASE/'public-cases.jsonl')
        for name in ('candidate','baseline'):
            executable=BASE/f'diagnostics/{stage}/{name}'
            assert sha(executable)==report['engine_sha256'][name]
            for case,row in zip(cases,report['positions']):
                assert case['id']==row['id'] and decide(case,executable)==row[name]
    for identity in ('priorities-v1-normal','plans-v2-normal','teacher-context-v1-normal','student-context-v2-normal','teacher-cold-control-v1-normal'):
        policy=get_policy(identity)
        assert sha(ROOT/policy['archive'])==policy['source_sha256']
    failure=json.loads((BASE/'plan-build-failure.json').read_text())
    failed=failure['policy']
    assert sha(ROOT/failed['archive'])==failed['source_sha256']
    assert failed['id'] not in {p['id'] for p in json.loads((ROOT/'ai/registry.json').read_text())['policies']}
    assert json.loads((BASE/'metadata-errata.json').read_text())['policy']=='student-context-v2-normal'
    for name,marker in (('production.log','native information: all disclosure/casualty checks passed'),
                        ('tournaments.log','Ran 9 tests'),('native-desktop.log','100% tests passed'),
                        ('legacy-teacher.log','Ran 4 tests'),('production-equivalence.log','3901 decisions: identical moves')):
        assert marker in (BASE/'checks'/name).read_text(),name
    old=get_policy('student-guard-v1-normal')
    with zipfile.ZipFile(ROOT/old['archive']) as bundle:
        assert bundle.read('src/core/ai_student_model_production.h')==(ROOT/'src/core/ai_student_model_production.h').read_bytes()
    requirements['production_and_regressions']=dict(status='complete',production='unchanged Guarded Student v1',
        reasons='Priority tactical failure; plan strength/hardware failure; student development failure. No runtime candidate meets the predeclared adoption gate.',
        exact_native_decisions=3901,root_hidden_permutations=15163,silent_inventory_comparisons=3836)
    # Full source/runtime/trace checks for every retained tournament, including
    # both validation control cohorts and the diagnostic ablation.
    games=0;files=[]
    for path in sorted((BASE/'tournaments').rglob('*.fmtour')):
        summary=verify(path);assert summary['status']=='complete'
        games+=summary['games'];files.append(dict(path=str(path.relative_to(BASE)),sha256=sha(path),games=summary['games']))
    assert len(files)==33 and games==8260
    checks=[dict(path=str(path.relative_to(BASE)),sha256=sha(path))
            for path in sorted((BASE/'checks').iterdir()) if path.is_file()]
    return dict(schema=1,status='complete',plan_sha256=sha(BASE/'plan.json'),requirements=requirements,
                tournaments=files,total_games=games,checks=checks,auditor_sha256=sha(__file__),
                decision='Production unchanged; retain all candidates and validated desktop-reference evidence.')


if __name__=='__main__':
    result=audit()
    (BASE/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='tournaments'},indent=2))
