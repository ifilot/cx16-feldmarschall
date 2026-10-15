"""Frozen development and gated validation of one linked-scouting candidate."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path

from ai_cycle import evidence, matched
from ai_registry import ROOT, get_policy
from tournament import run
from tournament_store import Tournament

BASE=ROOT/'docs/ai-linked-scouting-2026-10-15'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plan():return json.loads((BASE/'plan.json').read_text())


def play(first,second,stage,seed,rounds):
    config=plan();folder=BASE/'tournaments'/stage;folder.mkdir(parents=True,exist_ok=True)
    path=folder/f'{first}--{second}.fmtour'
    if path.exists():
        with Tournament(path) as tournament:
            meta=tournament.metadata()
            assert meta['status']=='complete',f'Inspect incomplete existing run: {path}'
            assert meta['seed']==seed and meta['rounds']==rounds
            assert meta['families']==config['families'] and meta['max_plies']==config['max_plies']
            assert [p['policy'] for p in meta['participants']]==[get_policy(first),get_policy(second)]
    else:
        print(f'Start {stage}: {first} versus {second} ({rounds*14} games)',flush=True)
        with path.with_suffix('.log').open('x') as log,contextlib.redirect_stdout(log):
            run(first,second,path,rounds=rounds,seed=seed,jobs=config['workers'],families=config['families'],
                max_plies=config['max_plies'],backend='openmp')
    result=evidence(path,first)
    print(f'Finished {first}: {result["score"]:.2%}',flush=True)
    return path,result


def compare(validation=False):
    config=plan();stage='validation' if validation else 'development'
    if validation:
        development=json.loads((BASE/'development.json').read_text())
        assert development['proceed_to_validation'] and development['plan_sha256']==sha(BASE/'plan.json')
        assert development['policy']==get_policy(config['candidate'])
    candidate,baseline=config['candidate'],config['baseline']
    _,head=play(candidate,baseline,stage+'-head',config['seeds'][stage+'_head'],config[stage+'_head_rounds'])
    candidates={};controls={}
    for opponent in config['opponents']:
        candidates[opponent]=play(candidate,opponent,stage+'-league',config['seeds'][stage+'_league'],
                                   config[stage+'_league_rounds'])[0]
        controls[opponent]=play(baseline,opponent,stage+'-control',config['seeds'][stage+'_league'],
                                 config[stage+'_league_rounds'])[0]
    league=matched(candidates,controls,candidate,baseline)
    log=(BASE/'checks/tactics.log').read_text()
    tactics='AI: passed;' in log and 'FAIL' not in log
    assert tactics,'Tactical/fairness checks must finish before decision'
    result=dict(stage=stage,plan_sha256=sha(BASE/'plan.json'),policy=get_policy(candidate),
                head_to_head=head,league=league,tactical_and_fairness_pass=tactics,
                proceed_to_validation=head['score']>=.52 and league['difference']>=0 and tactics)
    if validation:result['strength_gate']=head['paired_95'][0]>.5 and league['block_95'][0]>0 and tactics
    (BASE/(stage+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['development','validation'])
    args=parser.parse_args()
    result=compare(args.stage=='validation')
    print(json.dumps(result,indent=2))
