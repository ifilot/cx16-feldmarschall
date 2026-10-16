import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'tools'))
from new_campaign_divergence import record,summarize


def game(policy='baseline',side='red',identity=1):
    return dict(id=identity,pair_id=1,family='fixture',seed=12,
        red=policy if side=='red' else 'opponent',blue=policy if side=='blue' else 'opponent',
        red_setup='army-red',blue_setup='army-blue',result='red',reason='fixture',
        moves=[(60,50),(30,40),(50,51)])


class DivergenceContracts(unittest.TestCase):
    def pair(self,**changes):
        a=game();b=game('candidate');b.update(changes)
        return record(a,'baseline',b,'candidate')

    def test_identical_trace(self):
        r=self.pair();self.assertTrue(r['same_moves']);self.assertIsNone(r['first_different_move_ply'])

    def test_first_difference_counts_once_and_identifies_actor(self):
        r=self.pair(moves=[(60,50),(30,40),(50,52),(40,41),(52,53)])
        self.assertEqual(r['first_different_move_ply'],3)
        self.assertEqual(r['first_different_move_actor'],'candidate')
        self.assertEqual(r['common_prefix_plies'],2)

    def test_unequal_armies_rejected(self):
        with self.assertRaisesRegex(ValueError,'Own armies differ'):self.pair(red_setup='other')
        with self.assertRaisesRegex(ValueError,'opponent army'):self.pair(blue_setup='other')

    def test_error_extension_is_not_observed_different_choice(self):
        a=game();a.update(result='error',moves=[(60,50)])
        b=game('candidate')
        r=record(a,'baseline',b,'candidate')
        self.assertEqual(r['error_prefix_kind'],'one saved trace extends the other error prefix')
        self.assertIsNone(r['first_different_move_ply'])
        self.assertIsNone(r['baseline_score'])

    def test_tied_pair_separate_from_identical_trajectories(self):
        a=game();b=game('candidate');b['moves'][-1]=(50,52)
        red=record(a,'baseline',b,'candidate')
        blue=record(game(side='blue',identity=2),'baseline',game('candidate',side='blue',identity=2),'candidate')
        s=summarize([red,blue])
        self.assertEqual(s['paired_score_directions']['tied'],1)
        self.assertEqual(s['complete_game_trajectories']['different_moves'],1)
        self.assertEqual(s['complete_game_trajectories']['same_outcome_despite_different_moves'],1)

    def test_error_pairs_stay_unscored(self):
        red=self.pair(result='error')
        blue=record(game(side='blue',identity=2),'baseline',game('candidate',side='blue',identity=2),'candidate')
        s=summarize([red,blue])
        self.assertEqual(s['paired_score_directions']['unscored_error_pair'],1)
        self.assertIsNone(s['complete_case_paired_effect'])


if __name__=='__main__':unittest.main()
