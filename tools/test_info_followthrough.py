"""Mechanism tests for fair one-response information missions (Classic only)."""
import unittest

from feldmarschall import COUNTS, FLAG, LAKES, Position, SCOUT
from info_followthrough import _moves_from, adjustments


def fixture():
    cells = [255] * 100
    for sq in LAKES:
        cells[sq] = 254
    # Two legal Colonels cover both the corner and its vacated escape square.
    # Probe survives neither a General nor a Major. Colonels must abstain from
    # attacking the former and can safely take the latter after either reply.
    cells[1] = cells[11] = 2
    cells[20] = SCOUT
    cells[0] = cells[99] = 16 | 12
    lost = COUNTS[:]
    lost[1] -= 1
    lost[3] -= 1
    histories = {sq: [0] * 10 + [(1 << 1) | (1 << 3)] for sq in (0, 99)}
    return cells, lost, histories


class FollowthroughTests(unittest.TestCase):
    def test_positive_information_with_both_flags_and_valid_inventories(self):
        cells, lost, histories = fixture()
        cells[90] = FLAG
        cells[9] = 16 | 12
        cells[0] |= 64
        cells[99] |= 64
        lost[FLAG] -= 1
        histories[0] = histories[99] = [0] * 10 + [0x3ff]
        histories[9] = [0] * 10 + [0xfff]
        moves = {(20, 0): 0.0, (1, 2): 1.0}
        # Both assignments complete the public observation into a physical
        # ongoing Classic position, with legal root moves and a living Flag
        # for each army. Counts plus recorded enemy casualties exactly match
        # the original enemy inventory; own survivors respect its inventory.
        for target_rank, remote_rank in ((1, 3), (3, 1)):
            physical = Position()
            for sq, cell in enumerate(cells):
                if cell < 254:
                    rank = ({0: target_rank, 99: remote_rank, 9: FLAG}[sq]
                            if cell & 16 else cell & 15)
                    physical.cells[sq] = [int(bool(cell & 16)), rank, bool(cell & 64), False]
            self.assertTrue(set(moves).issubset(physical.moves(0)))
            for army in (0, 1):
                survivors = [sum(cell is not None and cell[0] == army and cell[1] == rank
                                 for cell in physical.cells) for rank in range(12)]
                self.assertEqual(survivors[FLAG], 1)
                self.assertTrue(all(n <= initial for n, initial in zip(survivors, COUNTS)))
                if army == 1:
                    self.assertEqual([n + dead for n, dead in zip(survivors, lost)], COUNTS)
        correction = adjustments(cells, 0, lost, histories, moves)
        self.assertAlmostEqual(correction[20, 0], 27.5)
        self.assertEqual(max(moves, key=moves.get), (1, 2))
        self.assertEqual(max(moves, key=lambda move: moves[move] + correction.get(move, 0)), (20, 0))

    def test_positive_information_covers_escape_and_changes_choice(self):
        cells, lost, histories = fixture()
        moves = {(20, 0): 0.0, (1, 2): 1.0}
        correction = adjustments(cells, 0, lost, histories, moves)
        self.assertAlmostEqual(correction[20, 0], 27.5)
        self.assertEqual(max(moves, key=moves.get), (1, 2))
        self.assertEqual(max(moves, key=lambda move: moves[move] + correction.get(move, 0)), (20, 0))

    def test_escape_without_second_beneficiary_buys_no_usable_information(self):
        cells, lost, histories = fixture()
        cells[11] = 255
        self.assertEqual(adjustments(cells, 0, lost, histories, {(20, 0): 0})[20, 0], -10)

    def test_enemy_can_remove_escape_beneficiary(self):
        cells, lost, histories = fixture()
        # The disclosed enemy Marshal can remove the Colonel covering square0
        # while the target waits, destroying the formerly robust continuation.
        cells[2] = 16 | 32
        lost[0] -= 1
        self.assertEqual(adjustments(cells, 0, lost, histories, {(20, 0): 0})[20, 0], -10)

    def test_known_target_has_no_information_adjustment(self):
        cells, lost, histories = fixture()
        cells[0] = 16 | 32 | 3
        self.assertEqual(adjustments(cells, 0, lost, histories, {(20, 0): 0}), {})

    def test_opponent_flag_capture_leaves_no_next_turn(self):
        cells, lost, histories = fixture()
        cells[98] = 11
        self.assertEqual(adjustments(cells, 0, lost, histories, {(20, 0): 0})[20, 0], -10)

    def test_lakes_blocked_rays_and_diagonal_are_not_legal(self):
        cells, _, _ = fixture()
        self.assertNotIn(0, list(_moves_from(cells, 11, 2, 0)))
        cells[20] = 255
        cells[40] = SCOUT
        self.assertNotIn(44, list(_moves_from(cells, 40, SCOUT, 0)))
        cells[10] = 5
        cells[20] = SCOUT
        self.assertNotIn(0, list(_moves_from(cells, 20, SCOUT, 0)))

    def test_privacy_and_input_immutability(self):
        cells, lost, histories = fixture()
        original = cells[:], lost[:], {k: v[:] for k, v in histories.items()}
        first = adjustments(cells, 0, lost, histories, {(20, 0): 0})
        self.assertEqual((cells, lost, histories), original)
        self.assertEqual(first, adjustments(cells[:], 0, lost[:], dict(histories), {(20, 0): 0}))
        cells[0] = 16 | 3  # A private true rank is never accepted as public input.
        with self.assertRaisesRegex(ValueError, 'masked'):
            adjustments(cells, 0, lost, histories, {(20, 0): 0})

    def test_side_symmetry(self):
        cells, lost, histories = fixture()
        mirrored = [cell ^ 16 if cell < 254 else cell for cell in cells]
        self.assertEqual(adjustments(cells, 0, lost, histories, {(20, 0): 0}),
                         adjustments(mirrored, 1, lost, histories, {(20, 0): 0}))

    def test_material_budget_without_any_beneficiary(self):
        cells, lost, histories = fixture()
        cells[1] = cells[11] = 255
        self.assertEqual(adjustments(cells, 0, lost, histories, {(20, 0): 0})[20, 0], -10)


if __name__ == '__main__':
    unittest.main()
