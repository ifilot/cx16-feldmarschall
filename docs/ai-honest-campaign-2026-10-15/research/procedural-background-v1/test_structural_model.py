"""Analytic evidence/marginals versus exhaustive small inventories and source facts."""
import itertools
import json
import math
from pathlib import Path
import unittest
from structural_model import ROOT,Geometry,StructuralModel,source_geometries,fit_row_odds,elementary
from campaign_template_beliefs import background_log_evidence
from feldmarschall import GLYPHS


class StructuralTests(unittest.TestCase):
    def test_weighted_partition(self):
        weights=[.3,2.,1.,4.]
        for k in range(6):
            exact=sum(math.prod(weights[i]for i in subset)for subset in itertools.combinations(range(4),k))
            self.assertAlmostEqual(elementary(weights,k),exact)

    def test_uniform_reduces_to_existing_exact_background_and_enumeration(self):
        counts=[1,1,1,1];worlds=list(itertools.permutations(range(4)))
        model=StructuralModel(counts,[Geometry(s,frozenset(),frozenset(),1.)for s in range(4)])
        for known_slots in((),(0,),(0,1)):
            for ranks in itertools.product(range(4),repeat=len(known_slots)):
                known=dict(zip(known_slots,ranks))
                for bits in range(16):
                    moved={s for s in range(4)if bits>>s&1}
                    legal=[w for w in worlds if all(w[o]==r for o,r in known.items())and all(w[o]<2 for o in moved)]
                    result=model.predict(known,moved)
                    log_exact=background_log_evidence(known,moved,counts=counts,mobile_types=2)
                    self.assertEqual(math.isfinite(result['log_evidence']),bool(legal))
                    if not legal:continue
                    self.assertAlmostEqual(result['log_evidence'],math.log(len(legal)/len(worlds)))
                    self.assertAlmostEqual(result['log_evidence'],log_exact)
                    for s in range(4):
                        self.assertAlmostEqual(result['flag'][s],sum(w[s]==3 for w in legal)/len(legal))
                        self.assertAlmostEqual(result['bomb'][s],sum(w[s]==2 for w in legal)/len(legal))

    def test_weighted_structural_geometry_matches_enumeration(self):
        counts=[2,1,2,1];weights=[1.,.4,2.,.8,3.,.5]
        geometry=Geometry(5,frozenset({4}),frozenset({0}),1.)
        model=StructuralModel(counts,[geometry],weights)
        words=set(itertools.permutations([0,0,1,2,2,3]));weighted=[]
        for word in words:
            if word[5]!=3 or word[4]!=2 or word[0]>=2:continue
            weight=math.prod(weights[s]for s,r in enumerate(word)if r==2 and s!=4)
            weighted.append((word,weight))
        total=sum(w for _,w in weighted)
        for known,moved in[({},set()),({1:2},{0}),({0:0,2:1},{3}),({4:0},set())]:
            selected=[(word,w)for word,w in weighted if all(word[o]==r for o,r in known.items())and all(word[o]<2 for o in moved)]
            result=model.predict(known,moved)
            if not selected:self.assertFalse(math.isfinite(result['log_evidence']));continue
            mass=sum(w for _,w in selected)
            self.assertAlmostEqual(math.exp(result['log_evidence']),mass/total)
            for s in range(6):self.assertAlmostEqual(result['bomb'][s],sum(w for word,w in selected if word[s]==2)/mass)

    def test_twelve_source_shapes_and_original_procedural_guard_facts(self):
        geometries=source_geometries();self.assertEqual(len(geometries),12)
        self.assertAlmostEqual(sum(g.prior for g in geometries),1.)
        source=ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-action-identification-v3/generation-evidence.json'
        armies=[[GLYPHS.index(g)for g in row['setup']]for row in json.loads(source.read_text())['selected']]
        # Historical data used ONLY to check source-derived structure; no scores,
        # row odds, parameter choice or study fit uses these armies.
        for ranks in armies:
            candidates=[g for g in geometries if ranks[g.flag]==11 and all(ranks[s]==10 for s in g.bombs)and all(ranks[s]<10 for s in g.mobiles)]
            self.assertEqual(len(candidates),1)
            known={s:ranks[s]for s in range(0,40,5)}
            moved={s for s,r in enumerate(ranks)if r<10 and s%3==0}
            result=StructuralModel().predict(known,moved)
            self.assertTrue(math.isfinite(result['log_evidence']))
            self.assertGreater(result['flag'][ranks.index(11)],0.)

    def test_exact_classic_origin_inventory_and_no_particle_collapse(self):
        model=StructuralModel(weights=[.1]*10+[1.]*30)
        for known,moved in[({},set()),({0:8,10:7},{1,2,3}),({39:11},{0,1,2})]:
            result=model.predict(known,moved)
            self.assertTrue(math.isfinite(result['log_evidence']))
            self.assertAlmostEqual(sum(result['flag']),1.)
            self.assertAlmostEqual(sum(result['bomb']),6.)


if __name__=='__main__':unittest.main()
