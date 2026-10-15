"""Check offline predictive metric definitions and disclosure-only API."""
import math
import unittest
from analyze_campaign_template_predictions import predict_public,scores
from campaign_template_beliefs import TEMPLATES
from feldmarschall import GLYPHS

class PredictionAudit(unittest.TestCase):
    def test_uniform_proper_score_definitions(self):
        truth=[GLYPHS.index(g) for g in TEMPLATES[0]]
        prediction=dict(flag=[1/40]*40,bomb=[6/40]*40)
        metrics=scores(prediction,truth)
        self.assertAlmostEqual(metrics['flag_logloss'],math.log(40))
        self.assertAlmostEqual(metrics['flag_brier'],39/40)
        self.assertAlmostEqual(metrics['bomb_brier_per_original_slot'],.15*.85)
        self.assertAlmostEqual(metrics['flag_top_tie_adjusted_accuracy'],1/40)
    def test_perfect_probabilities_have_zero_proper_loss(self):
        truth=[GLYPHS.index(g) for g in TEMPLATES[0]]
        prediction=dict(flag=[float(r==11) for r in truth],bomb=[float(r==10) for r in truth])
        metrics=scores(prediction,truth)
        for key in ('flag_logloss','flag_brier','bomb_logloss_per_original_slot','bomb_brier_per_original_slot'):
            self.assertAlmostEqual(metrics[key],0.)
        self.assertEqual(metrics['flag_top_accuracy'],1.)
    def test_disclosure_order_cannot_change_prediction_and_inventory(self):
        truth=[GLYPHS.index(g) for g in TEMPLATES[0]]
        disclosed=[(o,r) for o,r in enumerate(truth) if r!=11][:10]
        first=predict_public(disclosed);second=predict_public(disclosed[::-1])
        first.pop('marginal_seconds');second.pop('marginal_seconds');self.assertEqual(first,second)
        for name in ('template','uniform'):
            self.assertAlmostEqual(sum(first[name]['flag']),1.)
            self.assertAlmostEqual(sum(first[name]['bomb']),6.)
            for origin,rank in disclosed:
                self.assertEqual(first[name]['flag'][origin],float(rank==11))
                self.assertEqual(first[name]['bomb'][origin],float(rank==10))

if __name__=='__main__':unittest.main()
