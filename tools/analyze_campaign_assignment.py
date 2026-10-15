"""Public native-goal contention and alternative task opportunity audit.

Reproduce the immutable Context Teacher's existing target utilities exactly.
This is retrospective allocation evidence, not proof that duplicate pursuit is
wrong: several hunters can trap a fleeing unit or provide useful support.
"""
import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import random
import shlex

from ai_registry import build_policy
from campaign_strategy import NEIGHBORS
from feldmarschall import COUNTS, Engine, GLYPHS, VALUES, battle, parse_square, square_name
from tournament_store import Tournament, replay


def trunc(n, d):
    return n//d if n >= 0 else -((-n)//d)


def utilities(cells, army, lost, old_goals, actors):
    enemy = lambda cell: cell < 254 and bool(cell&16) != bool(army)
    seen = Counter(cell&15 for cell in cells if enemy(cell) and cell&32)
    hidden = [max(0, count-dead-seen[rank]) for rank, (count, dead) in enumerate(zip(COUNTS, lost))]
    worth = list(VALUES)
    if hidden[10]+seen[10]:
        worth[7] = 40
    if hidden[0]+seen[0] == 0:
        worth[9] = 15
    flag = next(sq for sq, c in enumerate(cells) if c < 254 and bool(c&16) == bool(army) and c&15 == 11)
    edges = {}
    for actor in actors:
        a = cells[actor]&15
        distances = {actor: 0}
        queue = deque([actor])
        while queue:
            src = queue.popleft()
            for dst in NEIGHBORS[src]:
                if dst in distances or not (cells[dst] == 255 or enemy(cells[dst])):
                    continue
                distances[dst] = distances[src]+1
                if not enemy(cells[dst]):
                    queue.append(dst)
        gains = []
        for rank in range(12):
            outcome = battle(a, rank)
            gains.append(2000 if rank == 11 else worth[rank] if outcome == 'attacker'
                         else -worth[a] if outcome == 'defender' else 0)
        edges[actor] = {}
        for target, cell in enumerate(cells):
            if not enemy(cell) or target not in distances:
                continue
            if cell&32:
                gain = gains[cell&15]
            else:
                allowed = [rank for rank in range(12) if not cell&64 or rank < 10]
                denominator = sum(hidden[rank] for rank in allowed)
                gain = trunc(sum(hidden[rank]*gains[rank] for rank in allowed), denominator) if denominator else 0
            if gain < trunc(-worth[a], 2):
                continue
            utility = 24+trunc(gain, 4)
            if not cell&32 and a >= 6:
                utility += 12
            if abs(target//10-flag//10)+abs(target % 10-flag % 10) <= 2 and (not cell&32 or cell&15 < 10):
                utility += 40
            utility -= 3*distances[target]
            if old_goals[actor] == target:
                utility += 8
            edges[actor][target] = dict(utility=utility, distance=distances[target], gain=gain,
                                        target_known=bool(cell&32), target_rank=cell&15 if cell&32 else None)
    return edges


def audit(path, decisions_per_game=10):
    policy = 'teacher-context-v1-normal'
    program, receipt = build_policy(policy)
    observer = Engine(shlex.quote(str(program.parent/'observer')))
    with Tournament(path) as tournament:
        groups = defaultdict(list)
        for row in tournament.games():
            if row['result'] in ('error', 'draw') or row['plies'] < 20:
                continue
            result = 'win' if row['result'] == ('red' if row['red'] == policy else 'blue') else 'loss'
            groups[(row['family'], result)].append(row)
        games = [tournament.game(max(rows, key=lambda r: r['plies'])['id'])
                 for _, rows in sorted(groups.items())]
    rng = random.Random(2410311)
    counts = Counter()
    rows = []
    try:
        for game in games:
            side = int(game['blue'] == policy)
            states, _ = replay(game)
            eligible = list(range(side, min(game['plies'], 500), 2))
            selected = set(rng.sample(eligible, min(decisions_per_game, len(eligible))))
            for line in ('new '+('red', 'blue')[side], 'rules 0', 'difficulty normal',
                         'seed '+str(game['seed']), 'setup '+game[('red_setup', 'blue_setup')[side]]):
                observer.send(line)
            for ply, (src, dst) in enumerate(game['moves']):
                if ply > max(selected):
                    break
                if ply % 2 == side:
                    if ply in selected:
                        _, public, lost, _ = observer.ask('public', 'public').split()
                        cells = list(bytes.fromhex(public))
                        old = bytes.fromhex(observer.ask('strategy', 'strategy'))[100*side:100*(side+1)]
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
                    if ply in selected:
                        goals = list(bytes.fromhex(observer.ask('strategy', 'strategy'))[100*side:100*(side+1)])
                        goals[parent[0]] = goals[parent[1]]
                        actors = sorted({a for a, b in scores})
                        edges = utilities(cells, side, list(bytes.fromhex(lost)), old, actors)
                        for actor in actors:
                            best = max(edges[actor], key=lambda target: (edges[actor][target]['utility'], -target)) if edges[actor] else 255
                            assert best == goals[actor], (game['id'], ply, actor, best, goals[actor])
                        counts['native_goals_exactly_reproduced'] += len(actors)
                        target_actors = defaultdict(list)
                        for actor in actors:
                            if goals[actor] < 100:
                                target_actors[goals[actor]].append(actor)
                        duplicate = []
                        for target, sources in target_actors.items():
                            if len(sources) < 2:
                                continue
                            known = bool(cells[target]&32)
                            mobile = known and cells[target]&15 < 10
                            entries = []
                            for actor in sources:
                                alternative = [dict(target=t, **edge) for t, edge in edges[actor].items()
                                               if t not in target_actors and edge['target_known']
                                               and edge['target_rank'] < 10 and edge['gain'] >= 0]
                                alternative.sort(key=lambda e: (-e['utility'], e['target']))
                                entries.append(dict(actor=actor, own_rank=GLYPHS[cells[actor]&15],
                                                    assigned=edges[actor][target],
                                                    uncovered_known_alternatives=alternative[:3]))
                            duplicate.append(dict(target=target, target_known=known,
                                                  target_rank=GLYPHS[cells[target]&15] if known else None,
                                                  actors=entries))
                            counts['duplicate_target_groups'] += 1
                            counts['duplicate_known_mobile_groups'] += mobile
                            if mobile and any(e['uncovered_known_alternatives'] for e in entries):
                                counts['duplicate_known_mobile_with_uncovered_alternative'] += 1
                        if duplicate:
                            counts['roots_with_duplicate_targets'] += 1
                        if any(d['target_known'] and d['target_rank'] not in ('B', 'F')
                               and any(e['uncovered_known_alternatives'] for e in d['actors']) for d in duplicate):
                            counts['roots_with_known_mobile_duplication_and_alternative'] += 1
                        rows.append(dict(game=game['id'], family=game['family'], ply=ply, side=side,
                                         legal_actors=len(actors), public=public, lost=lost,
                                         duplicate_targets=duplicate))
                    observer.ask('played '+square_name(src)+' '+square_name(dst), 'playedok')
                a, d = states[ply][src], states[ply][dst]
                observer.send('moved '+square_name(src)+' '+square_name(dst) if d is None else
                              'battle '+square_name(src)+' '+square_name(dst)+' '+GLYPHS[a[1]]+' '+GLYPHS[d[1]])
    finally:
        observer.close()
    return dict(kind='public-native-goal-contention-audit', strength_evidence=False,
                tournament=str(path), tournament_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                policy=policy, frozen_native_receipt=receipt, games=len(games), roots=len(rows),
                selection='Longest honest win and loss per family; ten seeded own-decision prefixes before ply500.',
                counters=dict(counts), rows=rows,
                primary_source='https://ai.stanford.edu/~gerkey/research/final_papers/mrta-taxonomy.pdf',
                limits=['Duplicate pursuit can provide a useful capture net or support; this audit does not classify it as a mistake.',
                        'An uncovered reachable alternative may be tactically unsafe or strategically inferior.',
                        'Every native target utility is reproduced exactly before reporting allocation opportunities.'])


def strict_opportunities(path):
    """Filter saved unchanged-goal evidence using v1 capability constraints."""
    data = json.loads(path.read_text())
    rows = []
    for root in data['rows']:
        edges = []
        for group in root['duplicate_targets']:
            if not group['target_known'] or group['target_rank'] in ('B', 'F'):
                continue
            primary = max(group['actors'], key=lambda a: (a['assigned']['utility'], -a['actor']))
            for actor in group['actors']:
                if actor == primary or actor['own_rank'] in ('8', 'S') or actor['assigned']['utility'] <= 0:
                    continue
                for alt in actor['uncovered_known_alternatives']:
                    if alt['utility'] > 0 and battle(GLYPHS.index(actor['own_rank']), alt['target_rank']) == 'attacker':
                        edges.append(dict(actor=actor['actor'], old_target=group['target'],
                                          old_utility=actor['assigned']['utility'],
                                          primary_actor=primary['actor'], primary_utility=primary['assigned']['utility'],
                                          new_target=alt['target'], new_utility=alt['utility']))
        if edges:
            chosen = max(edges, key=lambda e: (e['new_utility'], -e['actor'], -e['new_target']))
            rows.append(dict(game=root['game'], ply=root['ply'], eligible_edges=edges, selected=chosen,
                             actor_utility_delta=chosen['new_utility']-chosen['old_utility'],
                             distinct_task_primary_utility_delta=chosen['new_utility']))
    return dict(kind='strict-v1-retrospective-opportunity-filter',
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sampled_roots=data['roots'],
                roots_with_reported_strict_opportunity=len(rows),
                games_with_reported_strict_opportunity=len({r['game'] for r in rows}),
                limitation='Audit stores top3 alternatives per actor. These are concrete positive strict-winning opportunities; missed lower-ranked eligible alternatives may exist. Does not establish improved move choice or game outcome. Native runtime replans against its own changed goal history.',
                rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tournament', type=Path, nargs='?')
    parser.add_argument('--strict-source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = strict_opportunities(args.strict_source) if args.strict_source else audit(args.tournament)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
