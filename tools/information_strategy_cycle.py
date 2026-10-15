"""Frozen fair information-strategy tournaments, replay audit and statistics.

Run: python3 tools/information_strategy_cycle.py run --out docs/ai-fair-information-2026-10-15
Recompute: python3 tools/information_strategy_cycle.py analyze --out <same directory>
"""
import argparse
from collections import defaultdict
import contextlib
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import time
import traceback
import zipfile

from ai_registry import ROOT, catalog, get_policy, receives_opponent_setup
from analyze_info_activity import activity
from tournament import run
from tournament_store import Tournament, replay, verify

BEHAVIOR = ('new_enemy_disclosures', 'zero_disclosure_casualties',
            'known_losing_attack_deaths', 'casualties')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def matches(plan, phase):
    config = plan['cohorts'][phase]
    for policy in (plan['baseline'], *plan['candidates'].values()):
        yield dict(name='dos--'+policy, group='dos', policy=policy, opponent=plan['opponent'],
                   seed=config['dos_seed'], rounds=config['dos_rounds'])
    for policy in plan['candidates'].values():
        yield dict(name='head--'+policy, group='head', policy=policy, opponent=plan['baseline'],
                   seed=config['head_seed'], rounds=config['head_rounds'])


def validate_metadata(path, match, plan, frozen):
    with Tournament(path) as tournament:
        metadata = tournament.metadata()
        assert metadata['status'] == 'complete', f'Incomplete evidence is preserved: {path}'
        assert metadata['seed'] == match['seed'] and metadata['rounds'] == match['rounds']
        assert metadata['max_plies'] == plan['max_plies']
        assert metadata['families'] == plan['families']
        assert metadata.get('setup_mode','referee') == plan.get('setup_mode','referee')
        assert metadata['rules'] == 'classic' and metadata['backend'] == plan['backend']
        policies = [participant['policy'] for participant in metadata['participants']]
        assert policies == [frozen[match['policy']], frozen[match['opponent']]]
        assert len(tournament.games()) == 2*len(plan['families'])*match['rounds']


def score(game, policy):
    if game['result'] == 'error': return None
    if game['result'] == 'draw': return .5
    return float(game['result'] == ('red' if game['red'] == policy else 'blue'))


def bootstrap(blocks):
    """Joint percentile intervals; paired assignments remain indivisible."""
    if not blocks: return None
    fields = list(blocks[0][1])
    groups = defaultdict(list)
    for family, row in blocks: groups[family].append([row[key] for key in fields])
    values = [[] for _ in fields]
    rng = random.Random(1970001)
    for _ in range(20000):
        totals = [0.0]*len(fields)
        for rows in groups.values():
            for _ in rows:
                selected = rng.choice(rows)
                for index, value in enumerate(selected): totals[index] += value
        for index, total in enumerate(totals): values[index].append(total/len(blocks))
    result = {}
    for index, key in enumerate(fields):
        ordered = sorted(values[index])
        result[key] = dict(mean=sum(row[key] for _,row in blocks)/len(blocks),
                           interval_95=[ordered[499],ordered[19499]],
                           interval_98_3333=[ordered[166],ordered[19833]])
    return dict(complete_pairs=len(blocks), pairs_by_family={key:len(rows) for key,rows in groups.items()},
                metrics=result)


def aggregate(activities):
    result = dict(games=len(activities), by_rank={}, weak={}, miners_lost=0,
                  own_weak_moves=0, own_moves=0, plies=0)
    for row in activities:
        for key in ('miners_lost','own_weak_moves','own_moves','plies'): result[key] += row[key]
        for key,value in row['weak'].items(): result['weak'][key] = result['weak'].get(key,0)+value
        for rank,counts in row['by_rank'].items():
            target=result['by_rank'].setdefault(rank,{})
            for key,value in counts.items(): target[key]=target.get(key,0)+value
    n=len(activities)
    result['per_game']={key:result['weak'].get(key,0)/n if n else None for key in BEHAVIOR}
    result['disclosures_per_100_weak_moves']=(100*result['weak'].get('new_enemy_disclosures',0)/result['own_weak_moves']
                                               if result['own_weak_moves'] else None)
    casualties=result['weak'].get('casualties',0)
    result['fraction_casualties_without_personal_disclosure']=(result['weak'].get('zero_disclosure_casualties',0)/casualties
                                                               if casualties else None)
    return result


