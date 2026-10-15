"""Stochastic root selection with a KL trust region around native preferences.

Only already-public native scores and masked-rollout corrections enter here.
The constraint has a scalar dual, solved separately at every decision:

  maximize E_p[score + correction] + T H(p)
  subject to KL(p || softmax(score/T)) <= budget.

For dual coefficient rho=lambda/T the solution is proportional to
exp(score/T + correction/(T*(1+rho))). rho=0 is the probability control.
This is a score-derived prior, not Ataraxos's learned move network.
"""
import json
import math
from pathlib import Path

SCHEMA = 'native-prior-kl-root-policy-v1'
MOVE_SEED_DOMAIN = 0x53545241


def log_softmax(values):
    largest = max(values)
    norm = math.log(sum(math.exp(value-largest) for value in values))
    return [value-largest-norm for value in values]


def divergence(log_p, log_q):
    return max(0.0, sum(math.exp(p)*(p-q) for p,q in zip(log_p,log_q)))


class RootPolicy:
    def __init__(self, document):
        if document.get('schema') != SCHEMA:
            raise ValueError('unsupported root policy')
        if document.get('mode') not in ('probability-control','kl-restrained'):
            raise ValueError('invalid root selection mode')
        self.mode = document['mode']
        self.temperature = float(document['temperature'])
        self.budget = float(document['kl_budget'])
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError('positive finite temperature required')
        if not math.isfinite(self.budget) or self.budget < 0:
            raise ValueError('nonnegative finite KL budget required')
        self.document = document

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text()))

    def distribution(self, scores, corrections):
        moves = sorted(scores)
        if not moves or set(scores) != set(corrections):
            raise ValueError('root move sets differ or are empty')
        if not all(math.isfinite(scores[m]) and math.isfinite(corrections[m]) for m in moves):
            raise ValueError('finite scores required')
        maximum = max(scores.values())
        native = [(scores[m]-maximum)/self.temperature for m in moves]
        prior = log_softmax(native)
        def policy(rho):
            return log_softmax([value+corrections[m]/(self.temperature*(1+rho))
                                for value,m in zip(native,moves)])
        control = policy(0.0)
        control_kl = divergence(control,prior)
        constrained = self.mode == 'kl-restrained' and control_kl > self.budget
        rho = 0.0
        if constrained and self.budget == 0:
            logs = prior
            rho = None  # exact infinite-penalty limit, represented without NaN/Inf
        elif constrained:
            lower, upper = 0.0, 1.0
            while divergence(policy(upper),prior) > self.budget:
                upper *= 2
                if upper > 2**50:
                    raise ValueError('KL dual did not converge')
            for _ in range(56):
                middle = (lower+upper)/2
                if divergence(policy(middle),prior) > self.budget:
                    lower = middle
                else:
                    upper = middle
            rho = upper
            logs = policy(rho)
        else:
            logs = control
        probabilities = [math.exp(value) for value in logs]
        prior_probabilities = [math.exp(value) for value in prior]
        kl = divergence(logs,prior)
        return dict(mode=self.mode,moves=moves,probabilities=probabilities,
                    prior_probabilities=prior_probabilities,kl=kl,control_kl=control_kl,
                    constrained=constrained,dual_ratio=rho,
                    entropy=-sum(p*lp for p,lp in zip(probabilities,logs)),
                    native_top_tier_mass=sum(p for m,p in zip(moves,probabilities) if scores[m]==maximum),
                    expected_corrected_score=sum(p*(scores[m]+corrections[m]) for m,p in zip(moves,probabilities)))

    @staticmethod
    def draw(distribution, rng):
        roll = rng.random()
        last = None
        for move, probability in zip(distribution['moves'],distribution['probabilities']):
            if probability:
                last = move
            roll -= probability
            if roll < 0:
                return tuple(move)
        if last is None:
            raise ValueError('empty root probability mass')
        return tuple(last)
