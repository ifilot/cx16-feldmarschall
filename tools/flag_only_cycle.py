"""Frozen Flag-only information diagnostic against original DOS Stratego."""
import argparse
import contextlib
import copy
import json
from pathlib import Path
import zipfile

from ai_registry import ROOT, catalog, get_policy, register, receives_opponent_setup
from information_strategy_cycle import analyze_match, bootstrap, digest, validate_metadata
from tournament import run
from tournament_store import Tournament

OUT=ROOT/'docs/ai-flag-only-2026-10-15'


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def register_flag(out,plan):
    before=out/'registry-before.json'
    assert not before.exists(),'registration already started'
    write(before,dict(policies=catalog()))
    spec=copy.deepcopy(get_policy(plan['flag_spy']))
    for field in ('archive','source_sha256'):spec.pop(field)
    spec.update(id=plan['candidate'],name='DIAGNOSTIC Flag-only Context Teacher v1 / Normal',
                description='Privileged-information ablation: identify only enemy Flag, leaving Spy and every other concealed rank masked. Original Context Teacher search unchanged.',
                information_model='diagnostic-flag',status='diagnostic',
                model='Unchanged Context Teacher v1 guarded student, eight worlds and four-ply masked continuation; Flag-only disclosure intervention.')
    index=spec['driver_args'].index('--diagnostic-knowledge')+1
    spec['driver_args'][index]='flag'
    write(out/'policy-spec.json',spec)
    register(spec)
    write(out/'frozen-policies.json',{plan[key]:get_policy(plan[key]) for key in ('baseline','candidate','flag_spy','opponent')})


def matches(plan):
    for key in ('baseline','candidate','flag_spy'):
        yield dict(name=plan[key],group='dos',policy=plan[key],opponent=plan['opponent'],
                   seed=plan['seed'],rounds=plan['rounds'])


def evaluate(out,plan,run_games):
    frozen=json.loads((out/'frozen-policies.json').read_text())
    before=json.loads((out/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)]==before
    assert all(get_policy(p)==spec for p,spec in frozen.items())
    reports,pairs,signature={},{},None
    for match in matches(plan):
        path=out/(match['name']+'.fmtour')
        if not path.exists():
            assert run_games,'missing tournament'
            print('Running',match['name'],flush=True)
            with path.with_suffix('.log').open('x') as log,contextlib.redirect_stdout(log):
                result=run(match['policy'],match['opponent'],path,rounds=match['rounds'],seed=match['seed'],
                           jobs=plan['jobs'],families=plan['families'],max_plies=plan['max_plies'],backend=plan['backend'])
                print(json.dumps(result),flush=True)
        validate_metadata(path,match,plan,frozen)
        report,complete,current=analyze_match(path,match,plan,frozen)
        if signature is None:signature=current
        assert signature==current,'armies or seeds differ across information arms'
        reports[match['policy']]=report;pairs[match['policy']]=complete
        write(out/(match['name']+'.report.json'),report)
        print('Verified',match['name'],report['summary']['standings'][match['policy']],flush=True)
    comparisons={}
    for name,first,second in (('flag_minus_honest','candidate','baseline'),
                              ('flag_spy_minus_flag','flag_spy','candidate'),
                              ('flag_spy_minus_honest','flag_spy','baseline')):
        new,old=pairs[plan[first]],pairs[plan[second]]
        common=sorted(new.keys() & old.keys())
        comparisons[name]=bootstrap([(new[key][0],dict(score=new[key][1]['score']-old[key][1]['score'])) for key in common])
    result=dict(question=plan['question'],standings={key:reports[plan[key]]['summary']['standings'][plan[key]]
                                                  for key in ('baseline','candidate','flag_spy')},
                comparisons=comparisons,
                paired_effects_percentage_points={name:dict(mean=100*r['metrics']['score']['mean'],
                                                            interval_95=[100*v for v in r['metrics']['score']['interval_95']],
                                                            complete_pairs=r['complete_pairs']) for name,r in comparisons.items()},
                attempts=sum(r['summary']['games'] for r in reports.values()),
                unscored_errors=sum(r['summary']['errors'] for r in reports.values()),
                primary_flag_gain_supported=comparisons['flag_minus_honest']['metrics']['score']['interval_95'][0]>0,
                incremental_spy_gain_supported=comparisons['flag_spy_minus_flag']['metrics']['score']['interval_95'][0]>0,
                production='Unchanged; Flag-only policy remains explicitly diagnostic.',
                limits=plan['limits'])
    write(out/'strength-report.json',dict(matches=reports,result=result,frozen_policies=frozen))
    write(out/'result.json',result)
    return result


