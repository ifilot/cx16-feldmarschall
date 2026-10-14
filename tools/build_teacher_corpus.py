"""Sample public training positions across Classic development games and phases."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from build_ai_diagnostics import permitted_view
from feldmarschall import Position, GLYPHS, square_name


def phase(ply):
    return 'opening' if ply < 60 else 'middle' if ply < 180 else 'late'


def select(games, per_bucket):
    buckets = defaultdict(list)
    for index, game in enumerate(games):
        for ply in range(len(game['moves'])):
            key = (game['group'], phase(ply), ply % 2)
            identity = f"{game['group']}:{game['seed']}:{index}:{ply}"
            buckets[key].append((hashlib.sha256(identity.encode()).hexdigest(), index, ply))
    return {(index, ply) for values in buckets.values()
            for _, index, ply in sorted(values)[:per_bucket]}


def extract(games, selected, source_sha):
    for index, game in enumerate(games):
        position = Position()
        for army in (0, 1): position.place(army, game['deployments'][army])
        lost, history = [[0] * 12, [0] * 12], []
        for ply, move in enumerate(game['moves']):
            army = ply % 2
            src, dst = move
            if (src, dst) not in position.moves(army):
                raise ValueError(f'illegal source trace: game {index}, ply {ply}')
            if (index, ply) in selected:
                identity = f'{source_sha}:{index}:{ply}'
                yield {'id': hashlib.sha256(identity.encode()).hexdigest()[:20],
                       'source': {'group': game['group'], 'seed': game['seed'],
                                  'game_index': index, 'ply': ply, 'phase': phase(ply)},
                       'input': permitted_view(position, army, lost),
                       'public_history': list(history)}
            moving, target = position.cells[src], position.cells[dst]
            squares = f'{square_name(src)} {square_name(dst)}'
            if target is None:
                history.append('moved ' + squares)
                position.move(src, dst)
            else:
                history.append(f'battle {squares} {GLYPHS[moving[1]]} {GLYPHS[target[1]]}')
                _, fallen = position.fight(src, dst, moving[1], target[1])
                for owner, rank, _, _ in fallen: lost[owner][rank] += 1


def build(run, out, per_bucket):
    provenance = json.loads((run / 'provenance.json').read_text())
    if provenance.get('phase') != 'development' or provenance.get('suite') != 'broad':
        raise ValueError('only broad development games may supply this training corpus')
    if provenance.get('difficulty') != 'normal':
        raise ValueError('this corpus currently supports Classic Normal only')
    raw = (run / 'games.jsonl').read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    games = [json.loads(line) for line in raw.splitlines()]
    if provenance.get('rules', 0) or any(game.get('rules', 0) for game in games):
        raise ValueError('Classic rules required')
    if not games or any('moves' not in game or 'deployments' not in game for game in games):
        raise ValueError('complete game traces and deployments required')
    if per_bucket < 1: raise ValueError('positive bucket size required')
    selected = select(games, per_bucket)
    records = list(extract(games, selected, source_sha))
    if len(records) != len(selected): raise ValueError('selected positions missing')
    out.mkdir(parents=True, exist_ok=False)
    corpus = out / 'positions.jsonl'
    corpus.write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in records))
    report = {'schema': 1, 'source_run': str(run.resolve()), 'source_games_sha256': source_sha,
              'source_provenance_sha256': hashlib.sha256((run / 'provenance.json').read_bytes()).hexdigest(),
              'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'positions_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(),
              'source_games': len(games), 'positions': len(records), 'per_bucket': per_bucket,
              'coverage': dict(sorted(Counter(f"{r['source']['group']}:{r['source']['phase']}:{r['input']['army']}"
                                              for r in records).items())),
              'selection': 'smallest deterministic hashes per layout family, phase and army; independent of outcome',
              'scope': 'public input/history only; family and seed are split metadata, never model features'}
    (out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--per-bucket', type=int, default=24)
    args = parser.parse_args()
    print(json.dumps(build(args.run, args.out, args.per_bucket), indent=2))
