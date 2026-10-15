"""Count-consistent public-world sampling with randomized Latin hypercubes.

McKay, Beckman and Conover (1979), Technometrics 21(2), 239--245:
https://www.stat.cmu.edu/technometrics/70-79/VOL-21-02/v2102239.pdf

Hypothesis: spread a small world's batch across rank uncertainty instead of
spending additional native rollouts. Each fixed world's random coordinates are
still independent uniform values. Only dependence BETWEEN worlds changes.
There is no general guarantee of lower variance for nonlinear game search or
self-normalized importance estimates; tournaments must establish usefulness.
"""
import math

from train_ai_student import sample_world


class _LatinBatch:
    """Lazy independent Latin-hypercube columns, one uniform stratum per row."""
    def __init__(self, rng, samples):
        self.rng = rng
        self.samples = samples
        self.columns = []

    def coordinate(self, row, column):
        while len(self.columns) <= column:
            strata = list(range(self.samples))
            self.rng.shuffle(strata)
            self.columns.append([(s + self.rng.random()) / self.samples for s in strata])
        return self.columns[column][row]

    def row(self, index):
        return _LatinRow(self, index)


class _LatinRow:
    def __init__(self, batch, index):
        self.batch, self.index, self.column = batch, index, 0

    def random(self):
        value = self.batch.coordinate(self.index, self.column)
        self.column += 1
        return value

    def choice(self, values):
        if not values:
            raise IndexError('cannot choose from an empty sequence')
        return values[min(int(self.random()*len(values)), len(values)-1)]


class StratifiedSampler:
    """Drop-in sample_worlds provider; optional frozen learned belief model.

    Without a learned model the existing sample_world proposal and behavioral
    weights are preserved. With one, its sequential likelihood proposal and
    exact importance correction are preserved. Rejection retries simply use
    later independent columns. No referee position or opponent setup is read.
    """
    def __init__(self, belief_model=None):
        self.belief_model = belief_model

    def sample_worlds(self, cells, lost, histories, rng, army, samples):
        if not isinstance(samples, int) or isinstance(samples, bool) or samples < 1:
            raise ValueError('positive integer sample count required')
        batch = _LatinBatch(rng, samples)
        if self.belief_model is None:
            return [sample_world(cells, lost, histories, batch.row(i), army)
                    for i in range(samples)]
        slots, remaining, likelihoods = self.belief_model.prepare(cells, lost, histories, army)
        draws = [self.belief_model.draw(cells, histories, batch.row(i), slots, remaining, likelihoods)
                 for i in range(samples)]
        maximum = max(weight for _, weight in draws)
        return [(world, math.exp(weight-maximum)) for world, weight in draws]


class UniformSampler:
    """Ablate behavioral likelihoods, preserving the original IID proposals.

    This deliberately changes the modeled posterior: approach/retreat events
    no longer multiply assignment probabilities. Counts and public masks still
    constrain every world. For the actual all-rank/moved masks this proposal is
    uniform over compatible assignments. With future arbitrary narrower masks,
    sequential proposal/rejection need not be uniform; no such claim is made.
    """
    def sample_worlds(self, cells, lost, histories, rng, army, samples):
        if not isinstance(samples,int) or isinstance(samples,bool) or samples < 1:
            raise ValueError('positive integer sample count required')
        return [(sample_world(cells,lost,histories,rng,army)[0],1.0) for _ in range(samples)]
