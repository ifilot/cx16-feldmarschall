"""Boundary checks for the descriptive conversion analysis."""
from types import SimpleNamespace
import unittest

from analyze_template_conversion import flag_prediction, optimistic_miner_distance
from campaign_template_beliefs import TemplateMixtureBeliefs, TEMPLATES


class ConversionTests(unittest.TestCase):
    def model(self):
        model = TemplateMixtureBeliefs()
        model.observe(['new', 'red'])
        model.observe(['setup', TEMPLATES[0]])
        return model

    def test_public_flag_disclosure_overrides_prior_and_captured_identity_persists(self):
        model = self.model()
        model.known[1, 37] = 11
        probabilities, disclosed = flag_prediction(model)
        self.assertTrue(disclosed)
        self.assertEqual(probabilities, [float(o == 37) for o in range(40)])
        del model.tokens[next(sq for sq, token in model.tokens.items() if token == (1, 37))]
        self.assertEqual(flag_prediction(model), (probabilities, True))

    def test_moved_origin_is_never_flag_and_all_mass_is_conserved(self):
        model = self.model()
        before, _ = flag_prediction(model)
        origin = max(range(40), key=lambda o: before[o])
        model.moved.add((1, origin))
        after, disclosed = flag_prediction(model)
        self.assertFalse(disclosed)
        self.assertEqual(after[origin], 0.)
        self.assertAlmostEqual(sum(after), 1.)

    def test_path_bound_respects_own_immobiles_but_ignores_mobile_defenders(self):
        own = {(0, 0): 7, (0, 1): 10, (0, 2): 10, (0, 3): 10, (0, 4): 11}
        model = SimpleNamespace(army=0, known=own.copy(),
                                tokens={25: (0, 0), 15: (0, 1), 24: (0, 2), 26: (0, 3), 35: (0, 4)})
        self.assertEqual(optimistic_miner_distance(model, 0), (1, None))
        del model.tokens[15]
        self.assertIsNotNone(optimistic_miner_distance(model, 0)[1])
        expected = optimistic_miner_distance(model, 0)
        model.tokens[15] = (1, 5)
        model.known[1, 5] = 0
        self.assertEqual(optimistic_miner_distance(model, 0), expected)
        del model.tokens[25]
        self.assertEqual(optimistic_miner_distance(model, 0), (0, None))


if __name__ == '__main__':
    unittest.main()
