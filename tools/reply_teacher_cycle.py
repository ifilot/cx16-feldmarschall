"""One frozen desktop reply-branch trial and its gated independent validation."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path

from ai_cycle import evidence, matched
from ai_registry import ROOT, get_policy
from tournament import run
from tournament_store import Tournament

BASE=ROOT/'docs/ai-reply-teacher-2026-10-15'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plan():return json.loads((BASE/'plan.json').read_text())


def play(first,second,stage,seed,rounds):
    config=plan();folder=BASE/'tournaments'/stage;folder.mkdir(parents=True,exist_ok=True)
    path=folder/f'{first}--{second}.fmtour'
    if path.exists():
        with Tournament(path) as tournament:
            meta=tournament.metadata()
            assert meta['status']=='complete',f'Inspect existing incomplete file: {path}'
            assert meta['seed']==seed and meta['rounds']==rounds
            assert meta['families']==config['families'] and meta['max_plies']==config['max_plies']
            assert [p['policy'] for p in meta['participants']]==[get_policy(first),get_policy(second)]
    else:
        print(f'Start {stage}: {first} versus {second} ({rounds*14} games)',flush=True)
        with path.with_suffix('.log').open('x') as log,contextlib.redirect_stdout(log):
            run(first,second,path,rounds=rounds,seed=seed,jobs=config['workers'],families=config['families'],
                max_plies=config['max_plies'],backend='openmp')
    report=evidence(path,first)
    print(f'Finished {first}: {report["score"]:.2%}',flush=True)
    return path,report


def compare(validation=False):
    config=plan();stage='validation' if validation else 'development'
    candidate,control=config['candidate'],config['control']
    if validation:
        previous=json.loads((BASE/'development.json').read_text())
        assert previous['proceed_to_validation'] and previous['policy']==get_policy(candidate)
        assert previous['plan_sha256']==sha(BASE/'plan.json')
    log=(BASE/'checks/teacher-tests.log').read_text()
    assert 'Ran 6 tests' in log and '\nOK' in log and 'FAIL' not in log
    _,head=play(candidate,control,stage+'-head',config['seeds'][stage+'_head'],config[stage+'_head_rounds'])
    candidates={};controls={}
    for opponent in config['opponents']:
        candidates[opponent]=play(candidate,opponent,stage+'-league',config['seeds'][stage+'_league'],config[stage+'_league_rounds'])[0]
        controls[opponent]=play(control,opponent,stage+'-control',config['seeds'][stage+'_league'],config[stage+'_league_rounds'])[0]
    league=matched(candidates,controls,candidate,control)
    production=evidence(candidates[config['production']],candidate)
    report=dict(stage=stage,policy=get_policy(candidate),plan_sha256=sha(BASE/'plan.json'),
                head_to_head=head,league=league,production=production,privacy_and_state_tests_pass=True,
                proceed_to_validation=head['score']>=.52 and league['difference']>=0 and production['score']>.5)
    if validation:report['strength_gate']=head['paired_95'][0]>.5 and league['block_95'][0]>0 and production['paired_95'][0]>.5
    (BASE/(stage+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('development','validation'))
    compare(parser.parse_args().stage=='validation')
