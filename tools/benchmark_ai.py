"""Reproducible comparisons with the frozen v0.2.0 AI; run make benchmark-ai.

Development uses different seeds. Each validation round consists of two games
with identical deployments and engine sides swapped. Confidence intervals
resample complete pairs, so the two games are not treated as independent.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import sys

from arena import deployments, play
from feldmarschall import ROOT, new_rng


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def statistics(games, engine="current"):
    points = [1.0 if g['winner'] == engine else 0.5 if g['winner'] is None else 0.0 for g in games]
    pairs = [(points[i] + points[i + 1]) / 2 for i in range(0, len(points), 2)]
    rng = random.Random(8675309)
    samples = sorted(sum(rng.choices(pairs, k=len(pairs))) / len(pairs) for _ in range(10000))
    return {
        'games': len(games), 'wins': points.count(1.0), 'draws': points.count(0.5), 'losses': points.count(0.0),
        'score': sum(points) / len(points), 'paired_bootstrap_95': [samples[249], samples[9749]],
        'reasons': dict(Counter(g['reason'] for g in games)),
        'average_plies': sum(g['plies'] for g in games) / len(games),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=300, help='paired rounds for each deployment group')
    parser.add_argument('--levels', action='store_true', help='compare Easy, Normal and Hard with independent seeds')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/ai-benchmark')
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('--rounds must be positive')
    engines = {'current': str(ROOT / 'build/feldmarschall-engine'),
               'v020': str(ROOT / 'build/feldmarschall-ai-v020')}
    if args.levels:
        engines = {level: str(ROOT / 'build/feldmarschall-engine') + ' --difficulty ' + level
                   for level in ('easy', 'normal', 'hard')}
    pairs = [('normal', 'easy'), ('hard', 'normal'), ('hard', 'easy')] if args.levels else [('current', 'v020')]
    groups = [('mixed', 20261021), ('random', 20261022), ('presets', 20261023)] if args.levels else [('mixed', 271828), ('random', 314159), ('presets', 161803)]
    jobs, metadata = [], []
    for kind, seed in groups:
        rng = new_rng(seed)
        for round_index in range(args.rounds):
            setups = (deployments(kind, rng), deployments(kind, rng))
            move_seed = rng.randrange(1, 60000)
            for a, b in pairs:
                for names in [(a, b), (b, a)]:
                    jobs.append((names, tuple(engines[n] for n in names), setups, move_seed, 1000))
                    metadata.append({'group': kind, 'round': round_index, 'deployments': list(setups), 'comparison': a + '-vs-' + b})
    args.out.mkdir(parents=True, exist_ok=True)
    provenance = {
        'rounds_per_group': args.rounds, 'groups': dict(groups), 'max_plies': 1000,
        'source_sha256': sha(ROOT / 'src/core/ai.c'),
        'baseline_sha256': sha(ROOT / 'tests/baselines/ai_v020.c'),
        'rules_sha256': sha(ROOT / 'src/core/rules.c'),
        'engine_sha256': {name: sha(path.split(' --difficulty ')[0]) for name, path in engines.items()},
        'level_configuration_sha256': sha(ROOT / 'src/core/ai_level.c'),
        'confidence_method': '10000 bootstrap resamples of complete side-swapped pairs; seed 8675309',
    }
    games = []
    with (args.out / 'games.jsonl').open('w') as out, ProcessPoolExecutor(args.jobs) as pool:
        for i, game in enumerate(pool.map(play, jobs)):
            game.update(metadata[i])
            games.append(game)
            out.write(json.dumps(game) + '\n')
            if (i + 1) % 100 == 0:
                print(f'{i + 1}/{len(jobs)} games', file=sys.stderr)
    report = {'provenance': provenance, 'comparisons': {}}
    for a, b in pairs:
        name = a + '-vs-' + b
        selected = [g for g in games if g['comparison'] == name]
        result = {'groups': {kind: statistics([g for g in selected if g['group'] == kind], a) for kind, _ in groups},
                  'overall': statistics(selected, a)}
        report['comparisons'][name] = result
        for kind, stat in [*result['groups'].items(), ('overall', result['overall'])]:
            lo, hi = stat['paired_bootstrap_95']
            print(f'{name}, {kind}: {stat["wins"]} wins, {stat["draws"]} draws, {stat["losses"]} losses; '
                  f'score {stat["score"]:.1%}, paired 95% CI {lo:.1%}–{hi:.1%}')
    if not args.levels:
        report.update(report['comparisons']['current-vs-v020'])
    (args.out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    illegal = [g for g in games if g['reason'].startswith('illegal')]
    if illegal:
        raise SystemExit(f'{len(illegal)} illegal decisions; see games.jsonl')


if __name__ == '__main__':
    main()
