"""Mechanical public-contract tests; no strength evaluation."""
import unittest
from independent_trap_review import fixture
from trap_filter_prototype import clone, filter_move, trap_witness


class LastMinerProofTests(unittest.TestCase):
    def setUp(self):
        self.p, self.lost = fixture()

    def test_original_trap_all_friendly_rescues_and_bounded_retreat(self):
        before = clone(self.p)
        result = filter_move(self.p, 1, self.lost, (65, 66))
        self.assertTrue(result['changed'])
        self.assertEqual(result['move'], [65, 55])
        self.assertEqual(result['retreat']['second'], [55, 45])
        self.assertEqual(result['trap']['enemy_quiet_reply'], [68, 67])
        replies = result['trap']['friendly_reply_certificates']
        self.assertEqual(len(replies), 30)
        self.assertEqual(sum('enemy_capture' in r for r in replies), 29)
        self.assertEqual(self.p.cells, before.cells)
        self.assertEqual(self.p.shuttle, before.shuttle)

    def test_both_armies_and_rotated_board(self):
        p = clone(self.p)
        p.cells = [None if c is None else [1-c[0], *c[1:]]
                   for c in reversed(self.p.cells)]
        p.shuttle = {1-a: tuple(99-v if i < 2 and v is not None else v
                                for i, v in enumerate(values))
                     for a, values in self.p.shuttle.items()}
        result = filter_move(p, 0, self.lost, (34, 33))
        self.assertTrue(result['changed'])
        self.assertEqual(result['trap']['enemy_quiet_reply'], [31, 32])
        self.assertEqual(len(result['trap']['friendly_reply_certificates']), 30)

    def test_twelve_private_nibble_mutations_are_irrelevant(self):
        reference = filter_move(self.p, 1, self.lost, (65, 66))
        for rank in range(12):
            p = clone(self.p)
            for c in p.cells:
                if c and c[0] == 0 and not c[3]:
                    c[1] = rank
            self.assertEqual(filter_move(p, 1, self.lost, (65, 66)), reference)

    def test_other_selected_move_and_safe_miner_step_preserve_default(self):
        for move in ((79, 89), (65, 55)):
            result = filter_move(self.p, 1, self.lost, move)
            self.assertFalse(result['changed'])
            self.assertEqual(result['move'], list(move))

    def test_node_cap_falls_back(self):
        result = filter_move(self.p, 1, self.lost, (65, 66), max_nodes=0)
        self.assertFalse(result['changed'])
        self.assertTrue(result['capped'])

    def test_second_own_miner_disables_resource_gate(self):
        self.p.cells[20] = [1, 7, False, False]
        self.assertFalse(filter_move(self.p, 1, self.lost, (65, 66))['changed'])

    def test_own_flag_screen_exception(self):
        self.p.cells[1] = None
        result = filter_move(self.p, 1, self.lost, (65, 66))
        self.assertFalse(result['changed'])
        self.assertIn('own Flag', result['bailout'])

    def test_known_friendly_rescue_refutes_trap(self):
        self.p.cells[77] = [1, 0, True, True]
        witness, _, _ = trap_witness(self.p, 1, (65, 66), 96)
        self.assertIsNone(witness)

    def test_any_uncertain_friendly_combat_aborts_witness(self):
        self.p.cells[20] = [1, 8, False, False]
        self.p.cells[21] = [0, 12, True, False]
        witness, _, _ = trap_witness(self.p, 1, (65, 66), 96)
        self.assertIsNone(witness)

    def test_terminal_flag_capture_refutes_witness_even_if_concealed(self):
        # Unit-test the terminal guard independently of the resource gate:
        # own Scout20 can capture the deduced concealed Flag21 immediately.
        self.p.cells[20] = [1, 8, False, False]
        self.p.cells[21] = [0, 12, False, False]
        witness, _, _ = trap_witness(self.p, 1, (65, 66), 21)
        self.assertIsNone(witness)

    def test_shuttle_excludes_illegal_retreat_and_uses_other_certificate(self):
        # Reversing65->55 would be a forbidden sixth reversal. The other
        # public certificate65->64->54 remains legal.
        self.p.shuttle[1] = (55, 65, 5)
        result = filter_move(self.p, 1, self.lost, (65, 66))
        self.assertTrue(result['changed'])
        self.assertEqual(result['move'], [65, 64])
        self.assertEqual(result['retreat']['second'], [64, 54])


if __name__ == '__main__':
    unittest.main()
