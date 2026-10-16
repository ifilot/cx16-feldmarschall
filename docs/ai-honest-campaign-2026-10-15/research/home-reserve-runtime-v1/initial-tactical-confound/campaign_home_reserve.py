"""Public home-interceptor deadline reserve, Classic research candidate v1.

Keep a modeled response schedule to one disclosed Miner's corner-Flag invasion.
Other pieces remain fixed in that model. Hidden attackers, offensive races and
successive invasions are outside its guarantee. This is a host-side filter, not
an implementation measured or fitted for the CX16 target.
"""
from collections import deque
import math

from campaign_flag_guard import clone, confirmed_danger, position_from_public
from feldmarschall import FLAG, LAKES, battle

VERSION = 'public-home-reserve-v1'


def neighbors(square):
    row, column = divmod(square, 10)
    return [sq for sq in (square-10 if row else -1,
                         square+10 if row<9 else -1,
                         square-1 if column else -1,
                         square+1 if column<9 else -1)
            if sq >= 0 and sq not in LAKES]


def miner_distance(position, army, source, flag):
    """Fastest surviving single-Miner route with all other pieces fixed."""
    queue = deque([(source, 0)])
    visited = {source}
    previous_from, previous_to, count = position.shuttle[1-army]
    while queue:
        square, distance = queue.popleft()
        if square == flag:
            return distance
        for target in neighbors(square):
            if target in visited:
                continue
            if distance == 0 and count >= 5 and square == previous_to and target == previous_from:
                continue
            cell = position.cells[target]
            if cell and (cell[0] != army or battle(7, cell[1]) != 'attacker'):
                continue
            visited.add(target)
            queue.append((target, distance+1))
    return None


def routed_miners(position, army, flag):
    return {square: distance for square, cell in enumerate(position.cells)
            if cell and cell[0] != army and cell[3] and cell[1] == 7
            and (distance := miner_distance(position, army, square, flag)) is not None}


def lethal_squares(position, army, rank):
    """Known legal attacks which kill/exchange this rank, with current shuttle."""
    return {target for source, target in position.moves(1-army)
            if position.cells[source][3] and position.cells[source][1] < 10
            and battle(position.cells[source][1], rank) != 'defender'}


def guard_arrival(position, army, post):
    """Shortest quiet guard path avoiding currently disclosed lethal contacts.

    Remove that guard from its source for threat geometry, so its current body
    cannot conceal a Scout ray over a later route square. No future movement of
    other units is modeled. Each path is simple, so only its first edge can
    violate the current public shuttle restriction.
    """
    occupant = position.cells[post]
    if occupant and (occupant[0] != army or occupant[1] > 7):
        return None
    last_from, last_to, count = position.shuttle[army]
    choices = []
    for source, cell in enumerate(position.cells):
        if not cell or cell[0] != army or cell[1] > 7:
            continue
        if occupant and source != post:
            continue
        empty_source = clone(position)
        empty_source.cells[source] = None
        unsafe = lethal_squares(empty_source, army, cell[1])
        if post in unsafe:
            continue
        if source == post:
            choices.append(dict(guard=source, rank=cell[1], distance=0, path=[source]))
            continue
        queue = deque([(source, [source])])
        visited = {source}
        while queue:
            square, path = queue.popleft()
            if square == post:
                choices.append(dict(guard=source, rank=cell[1], distance=len(path)-1, path=path))
                break
            for target in neighbors(square):
                if target in visited or target in unsafe or position.cells[target] is not None:
                    continue
                if len(path) == 1 and count >= 5 and source == last_to and target == last_from:
                    continue
                visited.add(target)
                queue.append((target, path+[target]))
    return min(choices, key=lambda row: (row['distance'], row['guard'])) if choices else None


def readiness(position, army, flag, post):
    routes = routed_miners(position, army, flag)
    if not routes:
        return dict(feasible=True, reason='no-invasion-route', routes={}, guard=None)
    if len(routes) != 1:
        return dict(feasible=False, reason='multiple-routed-miners', routes=routes, guard=None)
    guard = guard_arrival(position, army, post)
    time = next(iter(routes.values()))
    feasible = bool(guard and guard['distance']+2 <= time)
    return dict(feasible=feasible, reason='deadline-preserved' if feasible else 'deadline-missed',
                routes=routes, guard=guard, enemy_time=time)


def evaluate(cells, army, lost, histories, moves, shuttle):
    """Pure public-input action adjustments; captures retain their exact scores.

    ``moves`` maps native legal moves to native scores. No rank hidden in an
    enemy lower nibble is inspected. ``lost``/``histories`` are unused adapter
    fields; no state or randomness survives a call.
    """
    adjustments = dict.fromkeys(moves, 0.0)
    report = dict(version=VERSION, active=False, reason='no-moves',
                  repair_moves=[], demoted_moves=0)
    if not moves:
        return adjustments, report
    if any(not math.isfinite(score) for score in moves.values()):
        raise ValueError('nonfinite existing move score')
    if max(moves.values()) >= 30000:
        report['reason'] = 'immediate-win'
        return adjustments, report
    position = position_from_public(cells, army, shuttle)
    legal = set(position.moves(army))
    if any(move not in legal for move in moves):
        raise ValueError('candidate is not a legal Classic move')
    if any(position.cells[dst] and position.cells[dst][0] != army
           and position.cells[dst][3] and position.cells[dst][1] == FLAG for _, dst in moves):
        report['reason'] = 'immediate-win'
        return adjustments, report
    flags = [square for square, cell in enumerate(position.cells)
             if cell and cell[:2] == [army, FLAG]]
    if len(flags) != 1 or flags[0] not in (0, 9, 90, 99):
        report['reason'] = 'no-corner-flag'
        return adjustments, report
    flag = flags[0]
    if confirmed_danger(position, army, flag):
        report['reason'] = 'confirmed-immediate-flag-danger'
        return adjustments, report
    if any(not position.cells[square] or position.cells[square][:2] != [army, 10]
           for square in neighbors(flag)):
        report['reason'] = 'no-intact-two-bomb-screen'
        return adjustments, report
    routes = routed_miners(position, army, flag)
    if len(routes) != 1:
        report['reason'] = 'no-invasion-route' if not routes else 'multiple-routed-miners'
        return adjustments, report
    if next(iter(routes.values())) <= 2:
        report['reason'] = 'existing-local-defense'
        return adjustments, report
    post = flag + (10 if flag < 10 else -10) + (1 if flag % 10 == 0 else -1)
    repairs = []
    report.update(flag=flag, post=post, current_routes=routes, candidates={})
    quiet = [move for move in moves if position.cells[move[1]] is None]
    for source, target in quiet:
        after = clone(position)
        after.move(source, target)
        if target in lethal_squares(after, army, after.cells[target][1]):
            row = dict(feasible=False, reason='disclosed-actor-loss')
        else:
            row = readiness(after, army, flag, post)
        report['candidates'][f'{source}:{target}'] = row
        if row['feasible']:
            repairs.append((source, target))
    report['repair_moves'] = repairs
    if not repairs:
        report['reason'] = 'no-safe-quiet-schedule'
        return adjustments, report
    floor = max(moves[move] for move in repairs)-1.0
    preferred = set(repairs)
    for move in quiet:
        if move not in preferred:
            adjustments[move] = min(0.0, floor-moves[move])
    demoted = sum(value < 0 for value in adjustments.values())
    report.update(active=bool(demoted), demoted_moves=demoted,
                  reason='preserve-home-response-deadline' if demoted else 'native-order-preserves-deadline')
    return adjustments, report
