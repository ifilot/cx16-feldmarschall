"""Geometric/rank invariants for the retrospective interceptor audit."""
import unittest

from campaign_flag_guard import adjustments, clone, coverage, evaluate, position_from_public, public_position
from feldmarschall import LAKES, Position


def fixture(intruder_rank=1, guard_rank=0):
    position = Position()
    position.cells[95] = [0, 11, False, False]
    position.cells[75] = [1, intruder_rank, True, True]
    position.cells[84] = [0, guard_rank, True, False]
    return position


def encode(position):
    cells = [254 if sq in LAKES else 255 if c is None else c[1] | (16 if c[0] else 0)
             | (64 if c[2] else 0) | (32 if c[3] else 0)
             for sq, c in enumerate(position.cells)]
    shuttle = bytes([position.shuttle[a][0] if position.shuttle[a][2] else 255 for a in (0, 1)]
                    + [position.shuttle[a][1] if position.shuttle[a][2] else 255 for a in (0, 1)]
                    + [position.shuttle[a][2] for a in (0, 1)])
    return cells, shuttle.hex()


class GuardCoverageTests(unittest.TestCase):
    def test_guard_preserves_next_turn_interception(self):
        position = fixture()
        self.assertTrue(coverage(position, 0, 75)['covered'])
        self.assertEqual(coverage(position, 0, 75)['guards'], [84])
        position.move(84, 83)
        self.assertFalse(coverage(position, 0, 75)['covered'])
        position.move(83, 84)
        self.assertTrue(coverage(position, 0, 75)['covered'])

    def test_spy_interception_differs_from_static_blocking(self):
        for attacker, guard in ((0, 9), (9, 0)):
            position = fixture(attacker, guard)
            self.assertTrue(coverage(position, 0, 75)['covered'])
            position.move(84, 85)
            self.assertFalse(coverage(position, 0, 75)['covered'])

    def test_weaker_guard_cannot_promise_interception(self):
        position = fixture(1, 7)
        self.assertFalse(coverage(position, 0, 75)['covered'])

    def test_immediate_scout_ray_and_friendly_blocker(self):
        position = Position()
        position.cells[95] = [0, 11, False, False]
        position.cells[5] = [1, 8, True, True]
        self.assertTrue(coverage(position, 0, 5)['immediate'])
        position.cells[55] = [0, 0, True, True]
        self.assertFalse(coverage(position, 0, 5)['immediate'])
        self.assertTrue(coverage(position, 0, 5)['covered'])

    def test_other_concealed_ranks_are_masked_and_no_mutation(self):
        position = fixture()
        position.cells[1] = [1, 0, False, False]
        before = clone(position)
        a = coverage(public_position(position, 0), 0, 75)
        position.cells[1][1] = 9
        b = coverage(public_position(position, 0), 0, 75)
        self.assertEqual(a, b)
        self.assertEqual(before.cells[75], position.cells[75])
        self.assertEqual(before.shuttle, position.shuttle)

    def test_public_two_squares_restriction_is_respected(self):
        position = fixture()
        position.shuttle[0] = (85, 84, 5)
        self.assertFalse(coverage(position, 0, 75)['covered'])
        # A different own move resets that army's restriction before its next
        # interception opportunity, which the branch must also represent.
        position.cells[90] = [0, 8, True, False]
        position.move(90, 80)
        self.assertTrue(coverage(position, 0, 75)['covered'])
        position = fixture()
        position.shuttle[1] = (85, 75, 5)
        self.assertTrue(coverage(position, 0, 75)['covered'])
        self.assertEqual(coverage(position, 0, 75)['approaches'], [])

    def test_rotation_and_colour_symmetry(self):
        position = fixture()
        rotated = Position()
        rotated.cells = [None if c is None else [1-c[0], *c[1:]] for c in reversed(position.cells)]
        self.assertTrue(coverage(rotated, 1, 24)['covered'])
        self.assertEqual(coverage(rotated, 1, 24)['guards'], [15])

    def test_enemy_can_capture_a_blocker_before_flag_attack(self):
        position = fixture(0, 9)
        position.cells[85] = [0, 8, False, False]
        report = coverage(position, 0, 75)
        self.assertTrue(report['covered'])
        self.assertEqual(report['approaches'][0]['move'], [75, 85])
        self.assertEqual(report['approaches'][0]['guard_squares'], [84])
        position.cells[84] = None
        self.assertFalse(coverage(position, 0, 75)['covered'])

    def test_interception_mission_orders_only_quiet_moves(self):
        position = fixture()
        position.move(84, 83)
        position.cells[60] = [0, 8, False, False]
        position.cells[50] = [1, 9, True, True]
        cells, shuttle = encode(position)
        moves = {(83, 84): 0.0, (83, 73): 10.0, (60, 50): 100.0}
        original = cells[:], dict(moves)
        changes, report = evaluate(cells, 0, object(), object(), moves, shuttle)
        self.assertTrue(report['active'])
        self.assertEqual(changes[(60, 50)], 0.0)
        self.assertGreater(moves[(83, 84)] + changes[(83, 84)], moves[(83, 73)] + changes[(83, 73)])
        self.assertEqual(original, (cells, moves))
        self.assertEqual(changes, adjustments(cells, 0, [], {}, moves, shuttle))

    def test_bailouts_for_win_known_or_publicly_moved_immediate_danger(self):
        position = fixture()
        position.move(84, 83)
        cells, shuttle = encode(position)
        moves = {(83, 84): 30000, (83, 73): 10}
        result, report = evaluate(cells, 0, [], {}, moves, shuttle)
        self.assertFalse(any(result.values()))
        self.assertEqual(report['reason'], 'immediate-win')
        for rank, revealed in ((1, True), (12, False)):
            position.cells[85] = [1, rank, True, revealed]
            cells, shuttle = encode(position)
            result, report = evaluate(cells, 0, [], {}, {(83, 84): 0, (83, 73): 10}, shuttle)
            self.assertFalse(any(result.values()))
            self.assertEqual(report['reason'], 'confirmed-immediate-flag-danger')

    def test_no_quiet_repair_or_maintainer_is_inactive(self):
        for position in (fixture(1, 7), fixture()):
            if position.cells[84][1] == 7:
                position.move(84, 83)
                moves = {(83, 84): 0, (83, 73): 10}
            else:
                moves = {(84, 83): 10, (84, 74): 0}
            cells, shuttle = encode(position)
            result, report = evaluate(cells, 0, [], {}, moves, shuttle)
            self.assertFalse(any(result.values()))
            self.assertFalse(report['active'])

    def test_shuttle_layout_and_hidden_nibble_invariance(self):
        position = fixture()
        position.move(84, 83)
        position.cells[1] = [1, 12, False, False]
        position.shuttle = {0: (84, 83, 1), 1: (65, 75, 1)}
        cells, shuttle = encode(position)
        decoded = position_from_public(cells, 0, shuttle)
        self.assertEqual(decoded.shuttle, position.shuttle)
        baseline = evaluate(cells, 0, [], {}, {(83, 84): 0, (83, 73): 10}, shuttle)
        for rank in range(12):
            altered = cells[:]
            altered[1] = (altered[1] & ~15) | rank
            self.assertEqual(baseline, evaluate(altered, 0, [], {}, {(83, 84): 0, (83, 73): 10}, shuttle))

    def test_existing_guard_is_retained_while_another_actor_moves(self):
        position = fixture()
        position.cells[60] = [0, 8, False, False]
        cells, shuttle = encode(position)
        moves = {(84, 83): 10, (60, 50): 0}
        changes, report = evaluate(cells, 0, [], {}, moves, shuttle)
        self.assertTrue(report['active'])
        self.assertEqual(report['reason'], 'retain-interception-mission')
        self.assertEqual(changes[(60, 50)], 0)
        self.assertLess(moves[(84, 83)] + changes[(84, 83)], moves[(60, 50)])
        # If every available quiet move keeps coverage, the mission is inert.
        changes, report = evaluate(cells, 0, [], {}, {(84, 85): 10, (60, 50): 0}, shuttle)
        self.assertFalse(any(changes.values()))
        self.assertFalse(report['active'])

    def test_known_flag_capture_bails_out_even_with_corrected_score(self):
        position = fixture()
        position.move(84, 83)
        position.cells[84] = [1, 11, False, True]
        cells, shuttle = encode(position)
        changes, report = evaluate(cells, 0, [], {}, {(83, 84): 29808, (83, 73): 0}, shuttle)
        self.assertFalse(any(changes.values()))
        self.assertEqual(report['reason'], 'immediate-win')


if __name__ == '__main__':
    unittest.main()
