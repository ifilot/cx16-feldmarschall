"""Referee: play matches between programs that speak the engine protocol.

Usage:
  python3 tools/arena.py --engine ai=build/feldmarschall-engine \\
                         --engine greedy="python3 tools/bots.py greedy" \\
                         [--rounds 20] [--setups mixed] [--jobs 8] [--out build/results.jsonl]

Every pair of engines plays `rounds` rounds. A round draws two deployments
(the ten presets of src/core/presets.c, random ones, or a mix) and plays
them twice with the engines' sides swapped, so neither profits from a lucky
setup. The referee holds the true position, checks every move, and tells
both engines what happened: "moved a4 a5", or "battle a4 a5 7 9" with both
ranks. A game ends when a flag falls, when the side to move has no legal
move, or as a draw after --max-plies. Results are appended to --out as JSON
lines for tools/rating.py.
"""
import argparse
import itertools
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from feldmarschall import (BLUE, FLAG, GLYPHS, RED, ROOT, Engine, Position, new_rng, parse_square,
                      presets, random_setup, square_name, valid_setup, stress_setup, STRESS_SETUPS)


def play(job):
    """Play one game; job = (red name, red command, blue name, blue command, setups, seed, max plies)."""
    names, commands, setups, seed, max_plies, *options = job
    record_moves = bool(options and options[0])
    moves = []
    truth = Position()
    engines = []
    try:
        for army in (RED, BLUE):
            engine = Engine(commands[army], names[army])
            engine.send(f'seed {seed * 2 + army + 1}')
            engine.send('new ' + ('red', 'blue')[army])
            engine.send('setup ' + setups[army])
            truth.place(army, setups[army])
            engines.append(engine)
        side, plies, winner, reason = RED, 0, None, ''
        while True:
            legal = truth.moves(side)
            if not legal:
                # the side to move loses, unless neither can move (play.c: stuck)
                if truth.moves(1 - side):
                    winner, reason = 1 - side, 'no moves'
                else:
                    reason = 'neither can move'
                break
            if plies >= max_plies:
                reason = 'ply limit'
                break
            answer = engines[side].ask('go', 'move').split()
            try:
                move = (parse_square(answer[0]), parse_square(answer[1]))
            except (ValueError, IndexError):
                move = None
            if move not in legal:
                winner, reason = 1 - side, 'illegal move ' + ' '.join(answer)
                break
            src, dst = move
            if record_moves:
                moves.append([src, dst])
            names_sq = f'{square_name(src)} {square_name(dst)}'
            if truth.cells[dst] is None:
                truth.move(src, dst)
                for engine in engines:
                    engine.send(f'moved {names_sq}')
            else:
                attacker, defender = truth.cells[src][1], truth.cells[dst][1]
                truth.fight(src, dst, attacker, defender)
                for engine in engines:
                    engine.send(f'battle {names_sq} {GLYPHS[attacker]} {GLYPHS[defender]}')
                if defender == FLAG:
                    winner, reason = side, 'flag'
                    plies += 1
                    break
            side = 1 - side
            plies += 1
    finally:
        for engine in engines:
            engine.close()
    result = {'red': names[RED], 'blue': names[BLUE], 'winner': None if winner is None else names[winner],
            'result': {None: 'draw', RED: 'red', BLUE: 'blue'}[winner], 'reason': reason,
            'plies': plies, 'seed': seed}
    if record_moves:
        result['moves'] = moves
    return result


def deployments(kind, rng):
    if kind in STRESS_SETUPS:
        return stress_setup(kind, rng)
    if kind == 'broad-mixed':
        return deployments(rng.choice((*STRESS_SETUPS, 'presets')), rng)
    if kind == 'presets' or (kind == 'mixed' and rng.random() < 0.5):
        return rng.choice(presets())[1]
    return random_setup(rng)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--engine', action='append', required=True, metavar='NAME=COMMAND')
    parser.add_argument('--rounds', type=int, default=10)
    parser.add_argument('--setups', choices=('random', 'presets', 'mixed', 'broad-mixed', *STRESS_SETUPS), default='mixed')
    parser.add_argument('--max-plies', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--jobs', type=int, default=os.cpu_count())
    parser.add_argument('--out', default=str(ROOT / 'build/results.jsonl'))
    args = parser.parse_args()

    engines = dict(e.split('=', 1) for e in args.engine)
    rng = new_rng(args.seed)
    jobs = []
    for a, b in itertools.combinations(engines, 2):
        for _ in range(args.rounds):
            first, second = deployments(args.setups, rng), deployments(args.setups, rng)
            assert valid_setup(first) and valid_setup(second)
            seed = rng.randrange(1, 60000)
            for red, blue in ((a, b), (b, a)):
                jobs.append(((red, blue), (engines[red], engines[blue]), (first, second), seed, args.max_plies))

    score = {name: [0.0, 0] for name in engines}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'a') as out, ProcessPoolExecutor(args.jobs) as pool:
        for n, game in enumerate(pool.map(play, jobs), 1):
            out.write(json.dumps(game) + '\n')
            for army in ('red', 'blue'):
                name = game[army]
                score[name][1] += 1
                score[name][0] += 1 if game['winner'] == name else 0.5 if game['winner'] is None else 0
            if game['reason'].startswith('illegal'):
                print(f'game {n}: {game["red"]} vs {game["blue"]}: {game["reason"]}', file=sys.stderr)
            print(f'\r{n}/{len(jobs)} games', end='', file=sys.stderr)
    print(file=sys.stderr)
    for name, (points, games) in sorted(score.items(), key=lambda kv: -kv[1][0] / max(1, kv[1][1])):
        print(f'{name:12s} {points:6.1f} / {games:4d}  ({100 * points / max(1, games):5.1f}%)')


if __name__ == '__main__':
    main()
