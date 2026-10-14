"""Extract reproducible loss/stall positions without turning oracle facts into AI inputs."""
import argparse
from collections import Counter, defaultdict, deque
import copy
import hashlib
import json
import sys
from pathlib import Path
import zipfile

from analyze_ai_endgames import optimistic_flag_route
from feldmarschall import ROOT, Position, GLYPHS, FLAG, BOMB, MINER, SCOUT, LAKES, UNKNOWN, square_name


def permitted_view(position, army, lost):
    cells = []
    for sq, cell in enumerate(position.cells):
        if sq in LAKES:
            cells.append(254)
        elif cell is None:
            cells.append(255)
        else:
            owner, rank, moved, revealed = cell
            kind = rank if owner == army or revealed else UNKNOWN
            cells.append(kind | (16 if owner else 0) | (64 if moved else 0) | (32 if revealed else 0))
    return {'army': army, 'board_hex': bytes(cells).hex(),
            'enemy_lost_hex': bytes(lost[1-army]).hex(),
            'shuttle': {str(side): list(state) for side, state in position.shuttle.items()}, 'rules': 0}


def choose_games(games, limit):
    """Round-robin across layout and terminal outcome; avoid taking only earliest seeds."""
    buckets = defaultdict(list)
    for index, game in enumerate(games):
        if 'moves' not in game:
            continue
        sides = [army for army, name in enumerate((game['red'], game['blue']))
                 if name in ('current', 'normal', 'hard') and game['winner'] != name]
        if not sides or (game['winner'] is None and game['reason'] != 'ply limit'):
            continue
        key = (game['group'], 'stall' if game['winner'] is None else 'loss')
        stable = hashlib.sha256(json.dumps(game, sort_keys=True).encode()).hexdigest()
        buckets[key].append((stable, index, game, sides))
    queues = [deque(sorted(values)) for _, values in sorted(buckets.items())]
    selected = []
    while queues and len(selected) < limit:
        for queue in queues:
            if queue and len(selected) < limit:
                _, index, game, sides = queue.popleft()
                selected.append((index, game, sides))
        queues = [queue for queue in queues if queue]
    return selected


