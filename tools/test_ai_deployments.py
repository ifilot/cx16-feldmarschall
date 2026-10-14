"""Validate legal genetic operators, diversity, pairing and setup-only comparisons."""
import random
import unittest

from feldmarschall import presets, valid_setup
from optimize_ai_deployments import mutate, separation, diverse, trials, delta


class DeploymentSearch(unittest.TestCase):
    def test_mutations_and_diversity(self):
        rng=random.Random(20261014);layout=presets()[0][1];layouts={layout}
        for _ in range(1000):
            layout=mutate(layout,rng);self.assertTrue(valid_setup(layout));layouts.add(layout)
        selected=diverse([(layout,1) for layout in sorted(layouts)],3,8)
        self.assertEqual(len(selected),3)
        self.assertTrue(all(separation(a,b)>=8 for i,a in enumerate(selected) for b in selected[i+1:]))

    def test_holdout_trials_and_side_pair_differences(self):
        training=trials(41261014,1,['v020','planned'])
        validation=trials(42261014,1,['v020','planned'])
        self.assertEqual(training,trials(41261014,1,['v020','planned']))
        self.assertNotEqual(training,validation)
        self.assertTrue(all(valid_setup(case['opponent_setup']) and valid_setup(case['random_control']) for case in validation))
        games=[]
        for case in range(4):
            for setup in ['candidate','control']:
                for blue in (False,True):
                    games.append({'setup_id':setup,'case':case,'candidate_blue':blue,
                                  'group':'fixture','round':case,
                                  'winner':'current' if setup=='candidate' else 'opponent'})
        comparison=delta(games,'candidate','control')
        self.assertEqual(comparison['score_difference'],1)
        self.assertEqual(comparison['paired_bootstrap_95'],[1,1])
        self.assertEqual(comparison['deployment_blocks'],4)


if __name__=='__main__':unittest.main()
