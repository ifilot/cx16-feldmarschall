"""Army activation v1: unblock friendly routes to the central crossings.

This is an isolated, public-input hypothesis, not a claim that mobility alone
improves Stratego. Unlike Flag Corridor Recon it never infers enemy objectives,
rewards disclosures, or assigns an investigator. It evaluates the movement of
the whole friendly army after quiet moves, including units other than the actor.

The mobility motivation comes from McGrath et al., Acquisition of Chess Knowledge
in AlphaZero (PNAS 2022), https://pmc.ncbi.nlm.nih.gov/articles/PMC9704706/ .
The transition-potential construction is inspired by Ng, Harada and Russell
(ICML 1999), https://ai.stanford.edu/~ang/papers/shaping-icml99.pdf . This root-only,
capped heuristic is NOT covered by their full-return policy-invariance theorem.
Neither paper establishes this particular heuristic's strength in Stratego.
"""
from collections import deque

from feldmarschall import LAKES

VERSION = 'army-activation-v1'
SETTINGS = {
    'version': VERSION,
    'max_route': 8,
    'route_scale': 8.0,
    'local_mobility_weight': .125,
    'adjustment_cap': 24.0,
    'combat_adjustment': 0.0,
}
CROSSINGS = frozenset(row * 10 + col for row in (4, 5)
                      for col in (0, 1, 4, 5, 8, 9))


def _neighbors(sq):
    row, col = divmod(sq, 10)
    return tuple(r * 10 + c for r, c in
                 ((row-1, col), (row+1, col), (row, col-1), (row, col+1))
                 if 0 <= r < 10 and 0 <= c < 10 and r*10+c not in LAKES)


NEIGHBORS = tuple(_neighbors(sq) for sq in range(100))


def _own_mobile(cell, army):
    return cell < 254 and bool(cell & 16) == bool(army) and (cell & 15) < 10


def _weight(rank):
    # Combat officers can support an invasion, while Miners open Bomb screens.
    # These coarse roles are fixed before tournament results are observed.
    return 2.0 if rank <= 4 else 1.5 if rank == 7 else .5 if rank == 9 else 1.0


def potential(cells, army):
    """Own army's empty-square access to fixed, symmetric lake crossings.

    Every occupied square is a blocker, regardless of its hidden rank. Friendly
    mobile pieces can enter an adjacent reachable empty square. No route crosses
    a friendly piece, an enemy, or a lake. An actor already on a crossing has
    reached that crossing; its square does not become traversable by teammates.
    """
    distances = {sq: 0 for sq in CROSSINGS if cells[sq] == 255}
    queue = deque(distances)
    while queue:
        src = queue.popleft()
        if distances[src] >= SETTINGS['max_route']:
            continue
        for dst in NEIGHBORS[src]:
            if cells[dst] == 255 and dst not in distances:
                distances[dst] = distances[src] + 1
                queue.append(dst)
    value = 0.0
    for sq, cell in enumerate(cells):
        if not _own_mobile(cell, army):
            continue
        empty = [n for n in NEIGHBORS[sq] if cells[n] == 255]
        distance = (0 if sq in CROSSINGS else
                    min((distances[n]+1 for n in empty if n in distances), default=9))
        access = max(0, 9-distance) / 9.0
        value += _weight(cell & 15) * (access + SETTINGS['local_mobility_weight'] * len(empty))
    return value


def adjustments(cells, army, lost, histories, moves):
    """Bounded potential differences for legal quiet moves, with no truth input.

    ``lost`` and ``histories`` are accepted solely for the existing adapter's
    public-strategy contract. They are unused. Enemy rank bits, including known
    ranks, are never consulted. Combat continues to use the original teacher.
    """
    if len(cells) != 100 or army not in (0, 1):
        raise ValueError('expected 100 public cells and army 0 or 1')
    before = potential(cells, army)
    result = {}
    for move, score in moves.items():
        src, dst = move
        result[move] = 0.0
        if cells[dst] != 255 or score >= 30000 or not _own_mobile(cells[src], army):
            continue
        after = list(cells)
        after[dst], after[src] = after[src], 255
        delta = SETTINGS['route_scale'] * (potential(after, army) - before)
        cap = SETTINGS['adjustment_cap']
        result[move] = max(-cap, min(cap, delta))
    return result