def audit(out,plan):
    frozen=json.loads((out/'frozen-policies.json').read_text())
    before=json.loads((out/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)]==before
    assert all(get_policy(p)==spec for p,spec in frozen.items())
    spec=frozen[plan['candidate']]
    assert receives_opponent_setup(spec) and spec['information_model']=='diagnostic-flag'
    assert 'AI_DIAGNOSTIC_TRUTH' in spec['defines']
    parent=frozen[plan['flag_spy']]
    assert spec['defines']==parent['defines'] and spec['teacher_defines']==parent['teacher_defines']
    assert spec['teacher_sources']==parent['teacher_sources']
    original=parent['driver_args'][:];args=spec['driver_args'][:]
    original[original.index('--diagnostic-knowledge')+1]='flag'
    assert original==args
    assert digest(ROOT/spec['archive'])==spec['source_sha256']
    assert not receives_opponent_setup(frozen[plan['baseline']])
    report=json.loads((out/'strength-report.json').read_text())
    signatures=[];games,states,errors=0,0,0
    for match in matches(plan):
        path=out/(match['name']+'.fmtour')
        validate_metadata(path,match,plan,frozen)
        analysis=report['matches'][match['policy']]
        assert analysis['tournament_sha256']==digest(path)
        assert analysis['verification']['python_replayed']==280
        assert analysis['verification']['native_replayed_all_states']==280
        assert path.with_suffix('.png').is_file()
        with Tournament(path) as tournament:
            signature=[]
            for row in tournament.games():
                game=tournament.game(row['id'])
                signature.append((game['family'],game['seed'],game['red_setup'],game['blue_setup']))
                games+=1;states+=game['plies']+1;errors+=game['result']=='error'
            signatures.append(signature)
    assert signatures[0]==signatures[1]==signatures[2]
    assert games==plan['planned_attempts']==840 and errors==report['result']['unscored_errors']
    for log in ('flag-only.log','teacher-truth.log','parent-parity.log'):
        text=(out/'checks'/log).read_text()
        assert '\nOK\n' in text and 'FAILED' not in text,log
    parity=json.loads((out/'checks/parent-parity.json').read_text())
    assert parity['passed'] and parity['tested_decisions']>=140
    assert parity['actual_extra_defines']==['AI_DIAGNOSTIC_TRUTH']
    assert json.loads((out/'checks/clean-rebuild.json').read_text())['all_runtime_hashes_reproduced']
    with zipfile.ZipFile(ROOT/spec['archive']) as archive:
        for name in ('teacher_bot.py','train_ai_student.py'):
            assert archive.read('tools/'+name)==(ROOT/'build/ai-catalog'/spec['id']/name).read_bytes()
    outcome=dict(passed=True,previous_policies_unchanged=len(before),new_diagnostic=plan['candidate'],
                 flag_only_masking_both_orientations=True,hidden_spy_permutation_invariance=True,
                 public_history_and_reset_checked=True,python_native_reused_process_parity=True,
                 exact_clean_build_runtime_reproduced=True,
                 parent_parity_positions=parity['tested_decisions'],matched_armies_and_seeds=True,
                 validation_attempts=games,replayed_states=states,unscored_dos_errors=errors,qt6_captures=3,
                 primary_flag_gain_supported=report['result']['primary_flag_gain_supported'])
    write(out/'completion-audit.json',outcome)
    with zipfile.ZipFile(out/'framework-source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT/'tools').glob('*.py')):archive.write(path,'tools/'+path.name)
        for name in ('desktop/desk.cpp','desktop/desk.h','desktop/CMakeLists.txt','docs/protocol.md'):
            archive.write(ROOT/name,name)
    manifest={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    write(out/'manifest.json',dict(sha256=manifest,external_sha256={spec['archive']:spec['source_sha256']}))
    return outcome


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('register','run','analyze','audit'))
    args=parser.parse_args();out=OUT
    plan=json.loads((out/'plan.json').read_text())
    if args.action=='register':register_flag(out,plan)
    elif args.action=='audit':print(json.dumps(audit(out,plan),indent=2))
    else:evaluate(out,plan,args.action=='run')


if __name__=='__main__':main()