def extract(game, index, entry, difficulty):
    position = Position()
    for army in (0, 1):
        position.place(army, game['deployments'][army])
    sides = [army for army, name in enumerate((game['red'], game['blue']))
             if name in ('current', 'normal', 'hard') and game['winner'] != name]
    lost, recent, emitted = [[0]*12, [0]*12], [deque(maxlen=40), deque(maxlen=40)], Counter()
    last_battle, records, public_history = 0, [], []
    last_turn = {army: max((p for p in range(len(game['moves'])) if p % 2 == army), default=-1) for army in sides}
    for ply, move in enumerate(game['moves']):
        army, (src, dst) = ply % 2, move
        legal = position.moves(army)
        if (src, dst) not in legal:
            raise ValueError(f'{entry["name"]} game {index} illegal trace at {ply}')
        labels, evidence = [], {}
        moving, target = position.cells[src], position.cells[dst]
        if army in sides:
            winning = [(a, b) for a, b in legal if position.cells[b] and
                       position.cells[b][1] == FLAG and position.cells[b][3]]
            if winning and (src, dst) not in winning:
                labels.append('missed_known_flag_capture')
                evidence['visible_winning_moves'] = winning
            oracle_wins = [(a, b) for a, b in legal if position.cells[b] and position.cells[b][1] == FLAG]
            if oracle_wins and (src, dst) not in oracle_wins and not winning:
                labels.append('oracle_missed_flag_capture')
                evidence['oracle_flag_capture_alternatives'] = oracle_wins
                evidence['warning'] = 'The flag is concealed; this opportunity does not prove the AI could identify it.'
            if ply-last_battle >= 100 and len(recent[army]) == 40 and len(set(recent[army])) <= 12:
                labels.append('quiet_repetition')
                evidence['quiet_plies'] = ply-last_battle
                evidence['distinct_last_40_own_moves'] = len(set(recent[army]))
            if target and moving[1] == SCOUT and target[3] and target[1] != FLAG:
                # Observation, not proof of a mistake: this could be a necessary defence.
                if moving[1] >= target[1] or target[1] == BOMB:
                    labels.append('scout_sacrifice_without_new_information')
                    evidence['already_disclosed_defender'] = target[1]
            if target and moving[1] == MINER and target[1] == BOMB and target[3] and (
                    dst < 20 if army == 0 else dst >= 80):
                flags = [sq for sq, cell in enumerate(position.cells)
                         if cell and cell[0] != army and cell[1] == FLAG]
                if flags and abs(flags[0]//10-dst//10)+abs(flags[0]%10-dst%10) >= 4:
                    labels.append('rear_bomb_probe_with_flag_elsewhere')
                    evidence['oracle_flag_square'] = flags[0]
                    evidence['oracle_flag_was_disclosed'] = position.cells[flags[0]][3]
            if ply == last_turn[army]:
                labels.append('last_turn_before_loss' if game['winner'] else 'last_turn_before_cap')
                if not optimistic_flag_route(position, army):
                    labels.append('oracle_flag_route_unavailable')
                evidence['oracle_optimistic_flag_route'] = optimistic_flag_route(position, army)
            labels = [label for label in labels if emitted[(army, label)] < 2]
            if labels:
                for label in labels:
                    emitted[(army, label)] += 1
                identity = f'{entry["name"]}:{index}:{ply}:{army}'
                records.append({
                    'id': hashlib.sha256(identity.encode()).hexdigest()[:20],
                    'source': {'archive': entry['archive'], 'archive_sha256': entry['archive_sha256'],
                               'exact_engine_replay_available': entry.get('executable_snapshots_available', False),
                               'game_index': index, 'ply': ply, 'comparison': game['comparison'],
                               'group': game['group'], 'round': game['round'], 'seed': game['seed']},
                    'difficulty': difficulty or (game['red'], game['blue'])[army],
                    'outcome': {'winner': game['winner'], 'reason': game['reason'], 'plies': game['plies']},
                    'labels': labels, 'evidence': evidence,
                    'input': permitted_view(position, army, lost), 'chosen_move': move,
                    'public_history': list(public_history),
                    'legal_moves': legal, 'referee_board': copy.deepcopy(position.cells),
                    # Replaying this prefix reconstructs rule, random and planner state.
                    # A fresh think on input alone is deliberately not an exact replay.
                    'replay': {'deployments': game['deployments'], 'red': game['red'], 'blue': game['blue'],
                               'seed': game['seed'], 'moves_before': game['moves'][:ply]},
                })
        recent[army].append((src, dst))
        squares = f'{square_name(src)} {square_name(dst)}'
        if target is None:
            public_history.append('moved ' + squares)
            position.move(src, dst)
        else:
            public_history.append(f'battle {squares} {GLYPHS[moving[1]]} {GLYPHS[target[1]]}')
            _, fallen = position.fight(src, dst, moving[1], target[1])
            for owner, rank, _, _ in fallen:
                lost[owner][rank] += 1
            last_battle = ply+1
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, default=ROOT/'docs/ai-experiments.json')
    parser.add_argument('--games-per-run', type=int, default=24)
    parser.add_argument('--broad-games-per-run', type=int, default=96)
    parser.add_argument('--out', type=Path, required=True, help='new immutable corpus directory')
    args = parser.parse_args()
    if args.games_per_run < 1:
        parser.error('--games-per-run must be positive')
    args.out.mkdir(parents=True, exist_ok=False)
    entries = json.loads(args.ledger.read_text())
    records, runs, selected_games = [], [], 0
    for entry in entries:
        path = args.ledger.parent/entry['archive']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['archive_sha256']:
            raise ValueError(f'archive identity changed: {path}')
        with zipfile.ZipFile(path) as archive:
            games = [json.loads(line) for line in archive.read('games.jsonl').splitlines()]
            provenance = json.loads(archive.read('provenance.json'))
        limit = args.broad_games_per_run if provenance.get('suite') == 'broad' else args.games_per_run
        chosen = choose_games(games, limit)
        for index, game, _ in chosen:
            records.extend(extract(game, index, entry, provenance.get('difficulty')))
        selected_games += len(chosen)
        runs.append({'archive': entry['archive'], 'archive_sha256': entry['archive_sha256'],
                     'games': len(games), 'traced_games': sum('moves' in game for game in games),
                     'selected_games': len(chosen)})
    corpus = args.out/'positions.jsonl'
    corpus.write_text(''.join(json.dumps(record, sort_keys=True)+'\n' for record in records))
    report = {'schema': 1, 'rules': 'classic', 'source_runs': runs, 'selected_games': selected_games,
              'command': sys.argv,
              'selection_parameters': {'games_per_run': args.games_per_run,
                                       'broad_games_per_run': args.broad_games_per_run,
                                       'max_positions_per_label_per_army_per_game': 2},
              'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                                ('tools/build_ai_diagnostics.py', 'tools/analyze_ai_endgames.py', 'tools/feldmarschall.py')},
              'positions': len(records), 'positions_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(),
              'labels': dict(Counter(label for record in records for label in record['labels'])),
              'groups': dict(Counter(record['source']['group'] for record in records)),
              'selection': 'deterministic hash ordering, round-robin layout/outcome buckets per run',
              'warning': 'Labels are observable symptoms or explicitly oracle-labelled facts, not proof of inferior moves. Teacher features may use input and public_history only; replay deployments, referee_board, labels and evidence can contain concealed truth.'}
    (args.out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ('selected_games', 'positions', 'labels', 'groups')}))


if __name__ == '__main__':
    main()
