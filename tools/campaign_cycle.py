"""Frozen honest-AI campaign cycles: matched Classic DOS games and full replay."""
import argparse
import contextlib
import copy
import json
import re
import time
from pathlib import Path

from ai_registry import ROOT, build_policy, catalog, get_policy, register, receives_opponent_setup
from information_strategy_cycle import analyze_match, bootstrap, digest, validate_metadata
from tournament import run

BASE = ROOT / 'docs/ai-honest-campaign-2026-10-15'
FAMILIES = ['fortified', 'uniform', 'unguarded', 'forward', 'decoy', 'presets', 'broad-mixed']


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def freeze(directory):
    plan = json.loads((directory/'plan.json').read_text())
    assert not (directory/'frozen-policies.json').exists()
    write(directory/'registry-before.json', dict(policies=catalog()))
    for spec in plan['new_policies']:
        assert not receives_opponent_setup(spec)
        assert 'AI_DIAGNOSTIC_TRUTH' not in spec['defines']
        assert '--diagnostic-truth' not in spec.get('driver_args', [])
        register(spec)
    identities = list(dict.fromkeys([*plan['policies'], plan['opponent'], plan['baseline']]))
    write(directory/'frozen-policies.json', {p: get_policy(p) for p in identities})
    write(directory/'registration.json', dict(epoch=time.time(), plan_sha256=digest(directory/'plan.json')))


def evaluate(directory):
    plan = json.loads((directory/'plan.json').read_text())
    frozen = json.loads((directory/'frozen-policies.json').read_text())
    registration = json.loads((directory/'registration.json').read_text())
    assert registration['plan_sha256'] == digest(directory/'plan.json')
    before = json.loads((directory/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)] == before
    assert all(get_policy(p) == spec for p, spec in frozen.items())
    reports, pairs, signature = {}, {}, None
    for identity in plan['policies']:
        match = dict(name=identity, group='dos', policy=identity, opponent=plan['opponent'],
                     seed=plan['seed'], rounds=plan['rounds'])
        path = directory/(identity+'.fmtour')
        if not path.exists():
            print('Running', identity, flush=True)
            with path.with_suffix('.log').open('x') as log, contextlib.redirect_stdout(log):
                result = run(identity, plan['opponent'], path, rounds=plan['rounds'], seed=plan['seed'],
                             jobs=plan['jobs'], families=plan['families'], max_plies=plan['max_plies'],
                             backend=plan['backend'])
                print(json.dumps(result), flush=True)
        validate_metadata(path, match, plan, frozen)
        assert path.stat().st_mtime >= registration['epoch']
        report_path = path.with_suffix('.report.json')
        # Reanalyse from artifacts: never silently reuse stale cached statistics.
        report, complete, current = analyze_match(path, match, plan, frozen)
        if signature is None:
            signature = current
        assert current == signature, 'Unmatched armies or seeds'
        reports[identity], pairs[identity] = report, complete
        write(report_path, report)
        print('Verified', identity, report['summary']['standings'][identity], flush=True)
    comparisons = {}
    for first, second in plan['contrasts']:
        common = sorted(pairs[first].keys() & pairs[second].keys())
        comparisons[first+' minus '+second] = bootstrap([
            (pairs[first][key][0], dict(score=pairs[first][key][1]['score']-pairs[second][key][1]['score']))
            for key in common])
    if plan['cycle'] == 1:
        base8, learned8, base32, learned32 = plan['policies']
        common = sorted(set.intersection(*(set(pairs[p]) for p in plan['policies'])))
        comparisons['model by sampling-budget interaction'] = bootstrap([
            (pairs[base8][key][0], dict(score=
             pairs[learned32][key][1]['score'] - pairs[base32][key][1]['score'] -
             pairs[learned8][key][1]['score'] + pairs[base8][key][1]['score'])) for key in common])
    result = dict(cycle=plan['cycle'], hypotheses=plan['hypotheses'],
                  standings={p:dict(r['summary']['standings'][p], errors=r['summary']['errors'])
                             for p,r in reports.items()},
                  execution_seconds={p:r['execution_seconds'] for p,r in reports.items()},
                  comparisons=comparisons, attempts=sum(r['summary']['games'] for r in reports.values()),
                  errors=sum(r['summary']['errors'] for r in reports.values()),
                  production='Unchanged. Campaign screening evidence, not a promotion decision.',
                  verified_games=sum(r['verification']['native_replayed_all_states'] for r in reports.values()))
    write(directory/'result.json', result)
    write(directory/'manifest.json', {str(p.relative_to(directory)):digest(p)
          for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'manifest.json'})
    overview()
    return result


