"""Develop a diverse setup mixture, freeze it, and test its actual selections."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import random

from feldmarschall import ROOT, valid_setup
from optimize_ai_deployments import (FAMILIES, comparisons, delta, evaluate,
                                     freeze, score, sha, trials)


def layouts():
    portfolio = json.loads((ROOT / 'docs/ai-deployments/portfolio.json').read_text())
    result = {'fortress': portfolio['preferred_existing_control']['glyphs']}
    result.update({entry['id']: entry['glyphs'] for entry in portfolio['layouts']})
    assert len(result) == 4 and all(valid_setup(value) for value in result.values())
    return result


def choose_weights(values):
    """Tenths, at least three layouts, no layout above 50%; deterministic ties."""
    candidates = []
    for weights in itertools.product(range(6), repeat=len(values)):
        if sum(weights) == 10 and sum(weight > 0 for weight in weights) >= 3:
            candidates.append((sum(weight * value for weight, value in zip(weights, values)), weights))
    return max(candidates)[1]


def selected_cases(cases, policy, seed):
    # A selection belongs to an opponent-layout block, not to the opponent or side.
    # Thus all five opponents and both sides test the same selected deployment.
    rng = random.Random(seed)
    selected = {}
    names = list(policy['weights'])
    for case in cases:
        block = (case['family'], case['round'])
        if block not in selected:
            selected[block] = rng.choices(names, weights=[policy['weights'][n] for n in names])[0]
    return {index: policy['layouts'][selected[(case['family'], case['round'])]]
            for index, case in enumerate(cases)}, selected


def describe(games):
    result = comparisons(games)
    for name, entry in result.items():
        subset = [game for game in games if game['comparison'] == name]
        entry['capped_games'] = sum(game['reason'] == 'ply limit' for game in subset)
        entry['families'] = {
            family: {'games': len(group), 'score': score(group),
                     'capped_games': sum(game['reason'] == 'ply limit' for game in group)}
            for family in FAMILIES
            if (group := [game for game in subset if game['group'] == family])}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--policy', type=Path, help='frozen development policy; selects validation mode')
    parser.add_argument('--difficulty', choices=('normal', 'hard'), required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--rounds', type=int, default=12)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if min(args.rounds, args.jobs) < 1:
        parser.error('rounds and jobs must be positive')
    phase = 'validation' if args.policy else 'development'
    policy = json.loads(args.policy.read_text()) if args.policy else None
    if policy and (policy['difficulty'] != args.difficulty or policy['development_seed'] == args.seed):
        parser.error('validation requires matching difficulty and a fresh seed')
    if policy:
        weights = policy['weights']
        if (policy['layouts'] != layouts() or set(weights) != set(policy['layouts']) or
                any(type(w) is not int or not 0 <= w <= 5 for w in weights.values()) or
                sum(weights.values()) != 10 or sum(w > 0 for w in weights.values()) < 3):
            parser.error('policy must use the retained layouts and satisfy the frozen diversity constraints')
    provenance = freeze(args.out, args.difficulty, phase, args.seed)
    provenance.update(strategy='deployment-selection', candidate_source=str(Path(__file__).resolve()),
                      source_sha256=sha(__file__), rounds=args.rounds,
                      promotion_gate='mixture minus random block 95% lower bound > 0; at least three layouts; maximum weight 50%')
    if policy:
        provenance['policy_sha256'] = sha(args.policy)
        (args.out / 'frozen-policy.json').write_bytes(args.policy.read_bytes())
    (args.out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    cases = trials(args.seed, args.rounds, [n for n in provenance['run_engine_commands'] if n != 'current'])
    (args.out / 'trials.json').write_text(json.dumps(cases, indent=2) + '\n')
    retained = layouts()
    games = []
    with (args.out / 'games.jsonl').open('w') as output, ProcessPoolExecutor(args.jobs) as pool:
        if policy:
            actual, selections = selected_cases(cases, policy, args.seed + 7919)
            # Case-indexed placements preserve global case IDs and matched sides.
            games = evaluate({'mixture': actual, 'fortress': retained['fortress'],
                              'random-control': None}, cases, provenance, pool, output, 'heldout')
            policy['validation_selection_counts'] = {
                name: sum(value == name for value in selections.values()) for name in policy['weights']}
        else:
            games = evaluate({**retained, 'random-control': None}, cases, provenance, pool, output, 'development')
            names = list(retained)
            values = [score([game for game in games if game['setup_id'] == name]) for name in names]
            weights = choose_weights(values)
            policy = {'schema': 1, 'difficulty': args.difficulty, 'development_seed': args.seed,
                      'layouts': retained, 'weights': dict(zip(names, weights)),
                      'development_scores': dict(zip(names, values)),
                      'selection_rule': 'maximize development mean; integer tenths; >=3 positive weights; each <=50%',
                      'expected_development_score': sum(w * v for w, v in zip(weights, values)) / 10}
        report = {'provenance': provenance, 'comparisons': describe(games), 'policy': policy}
        if args.policy:
            report['setup_deltas'] = {control: delta(games, 'mixture', control)
                                      for control in ('random-control', 'fortress')}
            report['promotion_passed'] = report['setup_deltas']['random-control']['paired_bootstrap_95'][0] > 0
    (args.out / 'policy.json').write_text(json.dumps(policy, indent=2) + '\n')
    (args.out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('setup_deltas', 'promotion_passed') if key in report}, indent=2)
          if args.policy else json.dumps(policy, indent=2))


if __name__ == '__main__':
    main()
