"""Flag Corridor Recon v1: send expendable pieces to useful concealed screens.

This policy consumes only the masked public board and the observer's candidate
rank masks. Its fixed priors are hypotheses, not hidden deployment knowledge.
It does not force a follow-up capture: the ordinary teacher still values combat.
"""
from collections import deque

from feldmarschall import COUNTS, LAKES, battle

VERSION = 'flag-corridor-recon-v1'
EXPENDABLE = {8: 1.0, 6: .65, 5: .4}


def _neighbors(sq):
    row, col = divmod(sq, 10)
    return [r * 10 + c for r, c in ((row-1,col),(row+1,col),(row,col-1),(row,col+1))
            if 0 <= r < 10 and 0 <= c < 10 and r*10+c not in LAKES]


def _enemy(cell, army):
    return cell < 254 and bool(cell & 16) != bool(army)


def _distances(cells, start, terminals=()):
    """Walkable cardinal routes, with enemy objectives terminal only.

    Friendly pieces, lakes and other enemies are real blockers. A terminal is
    never expanded; we cannot pretend a discovered enemy will disappear.
    """
    terminals = set(terminals)
    distances = {start: 0}
    queue = deque([start])
    while queue:
        src = queue.popleft()
        for dst in _neighbors(src):
            if dst in distances or (cells[dst] != 255 and dst not in terminals):
                continue
            distances[dst] = distances[src] + 1
            if dst not in terminals:
                queue.append(dst)
    return distances


def adjustments(cells, army, lost, histories, moves):
    """Return bounded native-material adjustments for existing legal moves.

    Select a specific unknown Flag candidate or its unknown adjacent screen.
    Both a weak investigator and a useful surviving beneficiary must have
    unobstructed routes to it. This broader mission avoids depending on the
    enemy offering a same-square tactical follow-up after a sacrificial probe.
    """
    result = {move: 0.0 for move in moves}
    remaining = [max(0, count - dead) for count, dead in zip(COUNTS, lost)]
    for cell in cells:
        if _enemy(cell, army) and cell & 32:
            remaining[cell & 15] = max(0, remaining[cell & 15] - 1)
    possible = {}
    for sq, cell in enumerate(cells):
        if not _enemy(cell, army) or cell & 32:
            continue
        # Low rank bits of a concealed cell are never consulted, even if the
        # caller accidentally carries physical ranks there.
        mask = histories[sq][-1] if sq in histories else (1 << 12) - 1
        if cell & 64:
            mask &= (1 << 10) - 1
        possible[sq] = [rank for rank, count in enumerate(remaining)
                        if count and mask & (1 << rank)]
    flags = {}
    for sq, cell in enumerate(cells):
        known_flag = _enemy(cell, army) and cell & 32 and cell & 15 == 11
        if known_flag or 11 in possible.get(sq, ()):
            # Every unmoved region remains possible. Back rows and public Bomb
            # screens receive weak priors; no enemy setup template is read.
            enemy_depth = sq // 10 if army == 0 else 9 - sq // 10
            prior = 1.0 + .25 * max(0, 3 - enemy_depth)
            prior += .5 * sum(_enemy(cells[n], army) and cells[n] & 32
                              and cells[n] & 15 == 10 for n in _neighbors(sq))
            flags[sq] = 4.0 if known_flag else prior
    if not flags:
        return result
    targets = {}
    for sq, ranks in possible.items():
        if len(ranks) < 2:
            continue  # A logically deduced rank is already information.
        mass = flags.get(sq, 0) + sum(flags.get(n, 0) for n in _neighbors(sq))
        if mass:
            targets[sq] = mass
    if not targets:
        return result
    # A route to an approach square must exist for an own Miner or combat unit.
    # Unknown enemy screens cannot be traversed by the prospective beneficiary.
    support = {}
    for sq, cell in enumerate(cells):
        if cell < 254 and not _enemy(cell, army) and ((cell & 15) <= 4 or cell & 15 == 7):
            distances = _distances(cells, sq, targets)
            for target in targets:
                if target in distances and distances[target] <= 6:
                    support[target] = min(support.get(target, 100), distances[target])
    targets = {sq: mass for sq, mass in targets.items() if sq in support}
    if not targets:
        return result
    peak = max(targets.values())
    by_actor = {}
    for move in moves:
        by_actor.setdefault(move[0], []).append(move)
    for src, candidates in by_actor.items():
        rank = cells[src] & 15
        if rank not in EXPENDABLE:
            continue
        distances = _distances(cells, src, targets)
        accessible = [t for t in targets if t in distances and distances[t] <= 8]
        if not accessible:
            continue
        target = max(accessible, key=lambda t: (targets[t] / (2 + distances[t]), -t))
        strength = EXPENDABLE[rank] * targets[target] / peak
        after = list(cells)
        after[src] = 255
        approach = _distances(after, target)
        for move in candidates:
            _, dst = move
            if dst == target:
                bonus = 16.0 * strength
            elif cells[dst] == 255:
                # Recompute with the actor's origin vacated. All other blockers
                # remain, and the enemy terminal cannot serve as a shortcut.
                future = approach.get(dst)
                if future is None:
                    continue
                progress = max(-1, min(1, distances[target] - future))
                bonus = 8.0 * strength * progress
            else:
                continue  # No discovery credit for a known/disconnected fight.
            # A known adjacent enemy can defeat a quiet investigator before the
            # probe. Do not reward knowingly throwing away its information job.
            if cells[dst] == 255 and any(
                    _enemy(cells[n], army) and cells[n] & 32 and cells[n] & 15 < 10
                    and battle(cells[n] & 15, rank) != 'defender'
                    for n in _neighbors(dst)):
                bonus = min(0.0, bonus) - 8.0 * strength
            result[move] = bonus
    return result