def overview(through_cycle=None):
    lines = ['# Honest AI campaign: cumulative DOS results', '',
             'Scores count wins plus half of draws; original DOS errors are excluded. '
             'Compare policies within their matched cycle. Screening results do not establish promotion.', '',
             '| Cycle / hypothesis | Policy | W / D / L | DOS score | Errors |',
             '|---|---|---:|---:|---:|']
    details = []
    for path in sorted(BASE.glob('cycle-*/result.json')):
        result = json.loads(path.read_text())
        if through_cycle is not None and result['cycle']>through_cycle:
            continue
        for policy, standing in result['standings'].items():
            # Standings preserve the canonical tournament schema.
            wins, draws, losses = (standing[k] for k in ('wins','draws','losses'))
            count = wins+draws+losses
            score = (wins+.5*draws)/count if count else 0
            lines.append(f"| {result['cycle']} | {policy} | {wins} / {draws} / {losses} | {score:.1%} | {standing['errors']} |")
        details += ['', '**Cycle '+str(result['cycle'])+' hypotheses:** '+
                  '; '.join(result['hypotheses']), '',
                  'Evidence: ['+path.parent.name+']('+path.parent.name+'/result.json).', '']
        for name, contrast in result['comparisons'].items():
            metric = contrast['metrics']['score']
            low, high = metric['interval_95']
            details.append(f"- {name}: {100*metric['mean']:+.1f} percentage points; 95% paired interval [{100*low:+.1f}, {100*high:+.1f}].")
        details.append('')
    lines += details
    (BASE/'OVERVIEW.md').write_text('\n'.join(lines)+'\n')


def audit(directory):
    plan = json.loads((directory/'plan.json').read_text())
    frozen = json.loads((directory/'frozen-policies.json').read_text())
    before = json.loads((directory/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)] == before
    assert all(get_policy(p) == spec for p, spec in frozen.items())
    result = json.loads((directory/'result.json').read_text())
    assert result['attempts'] == result['verified_games'] == 14*plan['rounds']*len(plan['policies'])
    reproduced = {}
    for spec in plan['new_policies']:
        policy = frozen[spec['id']]
        assert not receives_opponent_setup(policy)
        assert 'AI_DIAGNOSTIC_TRUTH' not in policy['defines']
        assert '--diagnostic-truth' not in policy['driver_args']
        executable, previous = build_policy(policy['id'])
        (executable.parent/'build.json').unlink()
        _, rebuilt = build_policy(policy['id'])
        assert rebuilt == previous, policy['id']
        reproduced[policy['id']] = rebuilt['runtime_sha256']
    for policy in plan['policies']:
        path = directory/(policy+'.fmtour')
        report = json.loads(path.with_suffix('.report.json').read_text())
        assert report['tournament_sha256'] == digest(path)
        assert report['verification']['python_replayed'] == 14*plan['rounds']
        assert report['verification']['native_replayed_all_states'] == 14*plan['rounds']
        assert path.with_suffix('.png').is_file()
    tests = directory/'checks.log'
    assert tests.is_file()
    test_text = tests.read_text()
    assert re.search(r'^OK(?: \(skipped=\d+\))?$', test_text, re.M) and 'FAILED' not in test_text
    counts = re.findall(r'^Ran (\d+) tests? in ', test_text, re.M)
    assert counts and all(int(count)>0 for count in counts)
    write(directory/'audit.json', dict(passed=True, previous_policies_unchanged=len(before),
          attempts=result['attempts'], errors_preserved_unscored=result['errors'],
          all_games_python_native_replayed=True, qt6_captures=len(plan['policies']),
          exact_rebuild_runtime_sha256=reproduced, production_unchanged=True,
          test_counts=[int(n) for n in counts],
          test_skip_summaries=re.findall(r'^OK \(skipped=\d+\)$',test_text,re.M)))
    write(directory/'manifest.json', {str(p.relative_to(directory)):digest(p)
          for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'manifest.json'})


