"""Finite-cohort error bounds retain every planned paired game."""
import hashlib
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest

from campaign_error_sensitivity import compare
from feldmarschall import random_setup
from tournament_store import Tournament, mirror_setup


class ErrorSensitivity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='feld-error-bounds-')
        self.folder = Path(self.temp.name)
        self.own = random_setup(random.Random(433)); self.enemy = random_setup(random.Random(434))
        self.alternative = random_setup(random.Random(435))

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, policy, scores, mode='referee', own=None, opponent='dos'):
        path = self.folder/(policy+'.fmtour')
        with Tournament(path, create=True, metadata=dict(planned_games=len(scores), setup_mode=mode,
                                                        setup_owner=policy, families=['one','two'])) as store:
            for index, score in enumerate(scores):
                side = 'red' if index % 2 == 0 else 'blue'
                names = (policy, opponent) if side == 'red' else (opponent, policy)
                if score is None: result = 'error'
                elif score == .5: result = 'draw'
                elif score == 1: result = side
                else: result = 'blue' if side == 'red' else 'red'
                setups = (own or self.own, self.enemy)
                if mode in ('policy-owned','policy-owned-rotated-v1') and side == 'blue': setups = tuple(reversed(setups))
                if mode == 'policy-owned-rotated-v1' and side == 'blue': setups=tuple(map(mirror_setup,setups))
                game = dict(red=names[0], blue=names[1], seed=100+index//2, result=result,
                            reason='fixture', plies=0, moves=[])
                store.add_game(game, index//2+1, 'one' if index < 2 else 'two', setups)
            store.set_metadata(dict(status='complete'))
        return path

    def test_no_error_collapses_to_ordinary_paired_mean_and_draws_are_half(self):
        a = self.fixture('a', [1,.5,0,.5]); b = self.fixture('b', [.5,0,.5,0])
        result = compare(a,'a',b,'b'); summary = result['summary']
        self.assertEqual(summary['paired_cohort_effect_bounds'], [.25,.25])
        self.assertEqual(summary['complete_case_paired_effect'], .25)
        self.assertEqual(summary['planned_pairs'], 2)
        self.assertEqual(summary['arms']['a']['all_attempt_score_bounds'], [.5,.5])
        self.assertEqual(result['families']['one']['paired_cohort_effect_bounds'], [.5,.5])

    def test_errors_in_same_game_are_independent_unknowns_and_unscored_officially(self):
        a = self.fixture('a', [None,1]); b = self.fixture('b', [None,0])
        summary = compare(a,'a',b,'b')['summary']
        self.assertEqual(summary['paired_cohort_effect_bounds'], [0,1])
        self.assertEqual(summary['complete_case_pairs'], 0)
        self.assertEqual(summary['arms']['a']['official_scored_score'], 1)
        self.assertEqual(summary['arms']['a']['all_attempt_score_bounds'], [.5,1])
        self.assertEqual(summary['arms']['b']['all_attempt_score_bounds'], [0,.5])

    def test_errors_in_opposite_games_and_per_family_keep_complete_planned_denominator(self):
        a = self.fixture('a', [None,1,.5,.5]); b = self.fixture('b', [1,None,0,0])
        result = compare(a,'a',b,'b')
        self.assertEqual(result['summary']['paired_cohort_effect_bounds'], [0,.5])
        self.assertEqual(result['summary']['complete_case_paired_effect'], .5)
        self.assertEqual(result['families']['one']['paired_cohort_effect_bounds'], [-.5,.5])
        self.assertEqual(result['summary']['error_games_a'], 1)
        self.assertEqual(result['summary']['error_games_b'], 1)

    def test_all_error_cohort_is_bounded_not_scored_as_losses(self):
        a = self.fixture('a', [None,None]); b = self.fixture('b', [None,None])
        summary = compare(a,'a',b,'b')['summary']
        self.assertEqual(summary['paired_cohort_effect_bounds'], [-1,1])
        self.assertIsNone(summary['arms']['a']['official_scored_score'])
        self.assertEqual(summary['arms']['a']['losses'], 0)

    def test_cross_arm_seed_setup_opponent_and_pair_mismatches_rejected(self):
        for mutation in ("UPDATE games SET seed=999", "UPDATE games SET red_setup='"+self.alternative+"'",
                         "UPDATE games SET family='other'", "UPDATE games SET pair_id=2"):
            a = self.fixture('a', [1,0]); b = self.fixture('b', [1,0])
            with sqlite3.connect(b) as db: db.execute(mutation)
            with self.assertRaises(ValueError): compare(a,'a',b,'b')
            a.unlink(); b.unlink()
        a = self.fixture('a', [1,0]); b = self.fixture('b', [1,0], opponent='other')
        with self.assertRaises(ValueError): compare(a,'a',b,'b')

    def test_explicit_policy_owned_mode_permits_only_candidate_army_changes(self):
        a = self.fixture('a', [1,0], mode='policy-owned')
        b = self.fixture('b', [1,0], mode='policy-owned', own=self.alternative)
        self.assertEqual(compare(a,'a',b,'b')['summary']['paired_cohort_effect_bounds'], [0,0])
        with sqlite3.connect(b) as db:
            db.execute('UPDATE games SET blue_setup=? WHERE red=?',(self.alternative,'b'))
            db.execute('UPDATE games SET red_setup=? WHERE blue=?',(self.alternative,'b'))
        with self.assertRaises(ValueError): compare(a,'a',b,'b')

    def test_rotated_comparison_permits_own_treatment_and_matches_dos_per_orientation(self):
        mode='policy-owned-rotated-v1'
        a=self.fixture('a',[None,1],mode=mode)
        b=self.fixture('b',[0,None],mode=mode,own=self.alternative)
        result=compare(a,'a',b,'b')
        self.assertEqual(result['summary']['paired_cohort_effect_bounds'],[0,1])
        with sqlite3.connect(b) as db:
            # Both strings are valid armies, but raw unreflected red DOS is wrong.
            db.execute('UPDATE games SET red_setup=? WHERE blue=?',(self.enemy,'b'))
        with self.assertRaises(ValueError):compare(a,'a',b,'b')

    def test_incomplete_planned_pairs_are_not_silently_dropped_and_files_read_only(self):
        a = self.fixture('a', [1,0]); b = self.fixture('b', [1,0])
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (a,b)]
        compare(a,'a',b,'b')
        self.assertEqual(before,[hashlib.sha256(path.read_bytes()).hexdigest() for path in (a,b)])
        with sqlite3.connect(b) as db: db.execute('DELETE FROM games WHERE id=2')
        with self.assertRaises(ValueError): compare(a,'a',b,'b')

    def test_exact_direction_diagnostic_ignores_ties_and_is_not_mean_test(self):
        a = self.fixture('a', [0,0]*5+[.5,.5]); b = self.fixture('b', [1,1]*5+[.5,.5])
        diagnostic = compare(a,'a',b,'b')['summary']['complete_case_direction_diagnostic']
        self.assertEqual((diagnostic['positive_pairs'],diagnostic['negative_pairs'],diagnostic['zero_pairs']), (0,5,1))
        self.assertEqual(diagnostic['exact_two_sided_binomial_sign_p'], .0625)
        self.assertIn('Not a test of the mean',diagnostic['interpretation'])


if __name__ == '__main__':
    unittest.main()
