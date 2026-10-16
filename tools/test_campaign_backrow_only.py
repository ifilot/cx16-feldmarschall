"""The minimal source prior must not retain any template inference."""
import unittest

from ai_registry import ROOT
from campaign_procedural_beliefs import ProceduralTemplateBeliefs
from campaign_template_beliefs import TEMPLATES

MODEL = ROOT/'ai/models/dos-backrow-only-v1.json'


class BackrowOnlyTests(unittest.TestCase):
    def model(self):
        model = ProceduralTemplateBeliefs.load(MODEL)
        model.observe(['new', 'red'])
        model.observe(['setup', TEMPLATES[0]])
        return model

    def test_template_weights_stay_zero_and_template_contents_are_irrelevant(self):
        model = self.model()
        before, _ = model.posterior()
        self.assertEqual(before[:8], [0.]*8)
        self.assertAlmostEqual(before[8], .99)
        self.assertAlmostEqual(before[9], .01)
        source = model.structural.predict({}, set())
        self.assertTrue(all(source['flag'][i] == 0 for i in range(30)))
        model.templates = tuple(tuple(reversed(t)) for t in model.templates)
        model._cache_key = None
        self.assertEqual(model.posterior()[0], before)

    def test_off_backrow_flag_keeps_positive_uniform_support(self):
        model = self.model()
        model.known[1, 4] = 11
        weights, report = model.posterior()
        self.assertEqual(weights[:9], [0.]*9)
        self.assertEqual(weights[9], 1.)
        self.assertEqual(report['template_mass'], 0.)

    def test_bool_is_not_a_template_mass_control(self):
        import json
        parameters = json.loads(MODEL.read_text())
        parameters['template_mass'] = False
        with self.assertRaises(ValueError):
            ProceduralTemplateBeliefs(parameters)


if __name__ == '__main__':
    unittest.main()
