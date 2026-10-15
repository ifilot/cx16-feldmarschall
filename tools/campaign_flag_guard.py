"""Public Flag Interceptor v1: reserve a legal response before a known invasion.

The mission orders quiet moves categorically when a legal deployment restores
or retains all disclosed intruders' local two-turn interception coverage. Captures retain
exactly their original scores. Immediate wins and current confirmed one-turn
Flag attacks leave control with the existing tactical policy.

The proof is local: a single disclosed intruder moves twice while other enemy
pieces remain fixed. Coordinated moves by different enemies and concealed
intruders are outside it. No hidden enemy rank or setup is read.
"""
import math

from feldmarschall import FLAG, Position, battle

VERSION = 'public-flag-interceptor-v1'

def clone(position):
    copy = Position()
    copy.cells = [list(c) if c else None for c in position.cells]
    copy.shuttle = dict(position.shuttle)
    return copy


def public_position(position, side):
    copy = clone(position)
    for cell in copy.cells:
        if cell and cell[0] != side and not cell[3]:
            cell[1] = 12
    return copy


def coverage(position, side, intruder):
    """Exact local rank/geometry proof against one disclosed intruder.

    Enumerate its surviving moves which would enable Flag capture on its next
    turn. Test whether the defender can remove it in between. Other enemy units
    remain blockers; their future moves and threats are outside this local proof.
    """
    cell = position.cells[intruder]
    assert cell and cell[0] != side and cell[3] and cell[1] < 10
    flag = next(sq for sq, c in enumerate(position.cells) if c and c[0] == side and c[1] == FLAG)
    if cell[1] != 8 and abs(intruder//10-flag//10)+abs(intruder % 10-flag % 10) > 2:
        return dict(immediate=False, approaches=[], covered=True, guards=[])
    enemy = 1-side
    actions = [move for move in position.moves(enemy) if move[0] == intruder]
    if (intruder, flag) in actions:
        return dict(immediate=True, approaches=[], covered=False, guards=[])
    approaches = []
    for src, dst in actions:
        branch = clone(position)
        target = branch.cells[dst]
        if target is not None:
            if battle(cell[1], target[1]) != 'attacker':
                continue
            branch.fight(src, dst, cell[1], target[1])
        else:
            branch.move(src, dst)
        if (dst, flag) not in branch.moves(enemy):
            continue
        interceptors = [a for a, b in branch.moves(side) if b == dst
                        and battle(branch.cells[a][1], cell[1]) != 'defender']
        approaches.append(dict(move=[src, dst], guard_squares=interceptors))
    return dict(immediate=False, approaches=approaches,
                covered=all(r['guard_squares'] for r in approaches),
                guards=sorted({g for row in approaches for g in row['guard_squares']}))



def position_from_public(cells, army, shuttle):
    """Decode the exact Classic public board and native six-byte shuttle."""
    if len(cells) != 100 or army not in (0, 1):
        raise ValueError('expected 100 public cells and army 0 or 1')
    raw = bytes.fromhex(shuttle) if isinstance(shuttle, str) else bytes(shuttle)
    if len(raw) != 6:
        raise ValueError('expected six public shuttle bytes')
    position = Position()
    for sq, cell in enumerate(cells):
        if cell >= 254:
            continue
        owner = int(bool(cell & 16))
        rank = cell & 15 if owner == army or cell & 32 else 12
        if rank > 11 and (owner == army or cell & 32):
            raise ValueError('invalid own or disclosed rank')
        position.cells[sq] = [owner, rank, bool(cell & 64), bool(cell & 32)]
    for side in (0, 1):
        # Native layout is from[2], to[2], count[2], not two triplets.
        count = raw[4+side]
        if count and (raw[side] >= 100 or raw[2+side] >= 100):
            raise ValueError('invalid active shuttle squares')
        position.shuttle[side] = (raw[side], raw[2+side], count) if count else (None, None, 0)
    return position


def confirmed_danger(position, army, flag):
    """Return current legally executable, publicly certain Flag attacks."""
    enemy_moves = set(position.moves(1-army))
    return [src for src, dst in enemy_moves if dst == flag
            and (position.cells[src][3] and position.cells[src][1] < 10
                 or position.cells[src][2])]


def evaluate(cells, army, lost, histories, moves, shuttle):
    """Return (score adjustments, diagnostics) without mutating any input.

    Exact own ranks, disclosed enemy ranks, occupancy and public shuttle are the
    complete information contract. ``lost`` and ``histories`` are accepted for
    adapter compatibility but unused. No state survives between calls or games.
    """
    result = dict.fromkeys(moves, 0.0)
    report = dict(version=VERSION, active=False, reason='no-local-threat',
                  repair_moves=[], demoted_moves=0)
    if not moves:
        report['reason'] = 'no-moves'
        return result, report
    if any(not math.isfinite(score) for score in moves.values()):
        raise ValueError('nonfinite existing move score')
    if max(moves.values()) >= 30000:
        report['reason'] = 'immediate-win'
        return result, report
    position = position_from_public(cells, army, shuttle)
    legal = set(position.moves(army))
    if any(move not in legal for move in moves):
        raise ValueError('candidate is not a legal Classic move')
    if any(position.cells[dst] is not None and position.cells[dst][0] != army
           and position.cells[dst][3] and position.cells[dst][1] == FLAG for src, dst in moves):
        report['reason'] = 'immediate-win'
        return result, report
    flags = [sq for sq, c in enumerate(position.cells) if c and c[0] == army and c[1] == FLAG]
    if len(flags) != 1:
        report['reason'] = 'no-single-own-flag'
        return result, report
    flag = flags[0]
    danger = confirmed_danger(position, army, flag)
    if danger:
        report.update(reason='confirmed-immediate-flag-danger', immediate_attackers=sorted(danger))
        return result, report
    intruders = [sq for sq, c in enumerate(position.cells) if c and c[0] != army
                 and c[3] and c[1] < 10]
    # Non-Scouts farther than two steps cannot acquire a two-turn Flag route
    # through any quiet deployment. Retain potential blocked routes too: a
    # defender's move can open one while abandoning its own interception job.
    if not any(position.cells[sq][1] == 8
               or abs(sq//10-flag//10)+abs(sq % 10-flag % 10) <= 2 for sq in intruders):
        return result, report
    current = {sq: coverage(position, army, sq) for sq in intruders}
    endangered = [sq for sq, row in current.items() if not row['covered']]
    report['endangered_intruders'] = endangered
    repairs = []
    quiet = [move for move in moves if position.cells[move[1]] is None]
    for src, dst in quiet:
        after = clone(position)
        after.move(src, dst)
        if all(coverage(after, army, sq)['covered'] for sq in intruders):
            repairs.append((src, dst))
    if not repairs:
        report['reason'] = 'no-quiet-repair' if endangered else 'no-quiet-maintainer'
        return result, report
    floor = max(moves[move] for move in repairs)-1.0
    repair_set = set(repairs)
    for move in quiet:
        if move not in repair_set:
            result[move] = min(0.0, floor-moves[move])
    demoted = sum(value < 0 for value in result.values())
    report.update(active=bool(demoted),
                  reason=('quiet-interception-mission' if endangered else 'retain-interception-mission')
                         if demoted else 'all-quiet-moves-maintain-coverage',
                  repair_moves=repairs, demoted_moves=demoted)
    return result, report


def adjustments(cells, army, lost, histories, moves, shuttle):
    return evaluate(cells, army, lost, histories, moves, shuttle)[0]
