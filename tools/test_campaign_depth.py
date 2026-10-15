"""Public width-only horizon selection and immutable mechanism evidence."""
import unittest

from campaign_depth import depth_for_actions


class AdaptiveDepth(unittest.TestCase):
    def test_only_sparse_four_ply_search_gets_longer_horizon(self):
        for count in range(1, 13):
            self.assertEqual(depth_for_actions(4, count), 8)
        for count in (13, 24, 100, 2000):
            self.assertEqual(depth_for_actions(4, count), 4)

    def test_other_explicit_horizons_are_preserved(self):
        for depth in (1, 2, 3, 5, 6, 8, 12):
            for count in (1, 12, 13, 24):
                self.assertEqual(depth_for_actions(depth, count), depth)

    def test_invalid_inputs_rejected_without_silent_coercion(self):
        for depth in (0, -1, 13, True, 4.0, '4', None):
            with self.assertRaises(ValueError):
                depth_for_actions(depth, 12)
        for count in (0, -1, 2001, True, 12.0, '12', None):
            with self.assertRaises(ValueError):
                depth_for_actions(4, count)


if __name__ == '__main__':
    unittest.main()
