"""Describe public combat losses and terminal Flag-defense opportunities.

Physical setup ranks are used only for exact referee replay. Combat rank labels
become public on that event. Counterfactual combat outcomes are labeled offline
diagnostics; they are never passed to an AI during a decision.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from feldmarschall import FLAG, GLYPHS, MARSHAL, MINER, Position, battle
from tournament_store import Tournament


def clone(position):
    result = Position()
    result.cells = [None if c is None else list(c) for c in position.cells]
    result.shuttle = dict(position.shuttle)
    return result


def analyze(path, policy):
    counters = defaultdict(Counter)
    rows = []
    scored = 0
    with Tournament(path) as tournament:
        for entry in tournament.games():
            if entry['result'] == 'error':
                continue
            game = tournament.game(entry['id'])
            if policy not in (game['red'], game['blue']):
                continue
            scored += 1
            side = int(game['blue'] == policy)
            result = ('draw' if game['result'] == 'draw' else
                      'win' if game['result'] == ('red', 'blue')[side] else 'loss')
            counters['results'][result] += 1
            position = Position()
            position.place(0, game['red_setup'])
            position.place(1, game['blue_setup'])
            previous_root = None
            for ply, (src, dst) in enumerate(game['moves']):
                assert (src, dst) in position.moves(ply % 2)
                if ply % 2 == side:
                    previous_root = clone(position)
                a, d = position.cells[src], position.cells[dst]
                if d is None:
                    position.move(src, dst)
                    continue
                our, enemy = (a, d) if a[0] == side else (d, a)
                attacking = a[0] == side
                outcome = battle(a[1], d[1])
                died = outcome in (('defender', 'both') if attacking else ('attacker', 'both'))
                if died:
                    counters['own_deaths_' + result][GLYPHS[our[1]]] += 1
                    if our[1] in (MARSHAL, MINER):
                        label = '|'.join((GLYPHS[enemy[1]], 'attacking' if attacking else 'defending',
                                          'known' if enemy[3] else 'concealed'))
                        counters[('marshal' if our[1] == MARSHAL else 'miner') + '_death_causes'][label] += 1
                if our[1] == MINER and enemy[1] == 10:
                    counters['miner_bomb_defuses'][result] += 1
                if d[1] == FLAG:
                    counters['flag_captor_' + result][GLYPHS[a[1]]] += 1
                    if result == 'loss':
                        if previous_root is None:
                            counters['terminal_flag_threats']['no preceding own decision'] += 1
                        else:
                            prior = previous_root.cells[src]
                            assert prior is not None and prior[0] != side
                            distance = abs(src//10-dst//10) + abs(src % 10-dst % 10)
                            key = '|'.join(('adjacent' if distance == 1 else 'ray',
                                            'known' if prior[3] else 'concealed',
                                            'moved' if prior[2] else 'unmoved'))
                            counters['terminal_flag_threats'][key] += 1
                            if distance == 1 and prior[2] and not prior[3]:
                                attempts = [m for m in previous_root.moves(side) if m[1] == src]
                                responses = [dict(move=m, own_rank=GLYPHS[previous_root.cells[m[0]][1]],
                                                  removes_every_mobile_rank=all(
                                                      battle(previous_root.cells[m[0]][1], rank) != 'defender'
                                                      for rank in range(10)),
                                                  offline_actual_outcome=battle(previous_root.cells[m[0]][1], prior[1]))
                                             for m in attempts]
                                rows.append(dict(game=game['id'], family=game['family'], ply=ply,
                                                 attacker_rank_disclosed_on_final_event=GLYPHS[a[1]],
                                                 src=src, flag=dst, legal_capture_responses=responses))
                position.fight(src, dst, a[1], d[1])
            if result == 'loss':
                counters['loss_endings'][game['reason']] += 1
                miners = sum(c is not None and c[0] == side and c[1] == MINER for c in position.cells)
                counters['miners_remaining_at_loss'][str(miners)] += 1
    return dict(tournament=str(path), tournament_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                policy=policy, scored_games=scored, counters=dict(counters),
                concealed_moved_adjacent_terminal_cases=len(rows),
                cases_with_any_legal_capture=sum(bool(r['legal_capture_responses']) for r in rows),
                cases_with_guaranteed_capture=sum(any(q['removes_every_mobile_rank'] for q in r['legal_capture_responses']) for r in rows),
                cases_with_offline_actual_successful_capture=sum(any(q['offline_actual_outcome'] != 'defender' for q in r['legal_capture_responses']) for r in rows),
                cases=rows,
                finding='Classic public movement establishes mobile status. Existing flag_threats counts only disclosed ranks; adjacent moved concealed attackers are also logically certain Flag threats.',
                hypothesis='Count this public logical threat under an isolated compile guard, retaining the existing defense evaluation.',
                limits=['Terminal positions are descriptive; changing earlier choices changes the game.',
                        'No historical concealed moved terminal case has a legal capture that succeeds against the subsequently disclosed rank. This is not evidence of recoverable wins.',
                        'Marshal and Miner casualties do not establish avoidable strategic errors.',
                        'Replay physical ranks and counterfactual outcomes never enter policy inputs.'],
                primary_code_sources=['src/core/rules.c', 'src/core/pieces.c', 'src/core/ai.c'],
                current_source_sha256={name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                                       for name in ('src/core/rules.c', 'src/core/pieces.c', 'src/core/ai.c')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tournament', type=Path)
    parser.add_argument('--policy', default='teacher-context-v1-normal')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    text = json.dumps(analyze(args.tournament, args.policy), indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end='')
