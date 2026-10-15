"""Behavior and public-information boundary tests for frozen lifetime v1."""
import random
import unittest

from info_lifetime import SETTINGS, adjustments


class LifetimeTests(unittest.TestCase):
    def board(self, army=0, rank=8, enemy_rank=4, revealed=True):
        cells = [255] * 100
        cells[44] = rank | (16 if army else 0)
        cells[45] = enemy_rank | (0 if army else 16) | (32 if revealed else 0)
        return cells

    def score(self, cells, moves=None, army=0):
        return adjustments(cells, army, [0] * 12, {}, moves or {(44, 45): 0})

    def test_new_information_allowed_but_known_futile_loss_costs(self):
        self.assertEqual(self.score(self.board())[(44, 45)], -32)
        self.assertEqual(self.score(self.board(enemy_rank=10))[(44, 45)], -32)
        self.assertEqual(self.score(self.board(revealed=False))[(44, 45)], 0)

    def test_known_win_or_exchange_not_penalized(self):
        for enemy in (8, 9, 11):
            self.assertEqual(self.score(self.board(enemy_rank=enemy))[(44, 45)], 0)

    def test_sergeant_expendable_but_miner_and_spy_keep_special_roles(self):
        self.assertEqual(self.score(self.board(rank=6))[(44, 45)], -32)
        for rank in (0, 5, 7, 9):
            self.assertEqual(self.score(self.board(rank=rank))[(44, 45)], 0)

    def test_both_armies(self):
        for army in (0, 1):
            self.assertEqual(self.score(self.board(army=army), army=army)[(44, 45)], -32)

    def test_quiet_entry_to_new_known_threat(self):
        cells = self.board()
        cells[45], cells[46] = 255, cells[45]
        self.assertEqual(self.score(cells)[(44, 45)], -16)
        cells[46] &= ~32
        self.assertEqual(self.score(cells)[(44, 45)], 0)

    def test_existing_threat_does_not_trap_escape_or_reposition(self):
        cells = self.board()
        cells[45], cells[34] = 255, cells[45]
        self.assertEqual(self.score(cells, {(44, 43): 0})[(44, 43)], 0)

    def test_no_row_wrap_threat(self):
        cells = [255] * 100
        cells[18], cells[20] = 8, 4 | 16 | 32
        self.assertEqual(self.score(cells, {(18, 19): 0})[(18, 19)], 0)

    def test_finite_cost_allows_tactically_justified_sacrifice(self):
        cells = self.board()
        values = {(44, 45): 90, (44, 43): 40}
        delta = self.score(cells, values)
        self.assertEqual(max(values, key=lambda m: values[m] + delta[m]), (44, 45))
        values[(44, 45)] = 50
        self.assertEqual(max(values, key=lambda m: values[m] + delta[m]), (44, 43))
        values[(44, 45)] = 30000
        self.assertEqual(self.score(cells, values)[(44, 45)], 0)

    def test_hidden_truth_permutations_and_irrelevant_ledgers(self):
        cells = self.board(revealed=False)
        moves = {(44, 45): 0, (44, 43): 0}
        expected = self.score(cells, moves)
        rng = random.Random(17001)
        for _ in range(120):
            cells[45] = rng.randrange(12) | 16
            cells[33] = rng.randrange(12) | 16
            got = adjustments(cells, 0, [rng.randrange(5) for _ in range(12)],
                              {45: [rng.randrange(100) for _ in range(11)]}, moves)
            self.assertEqual(got, expected)

    def test_settings_frozen(self):
        self.assertEqual(SETTINGS['known_losing_attack_cost'], 32)
        self.assertEqual(SETTINGS['new_disclosed_exposure_cost'], 16)


if __name__ == '__main__':
    unittest.main()
