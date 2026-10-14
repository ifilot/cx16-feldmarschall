"""Check legal inventories and the intended adversarial deployment properties."""
from collections import Counter
import random
import unittest

from feldmarschall import (RED, BLUE, Position,
                          STRESS_SETUPS, describe_setup, setup_neighbors,
                          stress_setup, valid_setup)
from arena import deployments


class StressDeployments(unittest.TestCase):
    def test_inventory_geometry_and_properties(self):
        for kind in STRESS_SETUPS:
            rng = random.Random(20261014)
            rows = Counter()
            for _ in range(500):
                layout = stress_setup(kind, rng)
                self.assertTrue(valid_setup(layout), (kind, layout))
                info = describe_setup(layout)
                rows[info['flag_row_from_front']] += 1
                if kind == 'fortified':
                    self.assertEqual(info['flag_row_from_front'], 3)
                    self.assertGreaterEqual(info['adjacent_bomb_guards'], 2)
                elif kind == 'unguarded':
                    self.assertEqual(info['flag_row_from_front'], 3)
                    self.assertEqual(info['adjacent_bomb_guards'], 0)
                elif kind == 'forward':
                    self.assertEqual(info['flag_row_from_front'], 0)
                    self.assertEqual(info['adjacent_bomb_guards'], 0)
                elif kind == 'decoy':
                    self.assertLess(info['flag_row_from_front'], 2)
                    self.assertEqual(info['adjacent_bomb_guards'], 0)
                    self.assertTrue(any(layout[i] not in 'BF' and all(
                        layout[n] == 'B' for n in setup_neighbors(i)) for i in range(31, 39)))
                for army in (RED, BLUE):
                    board = Position()
                    board.place(army, layout)
                    self.assertTrue(board.moves(army))
                    self.assertEqual(sum(cell is not None for cell in board.cells), 40)
            if kind == 'uniform':
                self.assertEqual(set(rows), {0, 1, 2, 3})

    def test_reproducibility_and_cross_family_mixture(self):
        for kind in (*STRESS_SETUPS, 'broad-mixed', 'presets', 'random', 'mixed'):
            first, second = random.Random(12345), random.Random(12345)
            for _ in range(30):
                self.assertEqual(deployments(kind, first), deployments(kind, second))
        rng = random.Random(12345)
        layouts = [deployments('broad-mixed', rng) for _ in range(200)]
        self.assertTrue(all(valid_setup(layout) for layout in layouts))
        self.assertTrue(any(describe_setup(layout)['flag_row_from_front'] == 0 for layout in layouts))
        self.assertTrue(any(describe_setup(layout)['flag_row_from_front'] == 3 for layout in layouts))
        self.assertTrue(any(describe_setup(layout)['adjacent_bomb_guards'] == 0 for layout in layouts))
        self.assertTrue(any(describe_setup(layout)['adjacent_bomb_guards'] >= 2 for layout in layouts))


if __name__ == '__main__':
    unittest.main()
