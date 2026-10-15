"""Mechanism and public-information boundaries for army activation."""
import unittest

from campaign_strategy import adjustments, potential
from feldmarschall import LAKES


def board():
    result = [255] * 100
    for sq in LAKES:
        result[sq] = 254
    return result


def rotate(cells):
    return [cell ^ 16 if cell < 254 else cell for cell in reversed(cells)]


class ActivationTests(unittest.TestCase):
    def test_enemy_hidden_ranks_do_not_matter(self):
        cells = board()
        cells[61], cells[31], cells[30] = 7, 16 | 12, 16 | 12
        moves = {(61, 51): 0, (61, 60): 0}
        baseline = adjustments(cells, 0, [], {}, moves)
        for rank in range(12):
            cells[31] = 16 | rank
            cells[30] = 16 | ((rank+3) % 12)
            self.assertEqual(baseline, adjustments(cells, 0, [], {}, moves))

    def test_rotation_and_colour_symmetry(self):
        cells = board()
        cells[81], cells[71], cells[61], cells[51] = 7, 0, 8, 16 | 12
        moves = {(61, 60): 0, (71, 70): 0, (71, 72): 0}
        expected = adjustments(cells, 0, [], {}, moves)
        other = adjustments(rotate(cells), 1, [], {},
                            {(99-a, 99-b): score for (a, b), score in moves.items()})
        self.assertAlmostEqual(potential(cells, 0), potential(rotate(cells), 1))
        for (a, b), value in expected.items():
            self.assertAlmostEqual(value, other[(99-a, 99-b)])

    def test_unblocking_teammate_increases_its_access(self):
        cells = board()
        # Trapped Miner at a1 can leave only through the Scout at a2.
        cells[90], cells[80], cells[91] = 7, 8, 10
        before = potential(cells, 0)
        after = cells[:]
        after[80], after[81] = 255, 8
        self.assertGreater(potential(after, 0), before)
        self.assertGreater(adjustments(cells, 0, [], {}, {(80, 81): 0})[(80, 81)], 0)

    def test_combat_and_immediate_victory_unchanged(self):
        cells = board()
        cells[61], cells[51] = 7, 16 | 12
        self.assertEqual(adjustments(cells, 0, [], {}, {(61, 51): 0, (61, 60): 30000}),
                         {(61, 51): 0.0, (61, 60): 0.0})

    def test_bounded_no_mutation_and_closed_crossing(self):
        cells = board()
        for sq in (60, 61, 64, 65, 68, 69):
            cells[sq] = 0
        original = cells[:]
        result = adjustments(cells, 0, [], {}, {(60, 50): 0, (61, 71): 0})
        self.assertEqual(cells, original)
        self.assertTrue(all(abs(value) <= 24 for value in result.values()))
        blocked = board()
        for sq in range(100):
            if blocked[sq] == 255:
                blocked[sq] = 16 | 12
        blocked[90] = 7
        self.assertEqual(potential(blocked, 0), 0)


if __name__ == '__main__':
    unittest.main()
