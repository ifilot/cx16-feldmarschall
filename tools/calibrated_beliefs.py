"""Public-history categorical likelihoods and count-consistent importance sampling.

This module never receives a referee position. Concealed rank nibbles are not
features. The caller supplies the same masked board/memory as Context Teacher.
"""
import json
import math
from pathlib import Path

from feldmarschall import COUNTS

FEATURE_SIZES = (20, 5, 5, 13, 13)
SCHEMA = 'public-history-categorical-beliefs-v1'


def bucket(value):
    return 0 if value == 0 else 1 if value == 1 else 2 if value < 4 else 3 if value < 8 else 4


def features(cells, army, square, history):
    """Origin geometry and observed movement; no hidden or own rank feature.

    Owner-normalized origin row (front=0), symmetric file (edge=0), move
    count, displacement, last approach to / retreat from a disclosed rank.
    """
    origin = history[2]
    row = 3-origin//10 if army == 0 else origin//10-6
    if not 0 <= row < 4:
        raise ValueError('invalid public piece origin')
    file = min(origin % 10, 9-origin % 10)
    distance = abs(origin//10-square//10)+abs(origin % 10-square % 10)
    return (row*5+file, bucket(history[5]), bucket(distance),
            min(history[8], 12), min(history[9], 12))


def unknowns(cells, lost, histories, army):
    remaining = [count-n for count, n in zip(COUNTS, lost)]
    slots = []
    for sq, cell in enumerate(cells):
        if cell >= 254 or bool(cell & 16) == bool(army):
            continue
        if cell & 32:
            remaining[cell & 15] -= 1
        else:
            slots.append(sq)
    if min(remaining) < 0 or sum(remaining) != len(slots):
        raise ValueError('inconsistent public inventory')
    if set(histories) != set(slots):
        raise ValueError('incomplete public histories')
    slots.sort(key=lambda sq: (histories[sq][-1].bit_count(), sq))
    return slots, remaining


class BeliefModel:
    def __init__(self, document):
        if document['schema'] != SCHEMA or document['feature_sizes'] != list(FEATURE_SIZES):
            raise ValueError('unsupported belief model')
        self.document = document
        self.temperature = float(document['temperature'])
        if not 0 <= self.temperature <= 1:
            raise ValueError('invalid belief temperature')
        self.tables = document['log_likelihood_ratios']
        if len(self.tables) != 2:
            raise ValueError('invalid belief groups')
        for group in self.tables:
            if len(group) != 12:
                raise ValueError('invalid rank table')
            for rank in group:
                if len(rank) != len(FEATURE_SIZES):
                    raise ValueError('invalid features')
                for values, size in zip(rank, FEATURE_SIZES):
                    if len(values) != size or not all(math.isfinite(v) for v in values):
                        raise ValueError('invalid likelihoods')

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text()))

    def likelihoods(self, cells, army, sq, history):
        values = features(cells, army, sq, history)
        table = self.tables[int(history[5] > 0)]
        # Bound soft evidence and retain support for bluffs and unseen behavior.
        return [math.exp(max(-2.0, min(2.0, self.temperature *
                    sum(rank[f][v] for f, v in enumerate(values))))) for rank in table]

    def prepare(self, cells, lost, histories, army):
        slots, remaining = unknowns(cells, lost, histories, army)
        likelihoods = {sq: self.likelihoods(cells, army, sq, histories[sq]) for sq in slots}
        return slots, remaining, likelihoods

    @staticmethod
    def draw(cells, histories, rng, slots, remaining, likelihoods):
        """Sequential proposal, corrected to product likelihood over assignments.

        q(rank_i|prefix) = remaining_count * likelihood / normalizer.
        Product of selected remaining counts is constant across complete
        assignments (factorial of each initial rank count). Thus target/q is
        proportional to product(normalizer / number of remaining slots).
        Rejected dead ends condition q on successful completion by a constant;
        the same correction remains valid for narrower public masks.
        """
        for _ in range(500):
            counts, world, log_weight = remaining[:], cells[:], 0.0
            for index, sq in enumerate(slots):
                mask = histories[sq][-1]
                weights = [n*likelihoods[sq][rank] if mask & (1 << rank) else 0.0
                           for rank, n in enumerate(counts)]
                total = sum(weights)
                if total <= 0:
                    break
                selected = rng.random()*total
                rank = 0
                while rank < 11 and selected >= weights[rank]:
                    selected -= weights[rank]
                    rank += 1
                counts[rank] -= 1
                world[sq] = (world[sq] & 240) | rank
                log_weight += math.log(total/(len(slots)-index))
            else:
                return world, log_weight
        raise ValueError('could not sample a consistent learned assignment')

    def sample_worlds(self, cells, lost, histories, rng, army, samples):
        if samples < 1:
            raise ValueError('positive sample count required')
        slots, remaining, likelihoods = self.prepare(cells, lost, histories, army)
        draws = [self.draw(cells, histories, rng, slots, remaining, likelihoods)
                 for _ in range(samples)]
        maximum = max(weight for _, weight in draws)
        return [(world, math.exp(weight-maximum)) for world, weight in draws]

    def marginals(self, cells, lost, histories, army, iterations=24):
        """Deterministic count-balanced approximation used ONLY for calibration.

        Iterative proportional fitting preserves hard zeros and balances the
        fractional rank table. These are not exact assignment marginals. Actual
        sampled marginals are separately evaluated after temperature selection.
        """
        slots, remaining, likelihoods = self.prepare(cells, lost, histories, army)
        rows = {sq: [remaining[r]*likelihoods[sq][r] if histories[sq][-1] & (1 << r) else 0.0
                     for r in range(12)] for sq in slots}
        for _ in range(iterations):
            for values in rows.values():
                total = sum(values)
                if not total:
                    raise ValueError('impossible public mask')
                for r in range(12): values[r] /= total
            totals = [sum(values[r] for values in rows.values()) for r in range(12)]
            for values in rows.values():
                for r in range(12):
                    values[r] *= remaining[r]/totals[r] if totals[r] else 0.0
        return {sq: [v/sum(values) for v in values] for sq, values in rows.items()}
