"""Mechanism tests for honest, count-consistent Latin-hypercube worlds."""
import itertools
import math
import random
import unittest

from calibrated_beliefs import BeliefModel
from campaign_sampling import StratifiedSampler, UniformSampler, _LatinBatch
from feldmarschall import COUNTS
from test_calibrated_beliefs import document, small_position
from train_ai_student import sample_world


class SamplingTests(unittest.TestCase):
    def test_uniform_ablation_keeps_exact_original_worlds_and_rng(self):
        cells,lost,histories=small_position()
        histories[0][8]=8 # deliberately nonconstant behavioral likelihood
        baseline_rng=random.Random(319);uniform_rng=random.Random(319)
        original=[sample_world(cells,lost,histories,baseline_rng,0) for _ in range(64)]
        ablated=UniformSampler().sample_worlds(cells,lost,histories,uniform_rng,0,64)
        self.assertEqual([world for world,_ in original],[world for world,_ in ablated])
        self.assertEqual([weight for _,weight in ablated],[1.0]*64)
        self.assertGreater(len(set(weight for _,weight in original)),1)
        self.assertEqual(baseline_rng.getstate(),uniform_rng.getstate())

    def test_uniform_ablation_keeps_masks_counts_and_ignores_hidden_nibbles(self):
        cells,lost,histories=small_position()
        histories[0][-1]=(1<<5)|(1<<8)
        histories[1][-1]=(1<<8)|(1<<11)
        histories[2][-1]=(1<<5)|(1<<11)
        mutated=cells[:]
        for sq in histories:mutated[sq]=16|sq
        sampler=UniformSampler()
        draws=sampler.sample_worlds(cells,lost,histories,random.Random(320),0,64)
        self.assertEqual(draws,sampler.sample_worlds(mutated,lost,histories,random.Random(320),0,64))
        for world,weight in draws:
            self.assertEqual(weight,1.)
            self.assertEqual(sorted(world[sq]&15 for sq in histories),[5,8,11])
            for sq in histories:self.assertTrue(histories[sq][-1] & (1<<(world[sq]&15)))

    def test_every_column_visits_every_stratum(self):
        batch = _LatinBatch(random.Random(1201), 8)
        for column in range(50):
            self.assertEqual(sorted(int(batch.coordinate(row,column)*8) for row in range(8)), list(range(8)))

    def test_uniform_assignment_marginals_match_enumeration(self):
        cells,lost,histories = small_position()
        totals = dict.fromkeys(itertools.permutations((5,8,11)), 0)
        rng = random.Random(1202)
        for _ in range(3000):
            for world,weight in StratifiedSampler().sample_worlds(cells,lost,histories,rng,0,8):
                totals[tuple(world[sq]&15 for sq in histories)] += weight
        self.assertEqual(len(totals),6)
        for count in totals.values():self.assertAlmostEqual(count/sum(totals.values()),1/6,delta=.01)

    def test_known_own_ranks_masks_counts_and_input_preserved(self):
        cells,lost,histories = small_position()
        histories[0][-1]=(1<<5)|(1<<8)
        histories[1][-1]=(1<<8)|(1<<11)
        histories[2][-1]=(1<<5)|(1<<11)
        cells[3]=16|32|0;lost[0]-=1
        cells[90]=9
        original=cells[:]
        draws=StratifiedSampler().sample_worlds(cells,lost,histories,random.Random(1203),0,256)
        for world,weight in draws:
            self.assertGreater(weight,0)
            self.assertEqual(world[3],cells[3]);self.assertEqual(world[90],9)
            self.assertEqual(sorted(world[sq]&15 for sq in histories),[5,8,11])
            for sq in histories:self.assertTrue(histories[sq][-1] & (1<<(world[sq]&15)))
        self.assertEqual(cells,original)

    def test_hidden_physical_nibbles_do_not_affect_worlds(self):
        cells,lost,histories=small_position()
        other=cells[:]
        for sq in histories:other[sq]=16|sq
        for sampler in (StratifiedSampler(),StratifiedSampler(BeliefModel(document()))):
            self.assertEqual(sampler.sample_worlds(cells,lost,histories,random.Random(1204),0,32),
                             sampler.sample_worlds(other,lost,histories,random.Random(1204),0,32))

    def test_learned_importance_weights_recover_exact_posterior(self):
        model=BeliefModel(document())
        matrix={0:{5:5.,8:1.,11:.2},1:{5:.4,8:3.,11:1.},2:{5:2.,8:.2,11:4.}}
        model.likelihoods=lambda cells,army,sq,h:[matrix[sq].get(r,1.) for r in range(12)]
        cells,lost,histories=small_position()
        exact={ranks:math.prod(matrix[sq][rank] for sq,rank in enumerate(ranks))
               for ranks in itertools.permutations((5,8,11))}
        # Normalize jointly across one large batch so per-batch weight scaling
        # cannot change a concatenated importance estimate.
        draws=StratifiedSampler(model).sample_worlds(cells,lost,histories,random.Random(1205),0,24000)
        actual=dict.fromkeys(exact,0.)
        for world,weight in draws:actual[tuple(world[sq]&15 for sq in histories)]+=weight
        for ranks in exact:self.assertAlmostEqual(actual[ranks]/sum(actual.values()),exact[ranks]/sum(exact.values()),delta=.009)

    def test_rank_marginal_variance_reduction_at_same_world_budget(self):
        cells,lost,histories=small_position()
        iid=[];latin=[]
        for seed in range(1200):
            rng=random.Random(seed)
            iid.append(sum((sample_world(cells,lost,histories,rng,0)[0][0]&15)==11 for _ in range(8))/8)
            worlds=StratifiedSampler().sample_worlds(cells,lost,histories,random.Random(seed),0,8)
            latin.append(sum((world[0]&15)==11 for world,_ in worlds)/8)
        mse=lambda values:sum((v-1/3)**2 for v in values)/len(values)
        self.assertLess(mse(latin),mse(iid)*.15)

    def test_invalid_budget_rejected(self):
        cells,lost,histories=small_position()
        for n in (0,-1,True,1.5):
            with self.assertRaises(ValueError):StratifiedSampler().sample_worlds(cells,lost,histories,random.Random(0),0,n)


if __name__=='__main__':unittest.main()