def analyze_match(path, match, plan, frozen):
    validate_metadata(path,match,plan,frozen)
    summary=verify(path)
    activities={};pairs=defaultdict(list)
    with Tournament(path) as tournament, tempfile.TemporaryDirectory(prefix='fair-info-replay-') as temp:
        metadata=tournament.metadata()
        games=[tournament.game(row['id']) for row in tournament.games()]
        request=Path(temp)/'game.json'
        for game in games:
            request.write_text(json.dumps(game))
            result=subprocess.run([str(ROOT/'build/desktop/feldmarschall-tournament-worker'),'--replay',str(request)],
                                  capture_output=True,text=True,check=True,timeout=30)
            assert json.loads(result.stdout)['states']==replay(game)[0]
            activities[game['id']]=activity(game,match['policy'])
            pairs[game['pair_id']].append(game)
        chosen=next((game for game in games if score(game,match['policy'])==1),games[0])
        result=subprocess.run([str(ROOT/'build/desktop/feldmarschall-desk'),'--capture-review',str(path),
                               '--match',str(chosen['id']),'--ply',str(chosen['plies']),
                               '--screenshot',str(path.with_suffix('.png'))],env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),
                              capture_output=True,text=True,timeout=30)
        path.with_suffix('.review.log').write_text(result.stdout+result.stderr)
        result.check_returncode()
    complete={}
    for key,rows in pairs.items():
        if len(rows)!=2 or any(row['result']=='error' for row in rows):continue
        metrics=dict(score=sum(score(row,match['policy']) for row in rows)/2)
        metrics.update({field:sum(activities[row['id']]['weak'][field] for row in rows)/2 for field in BEHAVIOR})
        complete[key]=(rows[0]['family'],metrics)
    result=dict(match=match,summary=summary,complete_pair_statistics=bootstrap(list(complete.values())),
                activity_scored=aggregate([activities[g['id']] for g in games if g['result']!='error']),
                activity_error_prefixes=aggregate([activities[g['id']] for g in games if g['result']=='error']),
                activities=list(activities.values()),participants=metadata['participants'],
                tournament_sha256=digest(path),execution_seconds=metadata['execution_seconds'],
                verification=dict(python_replayed=len(games),native_replayed_all_states=len(games),
                                  artifacts_verified=True,qt6_review_match=chosen['id']))
    signature=[(g['id'],g['pair_id'],g['family'],g['seed'],g['red_setup'],g['blue_setup']) for g in games]
    return result,complete,signature


def analyze_phase(out,phase,plan,frozen):
    report_path=out/phase/'report.json'
    if report_path.exists():
        previous=json.loads(report_path.read_text())
        assert previous['analysis_source_sha256']==digest(Path(__file__))
        assert previous['activity_source_sha256']==digest(ROOT/'tools/analyze_info_activity.py')
        assert previous['plan_sha256']==document_digest(plan),'Cached plan differs'
        assert previous['frozen_policies_sha256']==document_digest(frozen),'Cached policies differ'
        for match in matches(plan,phase):
            validate_metadata(out/phase/(match['name']+'.fmtour'),match,plan,frozen)
            assert previous['matches'][match['name']]['tournament_sha256']==digest(out/phase/(match['name']+'.fmtour'))
        return previous
    report=dict(matches={},comparisons={},analysis_source_sha256=digest(Path(__file__)),
                activity_source_sha256=digest(ROOT/'tools/analyze_info_activity.py'),
                plan_sha256=document_digest(plan),frozen_policies_sha256=document_digest(frozen))
    pairs={};signature=None
    for match in matches(plan,phase):
        path=out/phase/(match['name']+'.fmtour')
        result,blocks,current=analyze_match(path,match,plan,frozen)
        report['matches'][match['name']]=result
        if match['group']=='dos':
            if signature is None:signature=current
            assert signature==current,'DOS armies/seeds differ across policies'
            pairs[match['policy']]=blocks
        print('Verified',phase,match['name'],result['summary']['standings'][match['policy']],flush=True)
    baseline=pairs[plan['baseline']]
    for policy in plan['candidates'].values():
        common=sorted(baseline.keys() & pairs[policy].keys())
        differences=[(baseline[key][0],{field:pairs[policy][key][1][field]-baseline[key][1][field]
                                      for field in baseline[key][1]}) for key in common]
        comparison=bootstrap(differences)
        dos_interval=comparison['metrics']['score']['interval_98_3333']
        head=report['matches']['head--'+policy]['complete_pair_statistics']['metrics']['score']['interval_98_3333']
        comparison['dos_gain_supported']=dos_interval[0]>0
        comparison['direct_predecessor_gain_supported']=head[0]>.5
        comparison['both_strength_endpoints_supported']=dos_interval[0]>0 and head[0]>.5
        report['comparisons'][policy]=comparison
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    return report


