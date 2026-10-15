"""Exact public-evidence tests for the fixed DOS opening mixture."""
from collections import Counter
from fractions import Fraction
import itertools
import math
import random
import unittest
from campaign_template_beliefs import (TEMPLATES,TemplateMixtureBeliefs,background_log_evidence,component_posterior)
from feldmarschall import COUNTS,GLYPHS,setup_squares,valid_setup

OWN=''.join(g*n for g,n in zip(GLYPHS,COUNTS))

def model(army=0):
    result=TemplateMixtureBeliefs();result.observe(['new',('red','blue')[army]]);result.observe(['setup',OWN]);return result


def public_inputs(m):
    cells=[255]*100;histories={}
    for sq,(owner,origin) in m.tokens.items():
        known=m.known.get((owner,origin));moved=(owner,origin) in m.moved
        cells[sq]=(owner*16)|(32 if known is not None and owner!=m.army else 0)|(64 if moved else 0)|(known if known is not None else 12)
        if owner!=m.army and known is None:
            history=[0]*11;history[2]=setup_squares(owner)[origin];history[-1]=1023 if moved else 4095
            histories[sq]=history
    return cells,list(m.lost),histories


class TemplateBeliefs(unittest.TestCase):
    def check_marginals(self,m):
        cells,lost,h=public_inputs(m);marginals,remaining=m.rank_marginals(cells,m.army,lost,h)
        self.assertEqual(set(marginals),set(h))
        for sq,row in marginals.items():
            self.assertAlmostEqual(sum(row),1.,places=12)
            self.assertTrue(all(v>=0 for v in row))
            self.assertTrue(all(not v or h[sq][-1]&(1<<r) for r,v in enumerate(row)))
        for rank in range(12):self.assertAlmostEqual(sum(row[rank] for row in marginals.values()),remaining[rank],places=11)
    def test_initial_eight_templates_and_reflections(self):
        self.assertEqual(len(TEMPLATES),8)
        for i in range(0,8,2):
            self.assertTrue(valid_setup(TEMPLATES[i]))
            self.assertEqual(''.join(TEMPLATES[i][r:r+10][::-1] for r in range(0,40,10)),TEMPLATES[i+1])
        m=model();weights,report=m.posterior()
        for value in weights[:-1]:self.assertAlmostEqual(value,.1)
        self.assertAlmostEqual(report['background_probability'],.2)
        self.check_marginals(m)
    def test_toy_exact_enumeration(self):
        counts=(1,1,1);known={0:0};moved={1}
        worlds=list(itertools.permutations(range(3)))
        eligible=[w for w in worlds if w[0]==0 and w[1]<2]
        self.assertEqual(Fraction(len(eligible),len(worlds)),Fraction(1,6))
        self.assertAlmostEqual(math.exp(background_log_evidence(known,moved,counts,2)),1/6)
        probabilities,_=component_posterior([(0,1,2),(1,0,2)],known,moved,counts,2)
        self.assertAlmostEqual(probabilities[0],12/13)
        self.assertEqual(probabilities[1],0)
        self.assertAlmostEqual(probabilities[-1],1/13)
    def test_movement_likelihood_and_marginals(self):
        m=model();m.observe(['moved','a4','a5']);m.observe(['moved','a7','a6'])
        weights,report=m.posterior();self.assertAlmostEqual(math.exp(report['background_log_evidence']),33/40)
        self.assertAlmostEqual(weights[-1],(.2*33/40)/(.8+.2*33/40))
        self.check_marginals(m)
    def test_captured_public_revelation_retained(self):
        m=model();m.observe(['moved','a4','a5']);m.observe(['moved','a7','a6']);m.observe(['battle','a5','a6','1','4'])
        self.assertEqual(m.known[1,0],3);self.assertEqual(m.lost[3],1)
        self.assertNotIn((1,0),m.tokens.values())
        weights,report=m.posterior()
        self.assertTrue(any(v==0 for v in weights[:-1]));self.assertAlmostEqual(math.exp(report['background_log_evidence']),COUNTS[3]/40)
        for i,w in enumerate(weights[:-1]):self.assertEqual(w>0,TEMPLATES[i][0]=='4')
        self.check_marginals(m)
    def test_background_fallback_and_impossible_evidence(self):
        m=model();m.known[1,0]=11
        weights,_=m.posterior();self.assertEqual(weights,[0.]*8+[1.])
        self.check_marginals(m)
        with self.assertRaises(ValueError):component_posterior(m.templates,{0:11,1:11},set())
    def test_count_masks_and_private_nibble_invariance_both_armies(self):
        for army in (0,1):
            m=model(army);cells,lost,h=public_inputs(m)
            original=m.sample_worlds(cells,lost,h,random.Random(83519),army,80)
            for world,weight in original:
                self.assertEqual(weight,1.)
                self.assertEqual(Counter(c&15 for c in world if c<254 and bool(c&16)!=bool(army)),Counter({r:n for r,n in enumerate(COUNTS)}))
            reference=m.rank_marginals(cells,army,lost,h)
            for rank in range(12):
                altered=[(c&240)|rank if sq in h else c for sq,c in enumerate(cells)]
                self.assertEqual(m.sample_worlds(altered,lost,h,random.Random(83519),army,80),original)
                self.assertEqual(m.rank_marginals(altered,army,lost,h),reference)
    def test_moved_background_count_uniformity(self):
        m=model();m.observe(['moved','a4','a5']);m.observe(['moved','a7','a6']);cells,lost,h=public_inputs(m)
        # Force a public non-template clue at another original identity.
        m.known[1,1]=0;cells[31]=(cells[31]&240)|32;h.pop(31)
        # All remaining templates have non-Marshal at origin1.
        self.assertEqual(m.posterior()[0][-1],1.)
        for world,weight in m.sample_worlds(cells,lost,h,random.Random(1990),0,200):
            self.assertLess(world[40]&15,10)
            counts=Counter(c&15 for c in world if c<254 and c&16)
            self.assertEqual(counts,Counter({r:n for r,n in enumerate(COUNTS)}))
        self.check_marginals(m)
    def test_opponent_setup_rejected_seed_ignored(self):
        m=model();before=m.posterior();m.observe(['seed','1990']);self.assertEqual(m.posterior(),before)
        with self.assertRaises(ValueError):m.observe(['opponent-setup',TEMPLATES[0]])
        with self.assertRaises(ValueError):m.observe(['rules','1'])

