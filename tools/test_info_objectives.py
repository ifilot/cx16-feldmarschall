"""Focused behavior and public-input tests for Flag Corridor Recon v1."""
import random
import unittest

from feldmarschall import LAKES
from info_objectives import adjustments, _distances


class CorridorReconTest(unittest.TestCase):
    def position(self):
        cells = [254 if sq in LAKES else 255 for sq in range(100)]
        cells[32] = 8  # own Scout
        cells[21] = 0  # own Marshal, able to use the reconnaissance
        cells[12] = 16 | 12  # enemy unknown Flag/Bomb candidate
        histories = {12: [0] * 10 + [(1 << 10) | (1 << 11)]}
        moves = {(32, 22): 0, (32, 33): 0, (32, 12): 0}
        return cells, histories, moves

    def call(self, cells, histories, moves, army=0, lost=None):
        return adjustments(cells, army, lost or [0] * 12, histories, moves)

    def test_progress_and_disclosure(self):
        cells, histories, moves = self.position()
        scores = self.call(cells, histories, moves)
        self.assertGreater(scores[32, 22], 0)
        self.assertLess(scores[32, 33], 0)
        self.assertGreater(scores[32, 12], scores[32, 22])
        self.assertEqual(set(scores), set(moves))

    def test_no_beneficiary_no_information_mission(self):
        cells, histories, moves = self.position()
        cells[21] = 255
        self.assertTrue(all(v == 0 for v in self.call(cells, histories, moves).values()))

    def test_known_target_gives_no_disclosure_credit(self):
        cells, histories, moves = self.position()
        cells[12] = 16 | 32 | 11
        self.assertEqual(self.call(cells, histories, moves)[32, 12], 0)

    def test_miner_and_spy_preserved(self):
        cells, histories, moves = self.position()
        for rank in (0, 1, 2, 3, 4, 7, 9):
            cells[32] = rank
            self.assertTrue(all(v == 0 for v in self.call(cells, histories, moves).values()))

    def test_public_movement_excludes_flag(self):
        cells, histories, moves = self.position()
        cells[12] |= 64
        self.assertTrue(all(v == 0 for v in self.call(cells, histories, moves).values()))

    def test_inventory_deduction_needs_no_sacrifice(self):
        cells, histories, moves = self.position()
        lost = [0] * 12
        lost[10] = 6  # then this mask identifies the Flag without probing
        self.assertTrue(all(v == 0 for v in self.call(cells, histories, moves, lost=lost).values()))

    def test_publicly_known_threat_removes_progress_reward(self):
        cells, histories, moves = self.position()
        cells[23] = 16 | 32 | 1
        self.assertLess(self.call(cells, histories, moves)[32, 22], 0)

    def test_hidden_rank_invariance(self):
        cells, histories, moves = self.position()
        expected = self.call(cells, histories, moves)
        for rank in range(12):
            cells[12] = 16 | rank
            self.assertEqual(self.call(cells, histories, moves), expected)

    def test_input_not_mutated_or_score_scale_read(self):
        cells, histories, moves = self.position()
        before = (cells[:], {s: h[:] for s, h in histories.items()}, dict(moves))
        expected = self.call(cells, histories, moves)
        self.assertEqual((cells, histories, moves), before)
        self.assertEqual(expected, self.call(cells, histories, {m: 900 for m in moves}))

    def test_rotation_and_color_symmetry(self):
        cells, histories, moves = self.position()
        expected = self.call(cells, histories, moves)
        rotated = [cell ^ 16 if cell < 254 else cell for cell in reversed(cells)]
        scores = self.call(rotated, {99-s: h for s, h in histories.items()},
                           {(99-s, 99-d): v for (s, d), v in moves.items()}, army=1)
        self.assertEqual({(99-s, 99-d): v for (s, d), v in expected.items()}, scores)

    def test_lakes_and_other_pieces_are_not_shortcuts(self):
        cells = [254 if s in LAKES else 255 for s in range(100)]
        self.assertEqual(_distances(cells, 41, (44,))[44], 5)
        # Close both detours. Squares beyond the screen cannot be reached by
        # pretending that the terminal enemy is removed after a probe.
        for sq in (31, 51, 40):
            cells[sq] = 0
        self.assertNotIn(44, _distances(cells, 41, (44,)))
        cells = [255] * 100
        cells[11] = 16 | 12
        for sq in (1, 10, 20, 21):
            cells[sq] = 254
        self.assertIn(11, _distances(cells, 12, (11,)))
        self.assertNotIn(0, _distances(cells, 12, (11,)))

    def test_bounded_on_random_public_boards(self):
        rng = random.Random(61719)
        for _ in range(100):
            cells, histories, moves = self.position()
            for sq in rng.sample([s for s in range(100) if cells[s] == 255], 15):
                cells[sq] = 16 | 32 | rng.randrange(12)
            result = self.call(cells, histories, moves)
            self.assertTrue(all(-16 <= value <= 16 for value in result.values()))


if __name__ == '__main__':
    unittest.main()
