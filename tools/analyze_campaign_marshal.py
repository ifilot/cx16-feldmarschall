"""Public-prefix audit of honest Marshal deaths to Spy and Bomb.

Recorded death labels are offline public combat outcomes. The frozen observer
receives only its own setup and public movement/combat events. Its public rank
masks, approach history and native scores establish available information at
the preceding decision; no opponent setup enters that observer.
"""
import argparse
from collections import Counter
from collections import deque
import hashlib
import json
from pathlib import Path
import shlex

from ai_registry import build_policy
from feldmarschall import COUNTS, Engine, GLYPHS, Position, parse_square, square_name
from tournament_store import Tournament, replay
from campaign_strategy import NEIGHBORS


def adjacent(a, b):
    return abs(a//10-b//10) + abs(a % 10-b % 10) == 1


def audit(path, policy='teacher-context-v1-normal'):
    executable, receipt = build_policy(policy)
    observer = Engine(shlex.quote(str(executable.parent/'observer')))
    counts = Counter()
    rows = []
    try:
        with Tournament(path) as tournament:
            for entry in tournament.games():
                if entry['result'] == 'error':
                    continue
                game = tournament.game(entry['id'])
                if policy not in (game['red'], game['blue']):
                    continue
                side = int(game['blue'] == policy)
                states, _ = replay(game)
                targets = {}
                for ply, (src, dst) in enumerate(game['moves']):
                    a, d = states[ply][src], states[ply][dst]
                    if d is None:
                        continue
                    if a[0] != side and a[1] == 9 and d[1] == 0:
                        targets[ply-1] = ('Spy', ply, src, dst)
                    if a[0] == side and a[1] == 0 and d[1] == 10:
                        targets[ply] = ('Bomb', ply, src, dst)
                if not targets:
                    continue
                for line in ('new '+('red', 'blue')[side], 'rules 0', 'difficulty normal',
                             'seed '+str(game['seed']),
                             'setup '+game[('red_setup', 'blue_setup')[side]]):
                    observer.send(line)
                for ply, (src, dst) in enumerate(game['moves']):
                    if ply > max(targets):
                        break
                    if ply % 2 == side:
                        army, public, lost, shuttle = observer.ask('public', 'public').split()
                        cells = list(bytes.fromhex(public))
                        observer.send('ranked')
                        scores = {}
                        while True:
                            words = observer.read().split()
                            if words[0] == 'candidate':
                                scores[tuple(map(int, words[1:3]))] = int(words[3])
                            elif words[0] == 'move':
                                parent = tuple(map(parse_square, words[1:3]))
                                break
                            elif words[0] == 'error':
                                raise ValueError(words)
                        if ply in targets:
                            kind, deathply, killer_src, death_dst = targets[ply]
                            marshal = next(sq for sq, c in enumerate(cells) if c < 254
                                           and bool(c & 16) == bool(side) and c & 15 == 0)
                            histories = {sq: list(map(int, observer.ask('memory '+square_name(sq), 'history').split()))
                                         for sq, c in enumerate(cells) if c < 254
                                         and bool(c & 16) != bool(side) and not c & 32}
                            spy_possible = [sq for sq, h in histories.items() if h[-1] & (1 << 9)]
                            hidden = [max(0, count-dead-sum(c < 254 and bool(c&16) != bool(side)
                                             and c & 32 and c & 15 == rank for c in cells))
                                      for rank, (count, dead) in enumerate(zip(COUNTS, bytes.fromhex(lost)))]
                            hidden_mobile = sum(hidden[:10])
                            actual = (src, dst)
                            safe = []
                            for move, score in scores.items():
                                if move[0] != marshal or cells[move[1]] != 255:
                                    continue
                                if any(adjacent(move[1], sq) for sq in spy_possible):
                                    continue
                                # A disclosed enemy Marshal or Spy can also remove
                                # this Marshal; do not label such a move safe.
                                if any(c < 254 and bool(c & 16) != bool(side) and c & 32
                                       and c & 15 in (0, 9) and adjacent(move[1], sq)
                                       for sq, c in enumerate(cells)):
                                    continue
                                safe.append(dict(move=move, native_score=score))
                            bestsafe = max((r['native_score'] for r in safe), default=None)
                            strategic = bytes.fromhex(observer.ask('strategy', 'strategy'))
                            goal = strategic[100*side + (parent[1] if parent[0] == marshal else marshal)]
                            distances = {}
                            if goal < 100:
                                distances = {goal: 0}
                                queue = deque([goal])
                                while queue:
                                    node = queue.popleft()
                                    if node != goal and cells[node] < 254 and bool(cells[node]&16) != bool(side):
                                        continue
                                    for n in NEIGHBORS[node]:
                                        if n not in distances and (cells[n] == 255 or n == marshal
                                                or cells[n] < 254 and bool(cells[n]&16) != bool(side)):
                                            distances[n] = distances[node]+1
                                            queue.append(n)
                            preserving = [r for r in safe if src == marshal and dst in distances
                                          and r['move'][1] in distances
                                          and distances[r['move'][1]] <= distances[dst]]
                            row = dict(game=game['id'], family=game['family'], decision_ply=ply,
                                       death_ply=deathply, cause=kind, marshal_square=marshal,
                                       marshal_already_disclosed=bool(cells[marshal] & 32),
                                       enemy_marshal_publicly_dead=bytes.fromhex(lost)[0] > 0,
                                       enemy_spy_publicly_dead=bytes.fromhex(lost)[9] > 0,
                                       public_hidden_marshal_count=hidden[0],
                                       public_hidden_spy_count=hidden[9],
                                       public_hidden_mobile_count=hidden_mobile,
                                       native_single_moved_contact_risk=(400*(hidden[0]+hidden[9])//hidden_mobile if hidden_mobile else 0),
                                       recorded_move=actual, recorded_move_native_score=scores[actual],
                                       native_parent=parent, native_best_score=max(scores.values()),
                                       recorded_move_actor_is_marshal=src == marshal,
                                       recorded_move_is_capture=cells[dst] != 255,
                                       killer_public_cell=cells[killer_src] if kind == 'Spy' else cells[dst],
                                       killer_public_history=histories.get(killer_src if kind == 'Spy' else dst),
                                       spy_possible_squares=spy_possible, safe_quiet_marshal_moves=safe,
                                       native_marshal_goal=goal,
                                       safe_quiet_moves_preserving_goal_progress=preserving,
                                       best_safe_native_gap_from_recorded=(scores[actual]-bestsafe if bestsafe is not None else None),
                                       best_safe_native_gap_from_best=(max(scores.values())-bestsafe if bestsafe is not None else None))
                            rows.append(row)
                            counts[kind+'_deaths'] += 1
                            counts[kind+'_marshal_already_disclosed'] += row['marshal_already_disclosed']
                            counts[kind+'_with_safe_quiet_marshal_move'] += bool(safe)
                            counts[kind+'_with_safe_quiet_within32_of_native_best'] += bestsafe is not None and max(scores.values())-bestsafe <= 32
                            counts[kind+'_enemy_marshal_publicly_dead'] += row['enemy_marshal_publicly_dead']
                            counts[kind+'_with_safe_quiet_preserving_goal_progress'] += bool(preserving)
                            if kind == 'Spy':
                                h = row['killer_public_history']
                                post_marshal = dst if src == marshal else marshal
                                row['post_move_spy_candidate_contacts'] = [sq for sq in spy_possible
                                    if sq != dst and adjacent(post_marshal, sq)]
                                counts['Spy_killer_publicly_moved'] += bool(cells[killer_src] & 64)
                                counts['Spy_killer_approached_disclosed_marshal'] += h is not None and h[-3] == 0
                                counts['Spy_killer_candidate_mask_allows_Spy'] += h is not None and bool(h[-1] & (1 << 9))
                                counts['Spy_after_own_marshal_move'] += src == marshal
                                counts['Spy_after_quiet_own_move'] += cells[dst] == 255
                            else:
                                counts['Bomb_with_other_same_target_attacker'] += any(m[0] != marshal and m[1] == dst for m in scores)
                        observer.ask('played '+square_name(src)+' '+square_name(dst), 'playedok')
                    a, d = states[ply][src], states[ply][dst]
                    event = ('moved '+square_name(src)+' '+square_name(dst) if d is None else
                             'battle '+square_name(src)+' '+square_name(dst)+' '+GLYPHS[a[1]]+' '+GLYPHS[d[1]])
                    observer.send(event)
    finally:
        observer.close()
    return dict(kind='marshal-public-prefix-mechanism-audit', strength_evidence=False,
                tournament=str(path), tournament_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                policy=policy, frozen_native_receipt=receipt, counters=dict(counts), rows=rows,
                public_input_contract='Frozen observer receives only own setup and public moved/battle events.',
                source_observations=[
                    'ai.c survey computes risk[Marshal]=400*(hiddenMarshal+hiddenSpy)/hidden_mobile, including a full-own-loss term for hidden equal-rank exchanges.',
                    'ai.c threat takes the maximum concealed-contact risk; unmoved-contact risk is halved. Known equal-Marshal exchanges use worthdifference0 instead.',
                    'teacher_rollout.c policy_move calls ai_mask for the simulated acting side; initial_view masks every undisclosed enemy rank. Continuations receive no extra true opponent knowledge.',
                    'History approach-rank0 evidence occurs in only2 of23Spy deaths; an approach-to-disclosed-Marshal detector alone has low coverage.',
                    'The enemyMarshal was not publicly dead in any48selected deaths. A safety condition requiring an undefeated Marshal has zero coverage here.'],
                proposed_next_hypothesis='Consider only quiet Marshal route alternatives: prefer a route without adjacent possibleSpy when it makes at least equal progress toward the existing public goal. Evidence covers5of23historicalSpy deaths before any added disclosed-only restriction; no implementation or strength result is claimed.',
                limits=['Safe here means no immediate known Marshal/Spy or concealed Spy-candidate adjacency; it does not establish tactical safety or equivalent strategic control.',
                        'Native scores are forced-prefix mechanism evidence, not the original Context Teacher corrected values.',
                        'The selected death prefixes are development evidence and cannot serve as fresh strength validation.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tournament', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    text = json.dumps(audit(args.tournament), indent=2)+'\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end='')