def init_sampling():
    directory = BASE/'cycle-01-sampling-budget'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline, learned = 'teacher-context-v1-normal', 'teacher-calibrated-beliefs-v1-normal'
    new = []
    for parent, identity in ((baseline, 'teacher-context-worlds32-v1-normal'),
                             (learned, 'teacher-calibrated-worlds32-v1-normal')):
        spec = copy.deepcopy(get_policy(parent))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental',
                    description='Honest 32-world sampling-budget ablation of '+parent,
                    model='Unchanged four-ply guarded Context Teacher; 32 independent public-compatible armies.')
        spec['driver_args'][spec['driver_args'].index('--samples')+1] = '32'
        new.append(spec)
    policies = [baseline, learned, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=1, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2090001, rounds=20, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES,
          hypotheses=['More public-compatible enemy armies reduce decision noise at four times rollout work.',
                      'Calibrated beliefs benefit more from 32 armies than from eight; test the model-by-budget interaction.'],
          contrasts=[[policies[2],baseline],[policies[3],learned],[learned,baseline],[policies[3],policies[2]]],
          analysis='Fixed fresh screening cohort. 20000 family-stratified swapped-pair bootstrap replicates. '
                   'Report every contrast and cost, no production promotion from these exploratory comparisons. '
                   'All public-state traces replayed independently in Python and native worker; Qt6 capture each policy.',
          honesty='No opponent setup, diagnostic observer or referee ranks enter any policy. '
                  'Learned model was frozen before this campaign; no fitting on these seeds.'))
    return directory


def init_mechanisms():
    directory = BASE/'cycle-02-cheap-mechanisms'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline = 'teacher-context-v1-normal'
    new = []
    variants = [
        ('teacher-latin-worlds-v1-normal', ['--world-sampling','latin'],
         'Latin-hypercube random coordinates spread eight count-consistent worlds without additional native searches.'),
        ('teacher-army-activation-v1-normal', ['--campaign-strategy','activation'],
         'Bounded quiet-move potential rewards opening teammates routes to central crossings; enemy ranks unused.'),
        ('teacher-paired-confidence-v1-normal', ['--paired-confidence'],
         'Require paired corrected advantage over native move to exceed one jackknife standard error; no extra rollouts.')]
    for identity, arguments, idea in variants:
        spec = copy.deepcopy(get_policy(baseline))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental', description=idea,
                    model='Unchanged eight-world four-ply Context Teacher plus isolated '+identity,
                    information_model='Own setup and public events only. No opponent setup or diagnostic disclosure.')
        spec['driver_args'] += arguments
        new.append(spec)
    policies = [baseline, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=2, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2100001, rounds=30, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES, hypotheses=[row[2] for row in variants],
          contrasts=[[p, baseline] for p in policies[1:]],
          analysis='Three distinct prespecified exploratory mechanisms, all reported. Matched armies and seeds. '
                   '20000 family-stratified swapped-pair bootstrap replicates; both 95% and 98.333% intervals retained. '
                   'No promotion without fresh independent validation and honest direct opponents.',
          honesty='Native observer has no AI_DIAGNOSTIC_TRUTH. No candidate receives opponent setup. '
                  'Each optional hook isolated; baseline snapshot and all prior IDs immutable.'))
    return directory


def init_horizons():
    directory = BASE/'cycle-03-horizons-and-memory'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline = 'teacher-context-v1-normal'
    variants = [
        ('teacher-capture-quiescence-v1-normal', [], ['AI_ROLLOUT_QUIESCENCE'],
         'Finish policy-selected exchanges beyond four plies, stopping before a quiet move, with at most four extra masked decisions.'),
        ('teacher-sparse-depth-v1-normal', ['--adaptive-depth'], [],
         'Spend eight plies only when public root mobility has at most twelve legal actions, retaining four otherwise.'),
        ('teacher-recurrence-escape-v1-normal', ['--campaign-strategy','recurrence'], [],
         'Remember repeated friendly formations across actors and escape long quiet loops when a similarly valued fresh continuation exists.'),
        ('teacher-uniform-worlds-v1-normal', ['--world-sampling','uniform'], [],
         'Ablate handwritten approach/retreat weights while retaining exactly the same IID count-consistent world proposal; negative-control belief test.')]
    new = []
    for identity, arguments, defines, idea in variants:
        spec = copy.deepcopy(get_policy(baseline))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental', description=idea,
                    model='Isolated honest Context Teacher experiment: '+identity,
                    information_model='Own setup and public events only; sampled worlds never referee ranks.')
        spec['driver_args'] += arguments
        spec['teacher_defines'] += defines
        new.append(spec)
    policies = [baseline, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=3, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2110001, rounds=30, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES, hypotheses=[row[3] for row in variants],
          contrasts=[[p, baseline] for p in policies[1:]],
          analysis='Four prespecified distinct exploratory mechanisms. Fresh seeds, matched armies and side swaps. '
                   '20000 family-stratified paired bootstrap; 95% intervals descriptive across the campaign. '
                   'Uniform weights have adverse offline calibration evidence and are retained as an explicit negative control. '
                   'No tuning or promotion on this cohort.',
          evidence='Historical development mechanisms under research/: quiescence, adaptive-depth, recurrence and weight audit.'))
    return directory


