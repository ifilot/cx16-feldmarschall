"""Two-hour follow-up: frozen Classic studies, without modifying prior evidence.

Standard campaign_cycle plan fields apply. Optional dataset={path,split,offset}
uses the frozen setup corpus; plan.families must name its actual six families.
Commands: freeze DIRECTORY; run DIRECTORY; audit DIRECTORY; overview.
"""
import argparse
import contextlib
import json
import time
from pathlib import Path

import campaign_cycle as previous
from ai_registry import ROOT, catalog, get_policy, receives_opponent_setup
from campaign_error_sensitivity import compare as error_compare
from information_strategy_cycle import analyze_match, bootstrap, digest, validate_metadata
from tournament import FAMILIES, run
from tournament_store import Tournament

BASE = ROOT / 'docs/ai-honest-campaign-2026-10-16'
write = previous.write


def overview():
    lines = ['# Two-hour honest Classic AI campaign', '',
             'Each row belongs to its own matched study. Score is wins plus half draws; '
             'errors remain unscored. DOS and honest opponents are separate endpoints. '
             'Screening intervals do not establish promotion or correct for selecting hypotheses.', '',
             '| Cycle | Opponent and setup population | Policy | W / D / L | Score | Errors |',
             '|---|---|---|---:|---:|---:|']
    details = []
    for path in sorted(BASE.glob('cycle-*/plan.json')):
        plan = json.loads(path.read_text())
        directory = path.parent
        details += ['', f"**Cycle {plan['cycle']}:** " + '; '.join(plan['hypotheses']), '']
        result_path = directory/'result.json'
        if not result_path.exists():
            details += ['No completed strength result. [Frozen plan]('+directory.name+'/plan.json).']
            continue
        result = json.loads(result_path.read_text())
        context = (plan['dataset']['split'] + ' corpus' if plan.get('dataset') else
                   ', '.join(plan['families']) + ' / ' + plan.get('setup_mode','referee'))
        for policy, standing in result['standings'].items():
            w,d,l = (standing[k] for k in ('wins','draws','losses'))
            n = w+d+l
            metric = f'{(w+.5*d)/n:.1%}' if n else 'unscored'
            lines.append(f"| {plan['cycle']} | {plan['opponent']}; {context} | {policy} | {w} / {d} / {l} | {metric} | {standing['errors']} |")
        details += ['[Results and family breakdown]('+directory.name+'/result.json).']
        for name, comparison in result['comparisons'].items():
            if comparison is None:
                details.append(f'- {name}: no common complete pairs.')
                continue
            metric = comparison['metrics']['score']; lo,hi = metric['interval_95']
            details.append(f"- {name}: {metric['mean']*100:+.2f} points; 95% paired interval [{lo*100:+.2f}, {hi*100:+.2f}].")
        if (directory/'CONCLUSION.md').exists():
            details += ['[Interpretation]('+directory.name+'/CONCLUSION.md).']
    BASE.mkdir(parents=True,exist_ok=True)
    (BASE/'OVERVIEW.md').write_text('\n'.join(lines+details)+'\n')


def check_plan(directory):
    plan = json.loads((directory/'plan.json').read_text())
    if plan['cycle'] < 101:
        raise ValueError('New campaign cycle numbers start at 101')
    if directory.resolve().parent != BASE.resolve():
        raise ValueError('Cycles must be directly inside the new campaign directory')
    dataset = plan.get('dataset')
    if dataset:
        from setup_dataset import load_dataset, select_records
        bundle = load_dataset(ROOT/dataset['path'])
        split = dataset.get('split','development')
        select_records(bundle,split,plan['rounds'],dataset.get('offset',0))
        if plan['families'] != bundle['manifest']['splits'][split]['families']:
            raise ValueError('Plan families must match the exact frozen dataset partition')
        if plan.get('setup_mode','referee') != 'referee':
            raise ValueError('Dataset studies require referee setups')
    return plan


def freeze(directory):
    plan = check_plan(directory)
    previous.freeze(directory)
    if plan.get('dataset'):
        registration = json.loads((directory/'registration.json').read_text())
        registration['dataset_manifest_sha256'] = digest(ROOT/plan['dataset']['path']/'manifest.json')
        write(directory/'registration.json',registration)
    frozen = json.loads((directory/'frozen-policies.json').read_text())
    for identity in plan['policies']:
        policy = frozen[identity]
        assert not receives_opponent_setup(policy), identity
        assert 'AI_DIAGNOSTIC_TRUTH' not in policy.get('defines',[]), identity
        assert '--diagnostic-truth' not in policy.get('driver_args',[]), identity
    overview()


