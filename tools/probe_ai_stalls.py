"""Replay selected capped Normal games with the old and candidate evaluators.

This is a diagnostic corpus selected for stalls, not an independent strength
benchmark. Both versions use the original deployments, sides, and move seeds.
"""
import argparse
import hashlib
import json
from pathlib import Path

from arena import play
from feldmarschall import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('games', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    games = [json.loads(line) for line in args.games.read_text().splitlines()]
    selected = [game for game in games if game['reason'] == 'ply limit']
    results = []
    for game in selected:
        old_commands = tuple(str(ROOT / 'build' / ('feldmarschall-ai-normal-progress' if name == 'current' else 'feldmarschall-ai-20261014')) + ' --difficulty normal' for name in (game['red'], game['blue']))
        new_commands = tuple(str(ROOT / 'build' / ('feldmarschall-engine' if name == 'current' else 'feldmarschall-ai-20261014')) + ' --difficulty normal' for name in (game['red'], game['blue']))
        names = (game['red'], game['blue'])
        common = (tuple(game['deployments']), game['seed'], 1000, True)
        old = play((names, old_commands, *common))
        if old.get('moves') != game['moves']:
            raise RuntimeError('reference no longer reproduces recorded game')
        new = play((names, new_commands, *common))
        results.append({'group': game['group'], 'round': game['round'], 'deployments': game['deployments'], 'reference': old, 'candidate': new})
    report = {
        'source_sha256': hashlib.sha256((ROOT / 'src/core/ai.c').read_bytes()).hexdigest(),
        'input_sha256': hashlib.sha256(args.games.read_bytes()).hexdigest(),
        'selected_games': len(selected),
        'candidate_caps': sum(r['candidate']['reason'] == 'ply limit' for r in results),
        'results': results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(f"{len(selected)} reproduced caps; candidate still capped in {report['candidate_caps']} games")


if __name__ == '__main__':
    main()
