"""Test public terminal-threat diagnostics without private rank assignments."""
import unittest

from analyze_public_flag_survival import classify, flag_threats
from feldmarschall import Position, FLAG, SCOUT, UNKNOWN, TWO_SQUARES


class PublicFlagSurvivalTests(unittest.TestCase):
    def position(self):
        position = Position()
        position.cells = [None]*100
        position.cells[99] = [0, FLAG, False, False]
        return position

    def test_movement_proves_adjacent_unknown_can_capture_flag(self):
        position = self.position()
        position.cells[98] = [1, UNKNOWN, True, False]
        self.assertEqual(flag_threats(position, 0), [98])
        position.cells[98][2] = False
        self.assertEqual(flag_threats(position, 0), [])

    def test_two_squares_can_forbid_even_a_confirmed_flag_capture(self):
        position = self.position()
        position.cells[98] = [1, 5, True, True]
        position.shuttle[1] = (99, 98, TWO_SQUARES)
        self.assertEqual(flag_threats(position, 0), [])
        position.shuttle[1] = (99, 98, TWO_SQUARES-1)
        self.assertEqual(flag_threats(position, 0), [98])

    def test_vacating_a_blocker_opens_a_public_scout_ray(self):
        position = self.position()
        position.cells[90] = [1, SCOUT, True, True]
        position.cells[95] = [0, 5, True, False]
        self.assertEqual(flag_threats(position, 0), [])
        self.assertTrue(classify(position, 0, (95, 85))['confirmed_flag_capture_in_every_branch'])
        self.assertTrue(classify(position, 0, (95, 96))['guarantees_no_confirmed_flag_capture'])

    def test_unknown_capture_is_not_assumed_successful(self):
        position = self.position()
        position.cells[98] = [1, UNKNOWN, True, False]
        position.cells[88] = [0, SCOUT, True, False]
        result = classify(position, 0, (88, 98))
        self.assertFalse(result['guarantees_no_confirmed_flag_capture'])
        self.assertFalse(result['confirmed_flag_capture_in_every_branch'])
        self.assertEqual(result['branches'], 10)
        position.cells[88][1] = 0
        self.assertTrue(classify(position, 0, (88, 98))['guarantees_no_confirmed_flag_capture'])

    def test_immediate_flag_win_precedes_enemy_reply(self):
        position = self.position()
        position.cells[98] = [1, 5, True, True]
        position.cells[1] = [0, 5, True, False]
        position.cells[0] = [1, FLAG, False, True]
        self.assertTrue(classify(position, 0, (1, 0))['guarantees_no_confirmed_flag_capture'])


if __name__ == '__main__':
    unittest.main()
