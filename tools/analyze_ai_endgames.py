"""Replay capped benchmark games and summarize observable stall symptoms."""
import argparse
from collections import Counter
import json
from pathlib import Path

from feldmarschall import Position, RED, BLUE, FLAG, BOMB, MINER, LAKES


def optimistic_flag_route(position, army):
    """Ignore mobile blockers; even this optimistic test may find a sealed flag."""
    flags = {sq for sq, cell in enumerate(position.cells) if cell and cell[0] != army and cell[1] == FLAG}
    for start, cell in enumerate(position.cells):
        if not cell or cell[0] != army or cell[1] >= BOMB:
            continue
        pending, seen = [start], {start}
        for sq in pending:
            if sq in flags:
                return True
            for nb in (sq - 10, sq + 10, sq - 1, sq + 1):
                if not 0 <= nb < 100 or nb in LAKES or nb in seen:
                    continue
                if abs(nb // 10 - sq // 10) + abs(nb % 10 - sq % 10) != 1:
                    continue
                target = position.cells[nb]
                if target and target[1] == BOMB and (target[0] == army or cell[1] != MINER):
                    continue
                if target and target[1] == FLAG and target[0] == army:
                    continue
                seen.add(nb)
                pending.append(nb)
    return False


def analyze(game):
    if len(game['moves']) != game['plies']:
        raise ValueError('incomplete move trace')
    position = Position()
    for army in (RED, BLUE):
        position.place(army, game['deployments'][army])
    last_battle = 0
    for ply, (src, dst) in enumerate(game['moves'], 1):
        assert (src, dst) in position.moves((ply - 1) % 2), (ply, src, dst)
        if position.cells[dst] is None:
            position.move(src, dst)
        else:
            attacker, defender = position.cells[src][1], position.cells[dst][1]
            position.fight(src, dst, attacker, defender)
            last_battle = ply
    tail = game['moves'][-100:]
    return {
        'comparison': game['comparison'], 'group': game['group'], 'round': game['round'],
        'seed': game['seed'], 'red': game['red'], 'blue': game['blue'],
        'plies_since_last_battle': len(game['moves']) - last_battle,
        'distinct_moves_last_100': len({tuple(move) for move in tail}),
        'remaining_ranks': [dict(Counter(cell[1] for cell in position.cells if cell and cell[0] == army)) for army in (RED, BLUE)],
        'flags_remaining': sum(bool(cell and cell[1] == FLAG) for cell in position.cells),
        'optimistic_flag_routes': [optimistic_flag_route(position, army) for army in (RED, BLUE)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('games', type=Path)
    args = parser.parse_args()
    games = [json.loads(line) for line in args.games.read_text().splitlines()]
    capped = [game for game in games if game['reason'] == 'ply limit']
    if any('moves' not in game for game in capped):
        parser.error('move traces required; run benchmark_ai.py --record-moves')
    records = [analyze(game) for game in capped]
    print(json.dumps({'games': len(games), 'capped_games': len(records),
                      'caps_without_battle_last_100': sum(r['plies_since_last_battle'] >= 100 for r in records),
                      'records': records}, indent=2))


if __name__ == '__main__':
    main()
