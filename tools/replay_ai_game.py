"""Reproduce a recorded game with persistent engine state and optional tracing."""
import argparse
import json
import sys
import shlex
from pathlib import Path

from feldmarschall import ROOT, Engine, Position, RED, BLUE, GLYPHS, parse_square, square_name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('games', type=Path)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--comparison', required=True)
    parser.add_argument('--red', required=True, help='name of the red engine in the recorded game')
    parser.add_argument('--engine', default=str(ROOT / 'build/feldmarschall-engine-trace'))
    parser.add_argument('--opponent-engine', default=str(ROOT / 'build/feldmarschall-ai-20261014'),
                        help='binary for the frozen milestone in progress benchmarks')
    parser.add_argument('--difficulty', choices=('easy', 'normal', 'hard'),
                        help='level for current/reference comparisons; defaults to run provenance')
    parser.add_argument('--recorded-engines', action='store_true',
                        help='use retained programs and support scripts from this run')
    parser.add_argument('--trace-start', type=int, default=180, help='zero-based ply, inclusive')
    parser.add_argument('--trace-end', type=int, default=190, help='zero-based ply, exclusive')
    args = parser.parse_args()
    games = [json.loads(line) for line in args.games.read_text().splitlines()]
    matches = [g for g in games if g['seed'] == args.seed and g['comparison'] == args.comparison and g['red'] == args.red]
    if len(matches) != 1:
        parser.error('selection must identify exactly one recorded game')
    game = matches[0]
    provenance_path = args.games.parent / 'provenance.json'
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else {}
    configured_level = args.difficulty or provenance.get('difficulty') or 'normal'
    truth, engines = Position(), []
    try:
        for army, level in ((RED, game['red']), (BLUE, game['blue'])):
            is_milestone = level not in ('easy', 'normal', 'hard', 'current')
            command = args.opponent_engine if is_milestone else args.engine
            difficulty = configured_level if is_milestone or level == 'current' else level
            if args.recorded_engines:
                argv = shlex.split(provenance['run_engine_commands'][level])
                argv[0] = str((args.games.parent / 'engines' / level).resolve())
                for i, value in enumerate(argv[1:], 1):
                    if value.endswith('.py'):
                        argv[i] = str((args.games.parent / 'engines/support' / level / Path(value).name).resolve())
                command = shlex.join(argv)
            else:
                command += ' --difficulty ' + difficulty
            engine = Engine(command)
            engines.append(engine)
            engine.send(f"seed {game['seed'] * 2 + army + 1}")
            engine.send('new ' + ('red', 'blue')[army])
            engine.send('setup ' + game['deployments'][army])
            truth.place(army, game['deployments'][army])
        for ply, (src, dst) in enumerate(game['moves']):
            army = ply % 2
            tracing = args.trace_start <= ply < args.trace_end
            if not args.recorded_engines and (game['red'], game['blue'])[army] in ('easy', 'normal', 'hard', 'current'):
                engines[army].send('trace ' + ('on' if tracing else 'off'))
            if tracing:
                print(f'ply {ply} army={army}', file=sys.stderr, flush=True)
            answer = tuple(map(parse_square, engines[army].ask('go', 'move').split()))
            if answer != (src, dst):
                raise SystemExit(f'first divergence at ply {ply}: {answer} != {(src, dst)}')
            assert answer in truth.moves(army)
            names = f'{square_name(src)} {square_name(dst)}'
            if truth.cells[dst] is None:
                truth.move(src, dst)
                notification = f'moved {names}'
            else:
                attacker, defender = truth.cells[src][1], truth.cells[dst][1]
                truth.fight(src, dst, attacker, defender)
                notification = f'battle {names} {GLYPHS[attacker]} {GLYPHS[defender]}'
            for engine in engines:
                engine.send(notification)
        print(f"Reproduced {len(game['moves'])} plies with identical decisions and persistent state")
    finally:
        for engine in engines:
            engine.close()


if __name__ == '__main__':
    main()
