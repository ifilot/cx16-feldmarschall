"""Fair Classic probe valuation with a conservative one-response continuation.

Frozen v1 design: all concealed-target attacks by ranks 5, 6 and 8 pay their
expected sacrificed material. Only the four highest baseline-scored probes can
earn information credit. The credit compares choosing a safe continuation after
disclosure with an optimistic blind attack by the best available friendly rank.
Every plausible enemy response must leave some beneficiary useful; an escape,
beneficiary removal, and possible recapture are explicitly considered. No private board,
setup, model fit, or layout label enters this module.

This is a deliberately conservative tactical approximation, not a minimax
proof. Enemy hypothetical movement ignores repetition restrictions, enlarging
the response set. The credited friendly continuation is an adjacent attack by
a different non-Scout, which cannot reverse the sacrificed actor's last move.
Enemy rank possibilities are marginal public inventory beliefs, not a jointly
consistent assignment. Possible recaptures conservatively cost the whole
beneficiary even if the recapturer would exchange.
Expected sacrifice cost is an extra opportunity budget atop the teacher score,
not an unbiased material evaluation: information must justify spending a unit.
"""

from feldmarschall import BOMB, FLAG, LAKES, SCOUT, battle
from info_common import VALUES, battle_gain, neighbors, possible_ranks

MAX_PROBES = 4
MAX_CREDIT = 64.0
PROBERS = (5, 6, 8)  # Lieutenant, Sergeant and Scout; preserve specialised Miners.


def _occupied(cell):
    return cell < 254


def _side(cell):
    return int(bool(cell & 16))


def _moves_from(cells, source, rank, army):
    """Geometrical moves with lakes, blockers and Scout rays; no shuttle filter."""
    if rank in (BOMB, FLAG):
        return
    x, y = source % 10, source // 10
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nx, ny = x + dx, y + dy
        while 0 <= nx < 10 and 0 <= ny < 10:
            target = ny * 10 + nx
            if target in LAKES:
                break
            cell = cells[target]
            if _occupied(cell):
                if _side(cell) != army:
                    yield target
                break
            yield target
            if rank != SCOUT:
                break
            nx, ny = nx + dx, ny + dy


