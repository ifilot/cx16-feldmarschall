"""Classic development-cycle tournaments and matched, family-stratified evidence."""
import argparse
from collections import defaultdict
import contextlib
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys

from ai_registry import ROOT, get_policy
from tournament import run
from tournament_store import Tournament, verify

BASE = ROOT / 'docs/ai-cycle-2026-10-15'


def plan():
    return json.loads((BASE / 'plan.json').read_text())


def score(game, identity):
    return .5 if game['result'] == 'draw' else float(game['result'] == ('red' if game['red'] == identity else 'blue'))


def interval(families):
    rng = random.Random(8675309)
    draws = sorted(sum(rng.choice(values) for values in families.values() for _ in values) /
                   sum(map(len, families.values())) for _ in range(10000))
    return [draws[249], draws[9749]]


def evidence(path, identity):
    summary = verify(path)
    with Tournament(path) as tournament:
        games = tournament.games()
        pairs = defaultdict(list)
        for game in games:
            pairs[(game['family'], game['pair_id'])].append(score(game, identity))
        families = defaultdict(list)
        for (family, _), values in pairs.items():
            assert len(values) == 2
            families[family].append(sum(values) / 2)
        return dict(path=str(Path(path).relative_to(ROOT)), sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                    identity=identity, games=len(games), score=summary['standings'][identity]['score'],
                    paired_95=interval(families), capped=summary['endings'].get('ply limit', 0),
                    families=summary['families'], endings=summary['endings'])


def play(first, second, stage, seed, rounds):
    config = plan()
    directory = BASE / 'tournaments' / stage
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{first}--{second}.fmtour'
    if path.exists():
        with Tournament(path) as tournament:
            metadata = tournament.metadata()
            assert metadata['status'] == 'complete', f'Existing incomplete run must be inspected: {path}'
            assert metadata['seed'] == seed and metadata['rounds'] == rounds
            assert [p['policy'] for p in metadata['participants']] == [get_policy(first), get_policy(second)]
        verify(path)
    else:
        print(f'Start {stage}: {first} versus {second}, {rounds * 14} games', flush=True)
        with (directory / f'{first}--{second}.log').open('x') as log, contextlib.redirect_stdout(log):
            run(first, second, path, rounds=rounds, seed=seed, jobs=config['workers'],
                families=config['families'], max_plies=config['max_plies'], backend='openmp')
    report = evidence(path, first)
    print(f'Finished {first}: {report["score"]:.3%} ({report["games"]} games)', flush=True)
    return path, report


def baseline():
    config = plan()
    rows = []
    for first, second in itertools.combinations(config['league'], 2):
        _, report = play(first, second, 'baseline', config['seeds']['baseline'], config['baseline_rounds'])
        rows.append(report)
    (BASE / 'baseline.json').write_text(json.dumps(dict(plan_sha256=hashlib.sha256((BASE/'plan.json').read_bytes()).hexdigest(),
                                                      comparisons=rows), indent=2) + '\n')


def matched(candidate_paths, control_paths, identity, control):
    blocks = defaultdict(list)
    totals = [[], []]
    opponents = {}
    for opponent, path in candidate_paths.items():
        other_path = control_paths[opponent]
        with Tournament(path) as a, Tournament(other_path) as b:
            assert a.metadata()['seed'] == b.metadata()['seed']
            assert a.metadata()['rounds'] == b.metadata()['rounds']
            ag, bg = a.games(), b.games()
            assert len(ag) == len(bg)
            av, bv = [], []
            for ga, gb in zip(ag, bg):
                assert all(ga[k] == gb[k] for k in ('id', 'family', 'pair_id', 'seed'))
                aa, bb = a.game(ga['id']), b.game(gb['id'])
                assert all(aa[k] == bb[k] for k in ('red_setup', 'blue_setup'))
                sa, sb = score(ga, identity), score(gb, control)
                blocks[(ga['family'], ga['pair_id'])].append(sa - sb)
                totals[0].append(sa); totals[1].append(sb)
                av.append(sa); bv.append(sb)
            opponents[opponent] = dict(candidate=sum(av)/len(av), control=sum(bv)/len(bv), games=len(av))
    families = defaultdict(list)
    for (family, _), values in blocks.items():
        assert len(values) == 2 * len(candidate_paths)
        families[family].append(sum(values)/len(values))
    return dict(candidate=sum(totals[0])/len(totals[0]), control=sum(totals[1])/len(totals[1]),
                difference=(sum(totals[0])-sum(totals[1]))/len(totals[0]),
                block_95=interval(families), games_per_policy=len(totals[0]), opponents=opponents,
                method='10000 bootstrap resamples of complete opponent-and-side blocks within each layout family')


def compare(identity, stage, validation=False):
    config = plan()
    seed = config['seeds'][stage + ('_val' if validation else '_dev')]
    rounds = config['validation_head_to_head_rounds'] if validation else config['development_rounds']
    label = stage + ('-validation' if validation else '-development')
    _, head = play(identity, config['baseline'], label, seed, rounds)
    report = dict(candidate=identity, stage=label, head_to_head=head,
                  development_gate=head['score'] >= .52, validation=validation)
    if validation:
        candidate_paths, control_paths = {}, {}
        for opponent in config['opponents']:
            if opponent == identity:
                continue
            candidate_paths[opponent] = play(identity, opponent, label + '-league', seed + 1000,
                                             config['validation_league_rounds'])[0]
            control_paths[opponent] = play(config['baseline'], opponent, label + '-control', seed + 1000,
                                           config['validation_league_rounds'])[0]
        report['league'] = matched(candidate_paths, control_paths, identity, config['baseline'])
        report['strength_gate'] = head['paired_95'][0] > .5 and report['league']['block_95'][0] > 0
    (BASE / (label + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('baseline')
    c = commands.add_parser('compare'); c.add_argument('identity'); c.add_argument('stage', choices=('priorities','plans','teacher','student'))
    c.add_argument('--validation', action='store_true')
    args = parser.parse_args()
    if args.command == 'baseline': baseline()
    else: print(json.dumps(compare(args.identity, args.stage, args.validation), indent=2))