def init_public_defence():
    directory = BASE/'cycle-04-public-flag-defence'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline, native = 'teacher-context-v1-normal', 'student-guard-v1-normal'
    new = []
    for parent, identity in ((native,'student-public-flag-threats-v1-normal'),
                             (baseline,'teacher-public-flag-threats-v1-normal')):
        spec = copy.deepcopy(get_policy(parent))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental',
                    description='Classic public deduction: adjacent concealed enemy that already moved is a confirmed Flag threat.',
                    model='Unchanged '+parent+' except AI_PUBLIC_FLAG_THREATS.',
                    information_model='Own setup and public board/events only; no concealed enemy rank access.')
        spec['defines'].append('AI_PUBLIC_FLAG_THREATS')
        if 'teacher_defines' in spec:
            spec['teacher_defines'].append('AI_PUBLIC_FLAG_THREATS')
        spec.setdefault('asset_files', []).append('tests/ai_public_flag_threats_test.c')
        new.append(spec)
    policies = [native, new[0]['id'], baseline, new[1]['id']]
    write(directory/'plan.json', dict(cycle=4, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2120001, rounds=30, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES,
          hypotheses=['Correct a public logical omission in native Flag defence, without identifying the concealed rank.',
                      'Test the same deduction in the Context Teacher observer and masked continuations.'],
          contrasts=[[policies[1],native],[policies[3],baseline]],
          analysis='Fresh matched side-swapped Classic cohort; report both backends, no tuning or promotion. '
                   'Historical final positions often unsavable; synthetic defence correctness does not imply recovered wins.',
          evidence='research/loss-mechanisms.json and research/public-flag-threat-tests.json.'))
    return directory


def init_joint():
    directory = BASE/'cycle-05-joint-setup-beliefs'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline, independent = 'teacher-context-v1-normal', 'teacher-calibrated-beliefs-v1-normal'
    new = []
    for identity, model, idea in (
        ('teacher-flag-row-control-v1-normal','flag-row-prior-control-v1.json',
         'Control: trained Flag-row prior with exact public rank counts; no Flag/Bomb spatial coupling.'),
        ('teacher-joint-setup-v1-normal','joint-flag-bomb-beliefs-v1.json',
         'Infer protected versus loose Flag/Bomb setup style from public movement and retained Bomb disclosures.')):
        spec = copy.deepcopy(get_policy(baseline))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        path = ROOT/'ai/models'/model
        spec.update(id=identity, name=identity, status='experimental', description=idea,
                    model='Frozen two-style setup prior; exact conditional six-Bomb subset draw, eight worlds/four plies unchanged.',
                    joint_belief_model=str(path.relative_to(ROOT)),joint_belief_model_sha256=digest(path),
                    asset_files=[str(path.relative_to(ROOT))],
                    information_model='Own setup and public events only. Retains public captured Bomb origins. No enemy setup.')
        spec['driver_args'] += ['--joint-belief-model',model]
        new.append(spec)
    policies = [baseline, independent, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=5, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2130001, rounds=40, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES,
          hypotheses=['A cheap learned setup-style mixture can exploit public Flag/Bomb dependencies missed by independent rank tables.',
                      'A control with identical trained Flag-row priors and zero spatial coupling separates positional prior from cross-piece inference.'],
          contrasts=[[policies[3],policies[2]],[policies[3],baseline],[policies[2],baseline],[policies[3],independent]],
          analysis='Fresh matched cohort, all four arms retained. Joint versus identical-prior uncoupled control is primary mechanistic contrast. '
                   'Exploratory strength cohort; fresh final validation and honest opponents required for promotion. '
                   'Fit196historical training armies; calibration84 armies; no campaign seed used to fit or choose parameters.',
          evidence='research/joint-setup-development.json, joint-exact-control-calibration.json and joint-public-prefix-audit.json.'))
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init-sampling','init-mechanisms','init-horizons','init-public-defence','init-joint','freeze','run','overview','audit'])
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--through-cycle', type=int)
    args = parser.parse_args()
    if args.action == 'init-sampling':
        print(init_sampling())
    elif args.action == 'init-mechanisms':
        print(init_mechanisms())
    elif args.action == 'init-horizons':
        print(init_horizons())
    elif args.action == 'init-public-defence':
        print(init_public_defence())
    elif args.action == 'init-joint':
        print(init_joint())
    elif args.action == 'freeze':
        freeze(args.directory)
    elif args.action == 'run':
        evaluate(args.directory)
    elif args.action == 'audit':
        audit(args.directory)
    else:
        overview(args.through_cycle)


if __name__ == '__main__':
    main()