def audit_invariants(out,plan,frozen):
    before=json.loads((out/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)]==before,'An existing policy changed'
    for policy in plan['candidates'].values():
        spec=frozen[policy]
        assert not receives_opponent_setup(spec)
        assert 'AI_DIAGNOSTIC_TRUTH' not in spec['defines']
        assert '--diagnostic-truth' not in spec['driver_args']
        assert spec['difficulty']=='normal'
    return dict(previous_policies_unchanged=len(before),fair_candidates=len(plan['candidates']),
                no_private_setups=True,registered_before_games=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('run','analyze'))
    parser.add_argument('--out',type=Path,default=ROOT/'docs/ai-fair-information-2026-10-15')
    parser.add_argument('--phase',choices=('pilot','validation'))
    args=parser.parse_args();out=args.out.resolve()
    plan=json.loads((out/'plan.json').read_text())
    freeze=out/'frozen-policies.json'
    if not freeze.exists():
        assert args.action=='run'
        identities=[plan['baseline'],plan['opponent'],*plan['candidates'].values()]
        freeze.write_text(json.dumps({identity:get_policy(identity) for identity in identities},indent=2)+'\n')
    frozen=json.loads(freeze.read_text())
    assert all(get_policy(identity)==policy for identity,policy in frozen.items())
    invariants=audit_invariants(out,plan,frozen)
    phases=[args.phase] if args.phase else list(plan['cohorts'])
    reports={}
    for phase in phases:
        (out/phase).mkdir(exist_ok=True)
        if args.action=='run':
            for match in matches(plan,phase):
                path=out/phase/(match['name']+'.fmtour')
                if path.exists():validate_metadata(path,match,plan,frozen);continue
                print('Running',phase,match['name'],flush=True)
                started=time.monotonic()
                with path.with_suffix('.log').open('x') as log,contextlib.redirect_stdout(log):
                    try:
                        summary=run(match['policy'],match['opponent'],path,rounds=match['rounds'],seed=match['seed'],
                                    jobs=plan['jobs'],families=plan['families'],max_plies=plan['max_plies'],backend=plan['backend'])
                        print(json.dumps(summary,indent=2),flush=True)
                    except BaseException:traceback.print_exc(file=log);raise
                print('Finished',phase,match['name'],round(time.monotonic()-started,2),'seconds',flush=True)
        reports[phase]=analyze_phase(out,phase,plan,frozen)
    report=dict(plan=plan,cohorts=reports,invariants=invariants,
                statistics='20000 stratified paired bootstrap replicates. Matched comparisons omit a complete pair if either policy has an error. 95% intervals are descriptive; 98.3333% intervals adjust three strategy comparisons per endpoint. Behavior intervals are descriptive; information counts alone do not establish useful play.',
                tests={p.name:dict(sha256=digest(p),output=p.read_text()) for p in (out/'checks').glob('*.log')})
    (out/('report.json' if not args.phase else args.phase+'-report.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('Report saved',out,flush=True)


if __name__=='__main__':main()