import test_campaign_joint_beliefs as joint_fixture

class RealPublicHistory(joint_fixture.PublicHistoryTests):
    def initialize(self,army):
        from feldmarschall import Engine
        import shlex
        m=TemplateMixtureBeliefs();observer=Engine(shlex.quote(str(self.observer)))
        for line in ('new '+('red','blue')[army],'rules 0','setup '+self.game[('red_setup','blue_setup')[army]]):
            m.observe(line.split());observer.send(line)
        return m,observer

    def test_real_history_exact_marginal_inventory(self):
        from test_information_parent_parity import public_events
        for army in (0,1):
            m,observer=self.initialize(army)
            try:
                events=public_events(self.game,self.states)
                for ply in range(self.death+2):
                    if ply%20==0 or ply==self.death+1:
                        cells,lost,h=self.root(m,observer,army)
                        marginals,remaining=m.rank_marginals(cells,army,lost,h)
                        for row in marginals.values():self.assertAlmostEqual(sum(row),1.,places=11)
                        for rank in range(12):self.assertAlmostEqual(sum(row[rank] for row in marginals.values()),remaining[rank],places=10)
                    if ply<=self.death:m.observe(events[ply].split());observer.send(events[ply])
            finally:observer.close()

if __name__=='__main__':unittest.main()
