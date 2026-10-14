"""Curate public-only mission diagnostics; oracle labels select examples only."""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import zipfile

from feldmarschall import (ROOT, GLYPHS, MINER, SCOUT, BOMB, FLAG, UNKNOWN,
                          battle, parse_square, square_name)


def neighbors(sq):
    return [to for to in (sq - 10, sq + 10, sq - 1 if sq % 10 else -1,
                         sq + 1 if sq % 10 < 9 else -1) if 0 <= to < 100]


def public_analysis(info, history, chosen, legal):
    """Only permitted state, public events and observable actions enter analysis."""
    cells = list(bytes.fromhex(info['board_hex']))
    army = info['army']
    own = lambda cell: cell < 254 and bool(cell & 16) == bool(army)
    mobile = [sq for sq, cell in enumerate(cells) if own(cell) and (cell & 15) < BOMB]
    miners = [sq for sq in mobile if (cells[sq] & 15) == MINER]
    flags = [sq for sq, cell in enumerate(cells) if own(cell) and (cell & 15) == FLAG]
    possible_flags = [sq for sq, cell in enumerate(cells) if cell < 254 and not own(cell)
                      and ((cell & 32 and (cell & 15) == FLAG) or not cell & 96)]
    barriers = {sq for sq, cell in enumerate(cells) if cell == 254 or
                (own(cell) and (cell & 15) >= BOMB) or
                (cell < 254 and not own(cell) and cell & 32 and (cell & 15) == BOMB and not miners)}
    def reach(blocking):
        reachable = set(mobile)
        queue = deque(mobile)
        while queue:
            for to in neighbors(queue.popleft()):
                if to not in blocking and to not in reachable:
                    reachable.add(to); queue.append(to)
        return reachable
    reachable = reach(barriers)
    # This removes mobile blockers and treats unknown pieces optimistically.
    # Failure proves a static topological obstruction, not a hidden-rank claim.
    blocked = not bool(reachable.intersection(possible_flags))
    # An enemy miner could remove one of our stationary bombs. Permit that
    # cooperation before calling a direct flag-route obstruction permanent.
    lost = bytes.fromhex(info.get('enemy_lost_hex', '00' * 12))
    opponent_miners = 5 - lost[MINER]
    permanent = {sq for sq in barriers if not (opponent_miners and own(cells[sq]) and
                                               (cells[sq] & 15) == BOMB)}
    permanent_blockage = not bool(reach(permanent).intersection(possible_flags))
    recent = [tuple(map(parse_square, event.split()[1:3])) for event in history[army::2][-40:]]
    known_enemy = [sq for sq, cell in enumerate(cells) if cell < 254 and not own(cell)
                   and cell & 32 and (cell & 15) < BOMB]
    def danger(to, rank, src):
        threats = []
        for sq in known_enemy:
            if sq == to:
                continue
            distance = abs(sq // 10 - to // 10) + abs(sq % 10 - to % 10)
            can_reach = distance == 1
            if (cells[sq] & 15) == SCOUT and (sq // 10 == to // 10 or sq % 10 == to % 10):
                step = 10 if to > sq and to % 10 == sq % 10 else -10 if to % 10 == sq % 10 else 1 if to > sq else -1
                can_reach = all(cells[mid] == 255 or mid == src for mid in range(sq + step, to, step))
            if can_reach and battle(cells[sq] & 15, rank) != 'defender':
                threats.append(sq)
        return threats
    alternatives = []
    for src, to in legal:
        if [src, to] == chosen:
            continue
        rank, target = cells[src] & 15, cells[to]
        known_loss = target < 254 and target & 32 and battle(rank, target & 15) != 'attacker'
        threats = danger(to, rank, src)
        novelty = (src, to) not in recent
        investigating = target < 254 and not target & 32
        forward = (to // 10 - src // 10) * (1 if army else -1)
        utility = (40 if src == chosen[0] else 0) + 20 * novelty + 5 * forward
        utility += 20 * investigating - 100 * known_loss - 40 * len(threats)
        if target < 254 and target & 32 and (target & 15) == FLAG:
            utility += 10000
        reasons = []
        if src == chosen[0]: reasons.append('redirect the same specialist or actor')
        if novelty: reasons.append('avoid repeating one of the last 40 own moves')
        if forward > 0: reasons.append('advance toward opposing deployment rows')
        if investigating: reasons.append('investigate a concealed defender')
        if target == 255: reasons.append('keep the piece instead of this turn\'s capture attempt')
        if known_loss: reasons.append('known losing exchange; consider only for necessary flag defence')
        if threats: reasons.append('disclosed immediate recapture threats remain')
        alternatives.append({'move': [src, to], 'reasons': reasons,
                             'known_losing_capture': bool(known_loss),
                             'disclosed_reply_threats': threats, 'recent_move': not novelty,
                             'utility_for_curating': utility})
    alternatives.sort(key=lambda entry: (-entry['utility_for_curating'], entry['move']))
    chosen_src, chosen_to = chosen
    rank, target = cells[chosen_src] & 15, cells[chosen_to]
    return {'structural_status': 'blocked_by_stationary_barriers' if blocked else 'optimistic_route_exists',
            'route_scope': 'All public flag candidates; mobile blockers removable; concealed ranks optimistic. A route does not prove a winning continuation.',
            'public_flag_candidates': possible_flags,
            'stationary_barriers': sorted(barriers), 'own_miners': miners, 'own_flags': flags,
            'permanent_barriers': sorted(permanent), 'opponent_miners_remaining': opponent_miners,
            'permanent_flag_route_blockage': permanent_blockage,
            'blockage_scope': 'Direct flag capture only. Removing our bombs by an opposing Miner is allowed optimistically; winning by immobilizing the opponent is a separate question.',
            'distinct_last_40_own_moves': len(set(recent)),
            'chosen_move_recent': tuple(chosen) in recent,
            'chosen_known_losing_capture': bool(target < 254 and target & 32 and battle(rank, target & 15) != 'attacker'),
            'alternatives': alternatives[:3],
            'interpretation': 'Alternatives are legal public-information hypotheses, not oracle-labelled best moves. Check flag defence and concealed reply risk before calling a sacrifice avoidable.'}


def public_case(record, category):
    return {'id': record['id'], 'category': category, 'difficulty': record['difficulty'],
            'source': record['source'], 'input': record['input'],
            'public_history': record['public_history'], 'chosen_move': record['chosen_move'],
            'legal_moves': record['legal_moves'],
            'own_initial_setup': record['replay']['deployments'][record['input']['army']],
            'analysis': public_analysis(record['input'], record['public_history'],
                                        record['chosen_move'], record['legal_moves'])}


def select(records):
    chosen, seen_games = [], set()
    def add(category, candidates, count):
        candidates.sort(key=lambda r: (r['source']['group'] != 'decoy',
                                      not r['source']['archive'].startswith('ai-runs/broad-'), r['id']))
        selected = []
        for record in candidates:
            game = (record['source']['archive'], record['source']['game_index'])
            if game in seen_games or not record['legal_moves']:
                continue
            case = public_case(record, category)
            if not case['analysis']['alternatives']:
                continue
            selected.append(case); seen_games.add(game)
            if len(selected) == count: break
        if len(selected) != count:
            raise ValueError(f'{category}: only {len(selected)} independent examples')
        chosen.extend(selected)
    quiet = [r for r in records if 'quiet_repetition' in r['labels']]
    blocked = [r for r in quiet if public_case(r, 'blocked')['analysis']['permanent_flag_route_blockage']]
    add('stationary_blockage_control', blocked, 2)
    add('rear_guard_decoy', [r for r in records if 'rear_bomb_probe_with_flag_elsewhere' in r['labels']], 4)
    add('quiet_repetition', [r for r in quiet if r not in blocked], 4)
    add('ineffective_miner_approach', [r for r in records
        if (bytes.fromhex(r['input']['board_hex'])[r['chosen_move'][0]] & 15) == MINER
        and any(label in r['labels'] for label in ('quiet_repetition', 'oracle_flag_route_unavailable', 'last_turn_before_cap'))], 4)
    add('disclosed_specialist_loss', [r for r in records if 'scout_sacrifice_without_new_information' in r['labels']], 4)
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, default=ROOT / 'docs/ai-diagnostics/positions-20261014.zip')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    with zipfile.ZipFile(args.corpus) as archive:
        records = [json.loads(line) for line in archive.read('positions.jsonl').splitlines()]
    cases = select(records)
    args.out.mkdir(parents=True, exist_ok=False)
    data = ''.join(json.dumps(case, sort_keys=True) + '\n' for case in cases).encode()
    (args.out / 'cases.jsonl').write_bytes(data)
    manifest = {'schema': 1, 'cases': len(cases), 'source_corpus': str(args.corpus),
                'source_corpus_sha256': hashlib.sha256(args.corpus.read_bytes()).hexdigest(),
                'cases_sha256': hashlib.sha256(data).hexdigest(),
                'analysis_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'scope': 'Diagnostic development set. Excluded from strength claims; analysis contains no referee ranks, enemy initial deployment or oracle evidence.'}
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
