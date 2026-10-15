"""Posterior correctness, fair feature boundary and frozen transport checks."""
import contextlib
import copy
import io
import itertools
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from ai_registry import ROOT, build_policy, get_policy, receives_opponent_setup
from calibrated_beliefs import BeliefModel, FEATURE_SIZES, SCHEMA, features
from feldmarschall import COUNTS
from tournament import run
from tournament_store import Tournament, verify

POLICY = 'teacher-calibrated-beliefs-v1-normal'


def document():
    return dict(schema=SCHEMA, feature_sizes=list(FEATURE_SIZES), temperature=.5,
                log_likelihood_ratios=[[[[0.0]*n for n in FEATURE_SIZES] for _ in range(12)] for _ in range(2)])


def small_position():
    cells = [255]*100
    histories = {}
    for sq in (0,1,2):
        cells[sq] = 16|12
        histories[sq] = [sq,sq,sq,sq,16,0,0,12,12,12,(1<<5)|(1<<8)|(1<<11)]
    lost = COUNTS[:]
    for rank in (5,8,11): lost[rank] -= 1
    return cells,lost,histories


class PosteriorTests(unittest.TestCase):
    def test_importance_correction_matches_enumerated_posterior(self):
        model = BeliefModel(document())
        # Deliberately asymmetric, finite likelihoods; constrained assignment
        # probabilities differ substantially from greedy weighted placement.
        matrix = {0:{5:5.,8:1.,11:.2}, 1:{5:.4,8:3.,11:1.}, 2:{5:2.,8:.2,11:4.}}
        model.likelihoods = lambda cells,army,sq,h: [matrix[sq].get(r,1.) for r in range(12)]
        cells,lost,histories = small_position()
        exact = {}
        for ranks in itertools.permutations((5,8,11)):
            exact[ranks] = math.prod(matrix[sq][rank] for sq,rank in enumerate(ranks))
        normalizer = sum(exact.values())
        exact = {key:value/normalizer for key,value in exact.items()}
        samples = model.sample_worlds(cells,lost,histories,random.Random(407),0,40000)
        observed = dict.fromkeys(exact,0.)
        raw = dict.fromkeys(exact,0)
        for world,weight in samples:
            key=tuple(world[sq]&15 for sq in range(3))
            observed[key]+=weight
            raw[key]+=1
        total=sum(observed.values())
        for key,target in exact.items():self.assertAlmostEqual(observed[key]/total,target,delta=.009)
        self.assertGreater(max(abs(raw[k]/len(samples)-exact[k]) for k in exact),.03)

    def test_narrow_masks_correct_after_dead_end_rejection(self):
        model=BeliefModel(document())
        cells,lost,histories=small_position()
        histories[0][-1]=(1<<5)|(1<<8)
        histories[1][-1]=(1<<8)|(1<<11)
        histories[2][-1]=(1<<5)|(1<<11)
        samples=model.sample_worlds(cells,lost,histories,random.Random(12),0,12000)
        totals={}
        for world,weight in samples:
            key=tuple(world[sq]&15 for sq in range(3))
            totals[key]=totals.get(key,0)+weight
            self.assertEqual(sorted(key),[5,8,11])
            for sq in range(3):self.assertTrue(histories[sq][-1] & (1<<key[sq]))
        self.assertEqual(len(totals),2)
        self.assertAlmostEqual(next(iter(totals.values()))/sum(totals.values()),.5,delta=.02)

    def test_concealed_nibbles_never_change_features_or_drawn_ranks(self):
        cells,lost,histories=small_position()
        model=BeliefModel(document())
        mutated=cells[:]
        for sq in histories:mutated[sq]=16|sq
        self.assertEqual(model.prepare(cells,lost,histories,0),model.prepare(mutated,lost,histories,0))
        self.assertEqual(model.sample_worlds(cells,lost,histories,random.Random(5),0,16),
                         model.sample_worlds(mutated,lost,histories,random.Random(5),0,16))

    def test_orientation_normalization(self):
        cells,lost,histories=small_position()
        old=histories[1]
        rotated=old[:]
        rotated[0]=98;rotated[2]=98;rotated[3]=98
        self.assertEqual(features(cells,0,1,old),features(cells,1,98,rotated))

    def test_known_enemy_ranks_and_own_army_preserved(self):
        cells,lost,histories=small_position()
        cells[3]=16|32|0;lost[0]-=1
        cells[90]=9
        for world,weight in BeliefModel(document()).sample_worlds(cells,lost,histories,random.Random(0),0,50):
            self.assertEqual(world[3],cells[3]);self.assertEqual(world[90],9)
            self.assertGreater(weight,0)

    def test_invalid_model_inventory_and_histories_fail(self):
        bad=document();bad['log_likelihood_ratios'][0][0][0][0]=float('nan')
        with self.assertRaises(ValueError):BeliefModel(bad)
        cells,lost,histories=small_position();lost[5]+=1
        with self.assertRaises(ValueError):BeliefModel(document()).prepare(cells,lost,histories,0)
        cells,lost,histories=small_position();histories.pop(0)
        with self.assertRaises(ValueError):BeliefModel(document()).prepare(cells,lost,histories,0)

    def test_all_known_world(self):
        cells=[255]*100
        self.assertEqual(BeliefModel(document()).sample_worlds(cells,COUNTS,{},random.Random(1),0,2),[(cells,1.),(cells,1.)])


@unittest.skipUnless((ROOT/'ai/models/public-history-beliefs-v1.json').exists() and
                     any(p['id']==POLICY for p in json.loads((ROOT/'ai/registry.json').read_text())['policies']),
                     'run after model fitting and immutable registration')
class FrozenPolicyTests(unittest.TestCase):
    def test_portable_model_and_no_privileged_transport(self):
        executable,receipt=build_policy(POLICY)
        spec=receipt['policy']
        self.assertFalse(receives_opponent_setup(spec))
        self.assertNotIn('AI_DIAGNOSTIC_TRUTH',spec['defines'])
        with tempfile.TemporaryDirectory() as temp:
            result=subprocess.run([str(executable)],input='opponent-setup rejected\n',cwd=temp,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('rejects opponent setup',result.stderr)
        self.assertIn('public-history-beliefs-v1.json',receipt['runtime_sha256'])

    def test_python_native_reused_match_parity(self):
        with tempfile.TemporaryDirectory() as temp:
            paths=[]
            for label,backend,reuse in (('python','python',None),('native','openmp',False),('pool','openmp',True)):
                path=Path(temp)/(label+'.fmtour');paths.append(path)
                with contextlib.redirect_stdout(io.StringIO()):
                    run(POLICY,'teacher-context-v1-normal',path,rounds=1,seed=2009001,
                        jobs=1,families=['uniform'],max_plies=40,backend=backend,reuse_processes=reuse)
                self.assertEqual(verify(path)['errors'],0)
            with Tournament(paths[0]) as old:
                for path in paths[1:]:
                    with Tournament(path) as new:
                        for row in old.games():self.assertEqual(old.game(row['id']),new.game(row['id']))


if __name__=='__main__':unittest.main()
