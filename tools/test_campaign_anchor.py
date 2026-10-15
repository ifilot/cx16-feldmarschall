"""Legal-parent anchor algebra, clipping activation and historical parity."""
import json
import math
import random
import unittest

from ai_registry import ROOT
from campaign_anchor import choices

PARENT,OTHER=(60,50),(61,51)


class ParentAnchor(unittest.TestCase):
    def test_parent_zero_and_no_clipping_ranking_invariance(self):
        rng=random.Random(2391001)
        for _ in range(200):
            scores={PARENT:rng.randrange(-30,31),OTHER:rng.randrange(-30,31)}
            residual={PARENT:rng.randrange(-50,51),OTHER:rng.randrange(-50,51)}
            reference=rng.randrange(-50,51)
            totals={move:[value*8,0,reference*8] for move,value in residual.items()}
            result,correction,report=choices(scores,{},totals,[1]*8,PARENT)
            self.assertEqual(correction[PARENT],0)
            self.assertEqual(result[OTHER]-result[PARENT],
                scores[OTHER]+residual[OTHER]-reference-(scores[PARENT]+residual[PARENT]-reference))
            self.assertEqual(report['parent_anchor_saturated_actions'],0)

    def test_arbitrary_pass_offset_cannot_change_parent_anchored_scores(self):
        first=choices({PARENT:20,OTHER:10},{OTHER:4},
                      {PARENT:[20,3,70],OTHER:[30,8,70]},[1,2],PARENT)
        second=choices({PARENT:20,OTHER:10},{OTHER:4},
                       {PARENT:[20,3,-70000],OTHER:[30,8,-70000]},[1,2],PARENT)
        self.assertEqual(first[:2],second[:2])

    def test_clipping_anchor_can_restore_discrimination(self):
        scores={PARENT:10,OTHER:0}
        totals={PARENT:[1000,0,0],OTHER:[1020,0,0]}
        result,correction,report=choices(scores,{},totals,[1],PARENT)
        # Pass anchor clips both to+192, selecting parent. Legal anchor compares
        # the actual+20 difference instead, selecting the alternative.
        self.assertGreater(result[OTHER],result[PARENT])
        self.assertEqual(correction,{PARENT:0,OTHER:20})
        self.assertEqual(report['pass_anchor_saturated_actions'],2)

    def test_weights_and_capture_credits_enter_before_anchoring(self):
        result,correction,report=choices({PARENT:20,OTHER:10},{PARENT:5,OTHER:9},
            {PARENT:[120,60,40],OTHER:[240,80,40]},[1,3],PARENT)
        self.assertEqual(report['parent_residual'],20)
        self.assertEqual(correction[OTHER],29)
        self.assertEqual(result[OTHER],39)

    def test_extreme_difference_bounded_and_json_finite(self):
        result,correction,report=choices({PARENT:30000,OTHER:-10},{},
            {PARENT:[1000000,0,0],OTHER:[-1000000,0,0]},[1],PARENT)
        self.assertEqual(correction[OTHER],-192)
        self.assertGreater(result[PARENT],result[OTHER])
        json.dumps(report,allow_nan=False)

    def test_historical_140_root_mechanism_matches_helper_exactly(self):
        path=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon/parent-centering-mechanism.json'
        document=json.loads(path.read_text())
        changed=0
        for row in document['records']:
            parent=tuple(row['parent'])
            scores={tuple(v['move']):v['native_score'] for v in row['values']}
            credits={tuple(v['move']):v['credit'] for v in row['values']}
            # The retained residual is a sufficient statistic. Reconstitute
            # future-immediate so the helper must add the real capture credit.
            totals={tuple(v['move']):[v['residual']-v['credit'],0,row['reference']]
                    for v in row['values']}
            result,correction,report=choices(scores,credits,totals,[1],parent)
            for value in row['values']:
                self.assertAlmostEqual(result[tuple(value['move'])],value['centered'])
            selected=max(result,key=lambda move:(round(result[move],9),move==parent,-move[0],-move[1]))
            self.assertEqual(selected,tuple(row['selected_centered']))
            changed+=selected!=tuple(row['selected_original'])
        self.assertEqual(len(document['records']),140)
        self.assertEqual(changed,document['summary']['changed_decisions'])

    def test_invalid_inputs_rejected(self):
        for weights in ([],[0],[-1],[float('nan')],[float('inf')]):
            with self.assertRaises(ValueError):
                choices({PARENT:0},{},{PARENT:[0,0,0]},weights,PARENT)
        with self.assertRaises(ValueError):choices({PARENT:0},{},{OTHER:[0,0,0]},[1],PARENT)
        with self.assertRaises(ValueError):choices({PARENT:0},{},{PARENT:[0,math.inf,0]},[1],PARENT)
        with self.assertRaises(ValueError):
            choices({PARENT:0,OTHER:0},{},{PARENT:[0,0,1],OTHER:[0,0,2]},[1],PARENT)
        with self.assertRaises(ValueError):
            choices({PARENT:0},{},{PARENT:[1e308,0,0]},[1e-308],PARENT)


if __name__=='__main__':unittest.main()
