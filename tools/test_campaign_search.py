"""Paired uncertainty reduction: common-world noise, weighting and clipping."""
import json
import math
import unittest

from campaign_search import paired_selection

PARENT, OTHER = (60, 50), (61, 51)


def evaluate(differences, parent_values=None, scores=None, weights=None, multiplier=1):
    parent_values = parent_values or [0] * len(differences)
    samples = [({PARENT: (p, 0), OTHER: (p + difference, 0)}, 0)
               for p, difference in zip(parent_values, differences)]
    return paired_selection(scores or {PARENT: 0, OTHER: 0}, {}, PARENT,
                            samples, weights or [1] * len(samples), multiplier)


class PairedSelection(unittest.TestCase):
    def test_consistent_advantage_survives_large_common_world_noise(self):
        selected, report = evaluate([2] * 8, [-80, 80] * 4)
        self.assertEqual(selected, OTHER)
        other = report['values'][1]
        self.assertEqual(other['advantage'], 2)
        self.assertEqual(other['jackknife_standard_error'], 0)

    def test_single_outlier_override_rejected(self):
        selected, report = evaluate([-1] * 7 + [23])
        self.assertEqual(report['greedy'], OTHER)
        self.assertEqual(selected, PARENT)
        self.assertAlmostEqual(report['values'][1]['jackknife_standard_error'], 3)

    def test_zero_multiplier_exactly_recovers_greedy(self):
        selected, report = evaluate([-1] * 7 + [23], multiplier=0)
        self.assertEqual(selected, report['greedy'])

    def test_weight_scaling_does_not_change_result_or_uncertainty(self):
        first = evaluate([2, 5, -1, 7], weights=[1, 2, 3, 4])
        second = evaluate([2, 5, -1, 7], weights=[10, 20, 30, 40])
        self.assertEqual(first, second)

    def test_weighted_clipped_jackknife_matches_manual_deletions(self):
        scores = {PARENT: 7, OTHER: 8}
        values = [0, 100, 800, -200]
        weights = [1, 2, 1, 3]
        selected, report = evaluate(values, scores=scores, weights=weights)
        deleted = []
        for index in range(4):
            w = sum(weight for j, weight in enumerate(weights) if j != index)
            mean = sum(weight * value for j, (weight, value) in enumerate(zip(weights, values)) if j != index) / w
            deleted.append(1 + max(-192, min(192, mean)))
        center = sum(deleted) / 4
        expected = math.sqrt(3/4 * sum((v-center)**2 for v in deleted))
        self.assertAlmostEqual(report['values'][1]['jackknife_standard_error'], expected)

    def test_one_sample_falls_back_to_native(self):
        selected, report = evaluate([80])
        self.assertEqual(selected, PARENT)
        json.dumps(report, allow_nan=False)

    def test_native_tie_and_immediate_victory_preserved(self):
        self.assertEqual(evaluate([0] * 8)[0], PARENT)
        self.assertEqual(evaluate([-100] * 8, scores={PARENT: 0, OTHER: 30000})[0], OTHER)

    def test_invalid_inputs_rejected(self):
        for weights in ([0, 1], [-1, 1], [float('nan'), 1]):
            with self.assertRaises(ValueError): evaluate([1, 2], weights=weights)
        with self.assertRaises(ValueError): evaluate([1, 2], multiplier=-1)
        with self.assertRaises(ValueError):
            paired_selection({PARENT: 0}, {}, PARENT, [({}, 0)], [1])


if __name__ == '__main__':
    unittest.main()
