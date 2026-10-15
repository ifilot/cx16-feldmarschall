import unittest

from campaign_recurrence import RecurrenceEscape
from feldmarschall import LAKES


def board(a=60, b=69):
    result = [254 if sq in LAKES else 255 for sq in range(100)]
    result[a], result[b], result[20] = 0, 7, 16 | 12
    return result


class RecurrenceTests(unittest.TestCase):
    def cycle(self, module):
        # Alternating actors evade a last-move-only reverse penalty.
        for _ in range(5):
            for a, b in ((60, 69), (61, 69), (61, 68), (60, 68)):
                module.adjustments(board(a, b), 0, [], {}, {(a, a-10): 0})

    def test_alternating_actor_cycle_versus_novel_continuation(self):
        module = RecurrenceEscape()
        self.cycle(module)
        result = module.adjustments(board(), 0, [], {}, {(60, 61): 10, (60, 50): 0})
        self.assertEqual(result, {(60, 61): -24.0, (60, 50): 0.0})
        self.assertTrue(module.last_report['active'])

    def test_aspiration_prevents_expensive_forced_escape(self):
        module = RecurrenceEscape()
        self.cycle(module)
        result = module.adjustments(board(), 0, [], {}, {(60, 61): 100, (60, 50): 0})
        self.assertFalse(any(result.values()))

    def test_capture_or_disclosure_resets_memory(self):
        for capture in (True, False):
            module = RecurrenceEscape()
            self.cycle(module)
            cells = board()
            cells[20] = 255 if capture else 16 | 32 | 8
            self.assertFalse(any(module.adjustments(cells, 0, [], {}, {(60, 61): 0}).values()))
            self.assertEqual(module.quiet, 0)

    def test_reset_and_win_aspiration(self):
        module = RecurrenceEscape()
        self.cycle(module)
        self.assertFalse(any(module.adjustments(board(), 0, [], {},
                                              {(60, 61): 30000, (60, 50): 0}).values()))
        module.reset()
        self.assertEqual(len(module.history), 0)
        self.assertEqual(module.quiet, 0)

    def test_concealed_truth_invariance(self):
        a, b = RecurrenceEscape(), RecurrenceEscape()
        self.cycle(a)
        self.cycle(b)
        cells = board()
        hidden = cells[:]
        hidden[20] = 16 | 9
        moves = {(60, 61): 10, (60, 50): 0}
        self.assertEqual(a.adjustments(cells, 0, [], {}, moves),
                         b.adjustments(hidden, 0, [], {}, moves))


if __name__ == '__main__':
    unittest.main()
