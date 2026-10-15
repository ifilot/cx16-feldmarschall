"""Public-board helpers for the isolated Classic information experiments."""
from feldmarschall import COUNTS, LAKES, Position, battle

VALUES = (400, 200, 100, 75, 45, 30, 15, 25, 10, 100, 20, 1000)


def neighbors(square):
    row, col = divmod(square, 10)
    return [r*10+c for r, c in ((row-1, col), (row, col+1), (row+1, col), (row, col-1))
            if 0 <= r < 10 and 0 <= c < 10 and r*10+c not in LAKES]


def legal_moves(cells, army):
    """Geometric Classic moves; hypothetical repetition history is relaxed.

    Supplied root actions come from the native observer and retain repetition
    restrictions. Hidden enemies are occupied blockers, never inspected ranks.
    Callers simulating an enemy rank must install their explicit hypothesis.
    """
    position = Position()
    position.cells = [None if c >= 254 else
                      [int(bool(c & 16)), (c & 15) if bool(c & 16) == bool(army) or c & 32 else 12,
                       bool(c & 64), bool(c & 32)] for c in cells]
    return position.moves(army)


def rank_counts(cells, army, lost):
    """Enemy inventory still assigned to concealed pieces, from public counts."""
    counts = [n-dead for n, dead in zip(COUNTS, lost)]
    for cell in cells:
        if cell < 254 and bool(cell & 16) != bool(army) and cell & 32:
            counts[cell & 15] -= 1
    if min(counts) < 0: raise ValueError('inconsistent public inventory')
    return counts


def possible_ranks(cells, army, lost, histories, square):
    cell = cells[square]
    if cell >= 254 or bool(cell & 16) == bool(army): return {}
    if cell & 32: return {cell & 15: 1}
    history = histories.get(square)
    mask = history[-1] if history else 0xfff
    if cell & 64: mask &= 0x3ff  # Classic Bombs/Flag cannot move.
    return {rank: n for rank, n in enumerate(rank_counts(cells, army, lost))
            if n > 0 and mask & (1 << rank)}


def battle_gain(attacker, defender):
    result = battle(attacker, defender)
    return VALUES[defender] if result == 'attacker' else -VALUES[attacker] if result == 'defender' else VALUES[defender]-VALUES[attacker]
