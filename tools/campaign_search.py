"""Cheap paired uncertainty control for the public Classic teacher.

Hypothesis: eight-world mean maximization overreacts to uncertain root overrides.
Keep the native move unless another move's paired corrected advantage exceeds
one jackknife standard error. All moves share each sampled army, so uncertainty
is computed on their difference, preserving common-world cancellation.

This is inspired by confidence-aware best-arm identification (Kaufmann and
Koolen, NeurIPS 2017), not an implementation of their algorithm or a finite-
sample confidence guarantee. Self-normalized importance weights, correlated
belief errors and the correction clip make that distinction important.

Inputs contain only native public scores and already permitted search results.
No additional rollouts, concealed ranks, or opponent setup are accepted.
"""
import math


def paired_selection(scores, credit, parent, samples, weights, standard_errors=1.0):
    """Return (selected, report) from [(action_values, reference), ...].

    Each action_values[move] is (future, immediate), exactly as emitted by the
    masked teacher. Weighted delete-one jackknife estimates uncertainty in the
    *final clipped score difference*, rather than separately estimating action
    variances. Repeated importance weights are treated as observations, not as
    extra independent samples. The multiplier is frozen before tournaments.
    """
    if not scores or parent not in scores or len(samples) != len(weights) or not samples:
        raise ValueError('nonempty matching samples and native parent required')
    if not math.isfinite(standard_errors) or standard_errors < 0:
        raise ValueError('finite nonnegative uncertainty multiplier required')
    if any(not math.isfinite(w) or w <= 0 for w in weights):
        raise ValueError('finite positive world weights required')
    moves = sorted(scores)
    if any(not math.isfinite(v) for v in scores.values()):
        raise ValueError('finite native scores required')
    total_weight = sum(weights)
    totals = dict.fromkeys(moves, 0.0)
    increments = []
    for (values, reference), weight in zip(samples, weights):
        if set(values) != set(scores) or not math.isfinite(reference):
            raise ValueError('sample must preserve root move set and finite reference')
        increments.append({})
        for move in moves:
            future, immediate = values[move]
            value = future - immediate - reference
            if not math.isfinite(value) or not math.isfinite(credit.get(move, 0)):
                raise ValueError('finite search values and credits required')
            increments[-1][move] = value
            totals[move] += weight * value

    def corrected(move, numerator, denominator):
        return scores[move] + max(-192, min(192, numerator / denominator + credit.get(move, 0)))

    means = {move: corrected(move, totals[move], total_weight) for move in moves}
    details = []
    lower = {}
    for move in moves:
        advantage = means[move] - means[parent]
        if len(samples) < 2:
            # An uncertainty estimate needs at least two independent draws.
            error = None if move != parent else 0.0
            lower[move] = 0.0 if move == parent else -math.inf
        else:
            deleted = []
            for index, weight in enumerate(weights):
                remaining = total_weight - weight
                if remaining <= 0:
                    raise ValueError('world weights lose all mass after deletion')
                own = corrected(move, totals[move] - weight * increments[index][move], remaining)
                native = corrected(parent, totals[parent] - weight * increments[index][parent], remaining)
                deleted.append(own - native)
            center = sum(deleted) / len(deleted)
            error = math.sqrt((len(deleted) - 1) / len(deleted) *
                              sum((value - center) ** 2 for value in deleted))
            lower[move] = advantage - standard_errors * error
        details.append(dict(move=move, mean_score=means[move], advantage=advantage,
                            jackknife_standard_error=error,
                            conservative_advantage=lower[move] if math.isfinite(lower[move]) else None))
    wins = [move for move in moves if scores[move] >= 30000]
    if wins:
        selected = parent if parent in wins else max(wins, key=lambda move: (means[move], -move[0], -move[1]))
    else:
        selected = max(moves, key=lambda move: (lower[move], move == parent, -move[0], -move[1]))
    greedy = max(moves, key=lambda move: (means[move], move == parent, -move[0], -move[1]))
    return selected, dict(mode='paired-jackknife-one-se-v1', standard_errors=standard_errors,
                          samples=len(samples), effective_samples=total_weight ** 2 / sum(w*w for w in weights),
                          greedy=greedy, selected=selected, forced_immediate_win=bool(wins), values=details)