def dataset_evaluate(directory):
    plan = check_plan(directory)
    frozen = json.loads((directory/'frozen-policies.json').read_text())
    registration = json.loads((directory/'registration.json').read_text())
    assert registration['plan_sha256'] == digest(directory/'plan.json')
    before = json.loads((directory/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)] == before
    assert all(get_policy(p) == spec for p,spec in frozen.items())
    reports,pairs,signature = {},{},None
    dataset = plan['dataset']
    assert registration['dataset_manifest_sha256'] == digest(ROOT/dataset['path']/'manifest.json')
    for identity in plan['policies']:
        path = directory/(identity+'.fmtour')
        match = dict(name=identity,group='honest',policy=identity,opponent=plan['opponent'],
                     seed=plan['seed'],rounds=plan['rounds'])
        if not path.exists():
            print('Running',identity,flush=True)
            with path.with_suffix('.log').open('x') as log, contextlib.redirect_stdout(log):
                result = run(identity,plan['opponent'],path,rounds=plan['rounds'],seed=plan['seed'],
                    jobs=plan['jobs'],families=FAMILIES,max_plies=plan['max_plies'],backend=plan['backend'],
                    setup_dataset=ROOT/dataset['path'],dataset_split=dataset.get('split','development'),
                    dataset_offset=dataset.get('offset',0))
                print(json.dumps(result),flush=True)
        validate_metadata(path,match,plan,frozen)
        assert path.stat().st_mtime >= registration['epoch']
        with Tournament(path) as tournament:
            pin = tournament.metadata()['setup_dataset']
            assert pin['split'] == dataset.get('split','development')
            assert pin['offset'] == dataset.get('offset',0)
            assert pin['manifest_sha256'] == registration['dataset_manifest_sha256']
        report,complete,current = analyze_match(path,match,plan,frozen)
        if signature is None: signature = current
        assert signature == current, 'Unmatched armies or seeds'
        reports[identity],pairs[identity] = report,complete
        write(path.with_suffix('.report.json'),report)
        print('Verified',identity,report['summary']['standings'][identity],flush=True)
    return finish_result(directory,plan,reports,pairs)


def finish_result(directory,plan,reports,pairs):
    comparisons,sensitivity,family_comparisons = {},{},{}
    for a,b in plan['contrasts']:
        common = sorted(pairs[a].keys() & pairs[b].keys())
        blocks = [(pairs[a][key][0],dict(score=pairs[a][key][1]['score']-pairs[b][key][1]['score']))
                  for key in common]
        name = a+' minus '+b
        comparisons[name] = bootstrap(blocks)
        family_comparisons[name] = {f:bootstrap([row for row in blocks if row[0]==f]) for f in plan['families']}
        sensitivity[name] = error_compare(directory/(a+'.fmtour'),a,directory/(b+'.fmtour'),b)
    write(directory/'error-sensitivity.json',sensitivity)
    result = dict(cycle=plan['cycle'],hypotheses=plan['hypotheses'],opponent=plan['opponent'],
        families=plan['families'],setup_mode=plan.get('setup_mode','referee'),dataset=plan.get('dataset'),
        standings={p:dict(r['summary']['standings'][p],errors=r['summary']['errors']) for p,r in reports.items()},
        family_standings={p:r['summary']['families'] for p,r in reports.items()},
        execution_seconds={p:r['execution_seconds'] for p,r in reports.items()},comparisons=comparisons,
        family_comparisons=family_comparisons,error_sensitivity={n:r['summary'] for n,r in sensitivity.items()},
        attempts=sum(r['summary']['games'] for r in reports.values()),
        errors=sum(r['summary']['errors'] for r in reports.values()),
        verified_games=sum(r['verification']['native_replayed_all_states'] for r in reports.values()),
        production='Unchanged. Exploratory screening, not a promotion decision.')
    write(directory/'result.json',result)
    write(directory/'manifest.json',{str(p.relative_to(directory)):digest(p) for p in sorted(directory.rglob('*'))
                                    if p.is_file() and p.name!='manifest.json'})
    overview()
    return result


def family_supplement(directory):
    """Preserve family summaries also for the existing DOS evaluator."""
    result = json.loads((directory/'result.json').read_text())
    plan = json.loads((directory/'plan.json').read_text())
    family_rows = {}
    for identity in plan['policies']:
        report = json.loads((directory/(identity+'.report.json')).read_text())
        family_rows[identity] = report['summary']['families']
    result['family_standings'] = family_rows
    write(directory/'result.json',result)
    write(directory/'manifest.json',{str(p.relative_to(directory)):digest(p) for p in sorted(directory.rglob('*'))
                                    if p.is_file() and p.name!='manifest.json'})
    overview()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('freeze','run','audit','overview'))
    parser.add_argument('directory',type=Path,nargs='?')
    args=parser.parse_args()
    previous.BASE=BASE
    previous.overview=overview
    if args.action=='overview': overview(); return
    if args.directory is None: parser.error('directory is required')
    directory=args.directory.resolve()
    plan=check_plan(directory)
    if args.action=='freeze': freeze(directory)
    elif args.action=='audit': previous.audit(directory)
    elif plan.get('dataset'): print(json.dumps(dataset_evaluate(directory),indent=2))
    else:
        previous.evaluate(directory)
        print(json.dumps(family_supplement(directory),indent=2))


if __name__=='__main__': main()
