"""Check exact experiment diagnostics and conservative static route semantics."""
import unittest
from analyze_campaign_template_identification import entropy,experiment,route
from analyze_campaign_template_predictions import predict_public
from feldmarschall import Position

class IdentificationAudit(unittest.TestCase):
    def test_global_flag_joint_matches_existing_unchanged_posterior(self):
        prior=predict_public([])['template']['flag']
        for origin in range(10):
            diagnostic=experiment(origin);expected_entropy=0.;expected_guess=0.
            self.assertAlmostEqual(sum(diagnostic['observed_rank_probabilities']),1.)
            for rank,p in enumerate(diagnostic['observed_rank_probabilities']):
                posterior=predict_public([(origin,rank)])['template']['flag']
                expected_entropy+=p*entropy(posterior);expected_guess+=p*max(posterior)
            self.assertAlmostEqual(diagnostic['expected_flag_information_bits'],entropy(prior)-expected_entropy,places=11)
            self.assertAlmostEqual(diagnostic['flag_identification_probability_gain'],expected_guess-max(prior),places=12)
    def test_entropy_and_probability_gain_nonnegative(self):
        for origin in range(10):
            diagnostic=experiment(origin)
            self.assertGreaterEqual(diagnostic['expected_flag_information_bits'],0.)
            self.assertGreaterEqual(diagnostic['flag_identification_probability_gain'],0.)
            self.assertAlmostEqual(diagnostic['expected_scout_death_probability'],.99)
    def test_miner_static_route_respects_own_blockers_and_stronger_enemy(self):
        p=Position();p.cells[60]=[0,7,False,False];p.cells[50]=[1,10,False,False];p.cells[40]=[1,11,False,False]
        self.assertEqual(route(p,60,40,True),2)
        p.cells[50]=[1,1,True,True]
        self.assertEqual(route(p,60,40,True),4) # Must go around the superior piece.
        p.cells[30]=[1,10,False,False];p.cells[41]=[0,10,False,False];p.cells[50]=[0,10,False,False]
        # Three blocked sides, remaining adjacentBomb is clearable.
        self.assertIsNotNone(route(p,60,40,True))

if __name__=='__main__':unittest.main()