def _safe_gain(cells, army, target, rank, beneficiary, possibilities):
    if target is None:
        # An opponent who removes the revealed target by a suicidal attack
        # has already conceded this material, irrespective of our choice.
        return VALUES[rank]
    cell = cells[beneficiary]
    if not _occupied(cell) or _side(cell) != army or target not in neighbors(beneficiary):
        return 0.0
    own_rank = cell & 15
    outcome = battle(own_rank, rank)
    if outcome == 'defender':
        return -VALUES[own_rank]
    if outcome == 'both':
        return VALUES[rank] - VALUES[own_rank]
    after = cells[:]
    after[beneficiary], after[target] = 255, cell
    # A positive capture must survive every publicly plausible immediate
    # recapture; this deliberately gives no credit for uncertain safety.
    for square, options in possibilities.items():
        if square == target or not _occupied(after[square]) or _side(after[square]) == army:
            continue
        distance = abs(square % 10 - target % 10) + abs(square // 10 - target // 10)
        aligned = square % 10 == target % 10 or square // 10 == target // 10
        if distance != 1 and (not aligned or SCOUT not in options):
            continue
        for enemy_rank in options:
            if distance != 1 and enemy_rank != SCOUT:
                continue
            if battle(enemy_rank, own_rank) != 'defender' and target in _moves_from(after, square, enemy_rank, 1 - army):
                return VALUES[rank] - VALUES[own_rank]
    return float(VALUES[rank])


def _responses(cells, army, target, target_rank, possibilities):
    """Yield occupancy and public identity possibilities after one enemy move."""
    # Including pass is conservative and covers responses elsewhere that have
    # no local effect, as well as a position with no legal enemy move.
    yield cells, target, possibilities, 0.0
    for source, options in possibilities.items():
        for rank in options:
            for destination in _moves_from(cells, source, rank, 1 - army):
                after = cells[:]
                defender = after[destination]
                outcome = battle(rank, defender & 15) if _occupied(defender) else 'attacker'
                after[source] = 255
                after[destination] = ((rank | (16 if 1 - army else 0) | 32)
                                      if outcome == 'attacker' else
                                      255 if outcome == 'both' else defender)
                updated = dict(possibilities)
                del updated[source]
                if outcome == 'attacker':
                    updated[destination] = {rank: 1}
                new_target = target
                if source == target:
                    new_target = destination if outcome == 'attacker' else None
                terminal = (VALUES[target_rank] - (VALUES[defender & 15] if outcome == 'both' else 0)
                            if source == target and new_target is None else 0.0)
                if _occupied(defender) and defender & 15 == FLAG:
                    new_target, terminal = None, 0.0  # Game ended: no next own turn.
                yield after, new_target, updated, terminal


def _information(cells, army, source, target, probabilities, possibilities):
    vicinity = set(neighbors(target))
    for sq in tuple(vicinity):
        vicinity.update(neighbors(sq))
    beneficiaries = [sq for sq in sorted(vicinity)
                     if sq != source and _occupied(cells[sq]) and _side(cells[sq]) == army
                     and (cells[sq] & 15) not in (BOMB, FLAG, SCOUT)]
    if not beneficiaries:
        return 0.0
    conditional = 0.0
    # The blind comparator may choose its best rank and ignores geometry and
    # recapture entirely. This optimistic bound prevents positional flexibility
    # between different beneficiaries from masquerading as information value.
    blind = max(0.0, *(sum(p * battle_gain(cells[sq] & 15, rank)
                         for rank, p in probabilities.items()
                         if battle(cells[source] & 15, rank) == 'defender')
                       for sq in beneficiaries))
    for rank, probability in probabilities.items():
        if battle(cells[source] & 15, rank) != 'defender':
            continue  # No surviving target to investigate.
        after = cells[:]
        after[source] = 255
        after[target] = rank | (16 if 1 - army else 0) | 32
        options = dict(possibilities)
        options[target] = {rank: 1}
        worst = float('inf')
        for response, location, response_options, terminal in _responses(after, army, target, rank, options):
            useful = (max(0.0, *(_safe_gain(response, army, location, rank, sq, response_options)
                                 for sq in beneficiaries)) if location is not None else terminal)
            worst = min(worst, useful)
            if worst <= 0:
                break
        conditional += probability * max(0.0, worst)
    return max(0.0, conditional - blind)


def adjustments(cells, army, lost, histories, moves):
    """Return material-scale corrections for referee-legal root candidates.

    Public C board encoding is required: concealed enemies have rank UNKNOWN
    (12). Reject a supposedly concealed true rank instead of silently using it.
    """
    possibilities = {}
    for sq, cell in enumerate(cells):
        if _occupied(cell) and _side(cell) != army:
            if not cell & 32 and cell & 15 != 12:
                raise ValueError('concealed enemy rank must be masked')
            possibilities[sq] = possible_ranks(cells, army, lost, histories, sq)
    probes = []
    result = {}
    for move in moves:
        source, target = move
        actor, defender = cells[source], cells[target]
        if (actor & 15) not in PROBERS or not _occupied(defender) or _side(defender) == army or defender & 32:
            continue
        options = possibilities[target]
        total = sum(options.values())
        if not total:
            continue
        probabilities = {rank: weight / total for rank, weight in options.items()}
        loss = VALUES[actor & 15] * sum(p for rank, p in probabilities.items()
                                      if battle(actor & 15, rank) != 'attacker')
        result[move] = -loss
        probes.append((move, probabilities))
    probes.sort(key=lambda item: (-moves[item[0]], item[0]))
    for (source, target), probabilities in probes[:MAX_PROBES]:
        credit = _information(cells, army, source, target, probabilities, possibilities)
        result[source, target] += min(MAX_CREDIT, credit)
    return result
