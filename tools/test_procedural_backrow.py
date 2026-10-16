"""Independently enumerate a small fixed-inventory Flag restriction model."""
import itertools
import math
import unittest

from analyze_procedural_backrow import BackrowBackground


class BackrowTests(unittest.TestCase):
    def test_evidence_and_marginals_match_all_small_armies(self):
        worlds = sorted(set(itertools.permutations([0, 0, 1, 2, 3])))
        prior = [w for w in worlds if w.index(3) in (3, 4)]
        model = BackrowBackground(counts=(2, 1, 1, 1), allowed=(3, 4))
        cases = set()
        for world in worlds:
            for size in range(3):
                for origins in itertools.combinations(range(5), size):
                    known = tuple((o, world[o]) for o in origins)
                    for moved in [(), *((o,) for o in range(5) if world[o] < 2)]:
                        cases.add((known, moved))
        for facts, moved in sorted(cases):
            known = dict(facts)
            compatible = [w for w in prior if all(w[o] == r for o, r in facts)
                          and all(w[o] < 2 for o in moved)]
            prediction = model.predict(known, moved)
            if not compatible:
                self.assertEqual(prediction['log_evidence'], -math.inf)
                continue
            self.assertAlmostEqual(math.exp(prediction['log_evidence']), len(compatible)/len(prior), places=12)
            for o in range(5):
                self.assertAlmostEqual(prediction['flag'][o], sum(w[o] == 3 for w in compatible)/len(compatible), places=12)
                self.assertAlmostEqual(prediction['bomb'][o], sum(w[o] == 2 for w in compatible)/len(compatible), places=12)
        self.assertGreater(len(cases), 500)


if __name__ == '__main__':
    unittest.main()
