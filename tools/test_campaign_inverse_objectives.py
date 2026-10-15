"""Causal public-action features, secrecy boundaries and unchanged base priors."""
import copy
import json
import random
import unittest

from ai_registry import ROOT
from calibrated_beliefs import BeliefModel
from campaign_inverse_objectives import ObjectiveMemory,ObjectiveBeliefs,FEATURE_SIZES,SCHEMA,step_bucket,DISTANCES
from feldmarschall import COUNTS,GLYPHS,LAKES,setup_squares
from test_calibrated_beliefs import small_position


def setup():
    values=list(''.join(g*n for g,n in zip(GLYPHS,COUNTS)))
    i=values.index('S');values[0],values[i]=values[i],values[0]
    return ''.join(values)


def board(memory):
    cells=[254 if sq in LAKES else 255 for sq in range(100)]
    for sq,token in memory.public.tokens.items():
        owner,_=token
        cells[sq]=16*owner|(memory.public.known[token] if owner==memory.public.army else 12)
    return cells


class InverseFeatureTests(unittest.TestCase):
    def test_last_spy_progress_uses_objective_at_that_action_not_future_position(self):
        memory=ObjectiveMemory();memory.observe(['new','red']);memory.observe(['setup',setup()])
        for event in ('moved a4 a5','moved b7 b6','moved e4 e5','moved a7 b7','moved a5 b5'):
            memory.observe(event.split())
        cells=board(memory);h=[31,0,30,31,16,1,0,12,12,12,1023]
        features=memory.features(cells,0,31,h)
        self.assertEqual(features[4],0) # away from the Spy at a5 when DOS moved
        self.assertEqual(DISTANCES[30][51]-DISTANCES[31][51],1) # future b5 would say toward
        self.assertEqual(features[2],2) # toward our stationary Flag at j1

    def test_enemy_concealed_nibbles_never_change_features(self):
        memory=ObjectiveMemory();memory.observe(['new','red']);memory.observe(['setup',setup()])
        cells=board(memory);other=cells[:]
        for sq in setup_squares(1):other[sq]=16|(sq%12)
        h=[30,0,30,30,16,0,0,12,12,12,4095]
        for mirrored in (False,True):
            self.assertEqual(memory.features(cells,0,30,h,mirrored),memory.features(other,0,30,h,mirrored))

    def test_new_reset_and_private_setup_rejection(self):
        memory=ObjectiveMemory();memory.observe(['new','red']);memory.observe(['setup',setup()])
        memory.observe(['moved','a4','a5']);memory.observe(['moved','a7','a6'])
        self.assertTrue(memory.last)
        with self.assertRaisesRegex(ValueError,'rejects opponent setup'):memory.observe(['opponent-setup',setup()])
        memory.observe(['new','blue']);self.assertEqual(memory.last,{})
        self.assertEqual(memory.public.known,{})

    def document(self,strength):
        return dict(schema=SCHEMA,feature_sizes=list(FEATURE_SIZES),
            base_document=json.loads((ROOT/'ai/models/public-history-beliefs-v1.json').read_text()),
            factor_strength=strength,selected_features=[0,1,2,3,4],
            extra_log_likelihood_ratios=[[[.2*(rank-4)]*size for size in FEATURE_SIZES] for rank in range(10)])

    def test_zero_factor_is_exact_frozen_base_sampler(self):
        cells,lost,h=small_position();base=BeliefModel(self.document(0)['base_document']);new=ObjectiveBeliefs(self.document(0))
        h[0][5]=1;h[0][-1]=1023
        self.assertEqual(base.sample_worlds(cells,lost,h,random.Random(128),0,64),
                         new.sample_worlds(cells,lost,h,random.Random(128),0,64))

    def test_factors_only_change_moved_mobile_likelihoods_and_keep_constraints(self):
        cells,lost,h=small_position();h[0][5]=1;h[0][-1]=1023
        model=ObjectiveBeliefs(self.document(1));base=BeliefModel(self.document(0)['base_document'])
        model.context={sq:(0,0,0,0,0) for sq in h}
        self.assertEqual(model.likelihoods(cells,0,1,h[1]),base.likelihoods(cells,0,1,h[1]))
        changed=model.likelihoods(cells,0,0,h[0]);original=base.likelihoods(cells,0,0,h[0])
        self.assertEqual(changed[10:],original[10:]);self.assertNotEqual(changed[:10],original[:10])
        for world,weight in model.sample_worlds(cells,lost,h,random.Random(129),0,64):
            self.assertEqual(sorted(world[sq]&15 for sq in h),[5,8,11])
            for sq in h:self.assertTrue(h[sq][-1]&(1<<(world[sq]&15)))


if __name__=='__main__':unittest.main()
