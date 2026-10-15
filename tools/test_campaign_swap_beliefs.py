"""Stationary-target and honest-mask tests for independent swap chains."""
import itertools
import math
import random
import unittest

from calibrated_beliefs import BeliefModel
from campaign_swap_beliefs import SwapBeliefs,rejuvenate
from test_calibrated_beliefs import document,small_position


def toy():
    cells,lost,histories=small_position()
    for history in histories.values():history[-1]=4095
    model=BeliefModel(document())
    matrix={0:{5:5.,8:1.,11:.2},1:{5:.4,8:3.,11:1.},2:{5:2.,8:.2,11:4.}}
    model.likelihoods=lambda cells,army,sq,h:[matrix[sq].get(rank,1.) for rank in range(12)]
    return cells,lost,histories,model,matrix


class SwapTests(unittest.TestCase):
    def test_kernel_detailed_balance_for_every_pair_of_enumerated_assignments(self):
        cells,lost,h,model,matrix=toy()
        states=list(itertools.permutations((5,8,11)))
        probability={state:math.prod(matrix[sq][rank] for sq,rank in enumerate(state)) for state in states}
        for first in states:
            for i in range(3):
                for j in range(3):
                    second=list(first);second[i],second[j]=second[j],second[i];second=tuple(second)
                    forward=min(1,probability[second]/probability[first])/9
                    reverse=min(1,probability[first]/probability[second])/9
                    self.assertAlmostEqual(probability[first]*forward,probability[second]*reverse,places=12)

    def test_independent_chain_endpoints_recover_exact_small_posterior(self):
        cells,lost,h,model,matrix=toy()
        exact={state:math.prod(matrix[sq][rank] for sq,rank in enumerate(state))
               for state in itertools.permutations((5,8,11))}
        draws=SwapBeliefs(model,sweeps=32).sample_worlds(cells,lost,h,random.Random(557),0,24000)
        count=dict.fromkeys(exact,0)
        for world,weight in draws:
            self.assertEqual(weight,1.)
            count[tuple(world[sq]&15 for sq in h)]+=1
        for state in exact:self.assertAlmostEqual(count[state]/len(draws),exact[state]/sum(exact.values()),delta=.009)

    def test_hidden_nibbles_known_ranks_and_inventory_unchanged(self):
        cells,lost,h,model,_=toy();cells[90]=9;cells[3]=16|32|0;lost[0]-=1
        mutated=cells[:]
        for sq in h:mutated[sq]=16|sq
        sampler=SwapBeliefs(model,4)
        draws=sampler.sample_worlds(cells,lost,h,random.Random(558),0,64)
        self.assertEqual(draws,sampler.sample_worlds(mutated,lost,h,random.Random(558),0,64))
        for world,weight in draws:
            self.assertEqual(world[90],9);self.assertEqual(world[3],cells[3])
            self.assertEqual(sorted(world[sq]&15 for sq in h),[5,8,11])
            for sq in h:self.assertTrue(h[sq][-1]&(1<<(world[sq]&15)))

    def test_public_moved_masks_and_disconnected_masks(self):
        cells,lost,h,model,_=toy();h[0][-1]=1023
        draws=SwapBeliefs(model,8).sample_worlds(cells,lost,h,random.Random(559),0,100)
        self.assertTrue(all(world[0]&15<10 for world,_ in draws))
        h[0][-1]=(1<<5)|(1<<8)
        with self.assertRaisesRegex(ValueError,'all-rank/moved'):SwapBeliefs(model,8).sample_worlds(cells,lost,h,random.Random(559),0,8)

    def test_zero_sweeps_uses_identical_independent_proposal_seeds(self):
        cells,lost,h,model,_=toy();sampler=SwapBeliefs(model,0)
        expected=[];rng=random.Random(560);slots,counts,likelihoods=model.prepare(cells,lost,h,0)
        for _ in range(8):
            chain=random.Random(rng.getrandbits(64));expected.append((model.draw(cells,h,chain,slots,counts,likelihoods)[0],1.))
        self.assertEqual(sampler.sample_worlds(cells,lost,h,random.Random(560),0,8),expected)
        self.assertEqual(sampler.last_report['attempted_swaps'],0)


if __name__=='__main__':unittest.main()
