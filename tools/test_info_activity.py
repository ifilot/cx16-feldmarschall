import random
import unittest

from analyze_info_activity import analyze_events, activity
from feldmarschall import Position, random_setup


class ActivityTests(unittest.TestCase):
    def position(self, pieces):
        position = Position()
        for sq, army, rank, known in pieces:
            position.cells[sq] = [army, rank, False, known]
        return position

    def test_terminal_disclosure_precedes_casualty_classification(self):
        pos = self.position([(34, 0, 8, False), (35, 1, 4, False)])
        result = analyze_events(pos, [(34, 35)], 0)['weak']
        self.assertEqual(result['casualties'], 1)
        self.assertEqual(result['zero_disclosure_casualties'], 0)
        self.assertEqual(result['new_enemy_disclosures'], 1)
        self.assertEqual(result['surviving_target_disclosures'], 1)
        self.assertIsNotNone(pos.cells[34])  # Input unchanged.

    def test_known_futile_loss_and_unknown_exchange(self):
        pos = self.position([(34, 0, 6, False), (35, 1, 4, True)])
        result = analyze_events(pos, [(34, 35)], 0)['weak']
        self.assertEqual(result['zero_disclosure_casualties'], 1)
        self.assertEqual(result['known_enemy_terminal_deaths'], 1)
        self.assertEqual(result['known_losing_attack_deaths'], 1)
        pos = self.position([(34, 0, 6, False), (35, 1, 6, False)])
        result = analyze_events(pos, [(34, 35)], 0)['weak']
        self.assertEqual(result['casualties'], 1)
        self.assertEqual(result['new_enemy_disclosures'], 1)
        self.assertEqual(result['surviving_target_disclosures'], 0)

    def test_prior_personal_disclosure_follows_physical_identity(self):
        pos = self.position([(34, 0, 5, False), (35, 1, 8, False),
                             (36, 1, 4, True), (99, 1, 8, False)])
        result = analyze_events(pos, [(34, 35), (99, 98), (35, 36)], 0)
        self.assertEqual(result['weak']['casualties'], 1)
        self.assertEqual(result['weak']['zero_disclosure_casualties'], 0)
        self.assertEqual(result['weak']['known_losing_attack_deaths'], 1)
        self.assertEqual(result['by_rank']['5']['new_enemy_disclosures'], 1)

    def test_unknown_attacker_disclosure_counts_for_weak_defender(self):
        pos = self.position([(34, 0, 8, False), (36, 1, 4, False)])
        result = analyze_events(pos, [(34, 35), (36, 35)], 0)['weak']
        self.assertEqual(result['casualties'], 1)
        self.assertEqual(result['zero_disclosure_casualties'], 0)
        result = analyze_events(self.position([(34, 0, 4, False), (35, 1, 8, False)]),
                                [(34, 35)], 1)['weak']
        self.assertEqual(result['casualties'], 1)
        self.assertEqual(result['zero_disclosure_casualties'], 0)
        self.assertEqual(result['new_enemy_disclosures'], 1)
        self.assertEqual(result['concealed_enemy_attacks'], 0)

    def test_long_scout_is_already_disclosed_when_captured(self):
        pos = self.position([(30, 0, 8, False), (35, 1, 6, False)])
        result = analyze_events(pos, [(30, 34), (35, 34)], 1)['weak']
        self.assertEqual(result['new_enemy_disclosures'], 0)
        self.assertEqual(result['unit_appearances'], 1)

    def test_miner_separate_and_terminal_flag(self):
        pos = self.position([(34, 0, 7, False), (35, 1, 4, True)])
        result = analyze_events(pos, [(34, 35)], 0)
        self.assertEqual(result['miners_lost'], 1)
        self.assertEqual(result['weak']['casualties'], 0)
        pos = self.position([(34, 0, 8, False), (35, 1, 11, False)])
        result = analyze_events(pos, [(34, 35)], 0)['weak']
        self.assertEqual(result['new_enemy_disclosures'], 1)
        with self.assertRaises(ValueError):
            analyze_events(pos, [(34, 35), (35, 36)], 0)

    def test_illegal_trace_rejected(self):
        with self.assertRaises(ValueError):
            analyze_events(self.position([(34, 0, 6, False)]), [(34, 36)], 0)

    def test_game_cohort_denominators_and_policy_resolution(self):
        rng = random.Random(17311)
        game = dict(red='candidate', blue='control',
                    red_setup=random_setup(rng), blue_setup=random_setup(rng),
                    moves=[], result='error', id=1, pair_id=2, seed=17311,
                    family='fortified')
        result = activity(game, 'candidate')
        self.assertEqual(result['appearances'], 1)
        self.assertEqual(result['scored_games'], 0)
        self.assertEqual(result['error_prefixes'], 1)
        self.assertEqual(result['side'], 0)
        self.assertGreater(result['weak']['unit_appearances'], 0)
        game['result'] = 'draw'
        result = activity(game, 'control')
        self.assertEqual(result['side'], 1)
        self.assertEqual(result['scored_games'], 1)
        self.assertEqual(result['error_prefixes'], 0)
        with self.assertRaises(ValueError):
            activity(game, 'absent')

    def test_probe_followup_tracks_retreat_and_actual_winning_capture(self):
        pos = self.position([(34, 0, 8, False), (35, 1, 4, False),
                             (24, 0, 3, False)])
        result = analyze_events(pos, [(34, 35), (35, 25), (24, 25)], 0)
        weak = result['weak']
        for key in ('surviving_target_disclosures', 'probe_next_turn_reached',
                    'probe_target_survived_reply', 'favorable_followup_available',
                    'favorable_followup_taken'):
            self.assertEqual(weak[key], 1, key)
        self.assertEqual(result['by_rank']['8']['favorable_followup_taken'], 1)

    def test_probe_beneficiary_removed_by_reply(self):
        # Spy could attack a disclosed Marshal, but Marshal captures it first.
        pos = self.position([(34, 0, 8, False), (35, 1, 0, False),
                             (36, 0, 9, False), (30, 0, 6, False)])
        weak = analyze_events(pos, [(34, 35), (35, 36), (30, 31)], 0)['weak']
        self.assertEqual(weak['probe_next_turn_reached'], 1)
        self.assertEqual(weak['probe_target_survived_reply'], 1)
        self.assertEqual(weak['favorable_followup_available'], 0)
        self.assertEqual(weak['favorable_followup_taken'], 0)

    def test_probe_target_dies_during_reply(self):
        pos = self.position([(34, 0, 8, False), (35, 1, 4, False),
                             (36, 0, 0, False), (30, 0, 6, False)])
        weak = analyze_events(pos, [(34, 35), (35, 36), (30, 31)], 0)['weak']
        self.assertEqual(weak['probe_next_turn_reached'], 1)
        self.assertEqual(weak['probe_target_survived_reply'], 0)
        self.assertEqual(weak['favorable_followup_available'], 0)

    def test_probe_opportunity_available_but_not_taken(self):
        pos = self.position([(34, 0, 8, False), (35, 1, 4, False),
                             (24, 0, 3, False), (30, 0, 6, False)])
        weak = analyze_events(pos, [(34, 35), (35, 25), (30, 31)], 0)['weak']
        self.assertEqual(weak['favorable_followup_available'], 1)
        self.assertEqual(weak['favorable_followup_taken'], 0)

    def test_probe_game_ends_before_followup(self):
        pos = self.position([(34, 0, 8, False), (35, 1, 4, False),
                             (36, 0, 11, False)])
        for moves in ([(34, 35)], [(34, 35), (35, 36)]):
            weak = analyze_events(pos, moves, 0)['weak']
            self.assertEqual(weak['surviving_target_disclosures'], 1)
            self.assertEqual(weak['probe_next_turn_reached'], 0)
            self.assertEqual(weak['favorable_followup_available'], 0)


if __name__ == '__main__':
    unittest.main()
