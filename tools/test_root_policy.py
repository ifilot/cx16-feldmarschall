"""KL optimization, numerical stability, isolated integration and portability."""
import contextlib
import copy
import io
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from ai_registry import ROOT, build_policy, catalog, receives_opponent_setup
from feldmarschall import COUNTS, GLYPHS, LAKES
from root_policy import RootPolicy, SCHEMA, MOVE_SEED_DOMAIN
from teacher_bot import TeacherBot
from tournament import run
from tournament_store import Tournament, verify

POLICIES=('teacher-probability-control-v1-normal','teacher-kl-restrained-v1-normal')


def config(mode='kl-restrained',temperature=8,budget=.1):
    return dict(schema=SCHEMA,mode=mode,temperature=temperature,kl_budget=budget)


class RootPolicyMath(unittest.TestCase):
    def test_control_matches_softmax_of_corrected_scores(self):
        scores={(60,50):17,(61,51):9,(62,52):2}
        corrections={(60,50):-7,(61,51):8,(62,52):0}
        result=RootPolicy(config('probability-control')).distribution(scores,corrections)
        raw=[math.exp((scores[m]+corrections[m])/8) for m in result['moves']]
        for actual,value in zip(result['probabilities'],raw):self.assertAlmostEqual(actual,value/sum(raw))
        self.assertFalse(result['constrained'])

    def test_binary_constraint_matches_independent_grid_optimum(self):
        scores={(1,2):0,(3,4):0};corrections={(1,2):32,(3,4):-32}
        result=RootPolicy(config()).distribution(scores,corrections)
        p=result['probabilities'][0]
        self.assertAlmostEqual(result['kl'],.1,places=10)
        feasible=[]
        for index in range(1,10000):
            q=index/10000
            kl=q*math.log(2*q)+(1-q)*math.log(2*(1-q))
            if kl<=.1:
                objective=q*32+(1-q)*-32-8*(q*math.log(q)+(1-q)*math.log(1-q))
                feasible.append((objective,q))
        best=max(feasible)[1]
        self.assertAlmostEqual(p,best,delta=.00011)

    def test_inactive_constraint_is_exact_control(self):
        scores={(1,2):0,(3,4):1};corrections={(1,2):1,(3,4):0}
        control=RootPolicy(config('probability-control',budget=1)).distribution(scores,corrections)
        restrained=RootPolicy(config(budget=1)).distribution(scores,corrections)
        self.assertEqual(control['probabilities'],restrained['probabilities'])
        self.assertFalse(restrained['constrained'])

    def test_zero_budget_recovers_native_prior(self):
        result=RootPolicy(config(budget=0)).distribution({(1,2):0,(3,4):8},{(1,2):100,(3,4):-100})
        self.assertEqual(result['probabilities'],result['prior_probabilities'])
        self.assertEqual(result['kl'],0)
        self.assertIsNone(result['dual_ratio'])
        json.dumps(result,allow_nan=False)

    def test_extreme_scores_and_shift_invariance(self):
        scores={(1,2):-30000,(3,4):29999,(5,6):29990};corrections={m:192 for m in scores}
        first=RootPolicy(config()).distribution(scores,corrections)
        second=RootPolicy(config()).distribution({m:s+1000 for m,s in scores.items()},corrections)
        self.assertEqual(first['probabilities'],second['probabilities'])
        self.assertAlmostEqual(sum(first['probabilities']),1)
        self.assertAlmostEqual(first['kl'],0)
        json.dumps(first,allow_nan=False)

    def test_constraint_holds_across_random_move_sets(self):
        rng=random.Random(571)
        for _ in range(100):
            scores={(i,i+1):rng.randrange(-300,301) for i in range(rng.randrange(2,40))}
            corrections={m:rng.randrange(-192,193) for m in scores}
            result=RootPolicy(config(budget=.02)).distribution(scores,corrections)
            self.assertLessEqual(result['kl'],.02+1e-10)
            self.assertLessEqual(result['kl'],result['control_kl']+1e-10)
            self.assertAlmostEqual(sum(result['probabilities']),1,places=12)

    def test_draw_uses_given_stream_and_only_supported_moves(self):
        policy=RootPolicy(config('probability-control'))
        result=policy.distribution({(1,2):0,(3,4):8},{(1,2):0,(3,4):0})
        rng=random.Random(8);counts={(1,2):0,(3,4):0}
        for _ in range(10000):counts[policy.draw(result,rng)]+=1
        self.assertAlmostEqual(counts[(1,2)]/10000,result['probabilities'][0],delta=.015)

    def test_invalid_settings_scores_and_move_sets_rejected(self):
        for document in (config(temperature=0),config(budget=-1),config(temperature=float('nan')),config(mode='unknown')):
            with self.assertRaises(ValueError):RootPolicy(document)
        policy=RootPolicy(config())
        with self.assertRaises(ValueError):policy.distribution({}, {})
        with self.assertRaises(ValueError):policy.distribution({(1,2):0},{(3,4):1})
        with self.assertRaises(ValueError):policy.distribution({(1,2):float('inf')},{(1,2):0})


class RootPolicyAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        executable,_=build_policy('teacher-context-v1-normal')
        cls.observer,cls.teacher=executable.parent/'observer',executable.parent/'teacher'

    def bot(self,path=None):
        return TeacherBot(self.observer,self.teacher,samples=8,depth=4,blend='correction',
                          strategic=True,context=True,root_policy=path)

    def test_all_search_values_and_world_rng_unchanged(self):
        reports=[];rng_states=[]
        with tempfile.TemporaryDirectory() as temp:
            for mode in (None,'probability-control','kl-restrained'):
                path=Path(temp)/'settings.json'
                if mode:path.write_text(json.dumps(config(mode)))
                bot=self.bot(path if mode else None)
                try:
                    bot.rng.seed(314)
                    for command in ('new red','rules 0','difficulty normal','seed 314',
                                    'setup '+''.join(g*n for g,n in zip(GLYPHS,COUNTS))):
                        bot.observer.send(command)
                    bot.choose()
                    report=copy.deepcopy(bot.last_report)
                    report.pop('selected');report.pop('root_selection',None)
                    reports.append(report);rng_states.append(bot.rng.getstate())
                finally:bot.close()
        self.assertEqual(reports[0],reports[1]);self.assertEqual(reports[0],reports[2])
        self.assertEqual(rng_states[0],rng_states[1]);self.assertEqual(rng_states[0],rng_states[2])

    def test_immediate_flag_capture_is_forced_without_rng_draw(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'settings.json';path.write_text(json.dumps(config()))
            bot=self.bot(path)
            try:
                cells=[254 if sq in LAKES else 255 for sq in range(100)]
                cells[60],cells[99],cells[50]=8,11,16|32|11
                lost=COUNTS[:];lost[11]-=1
                bot.observer.ask('position 0 '+bytes(lost).hex()+' '+bytes(cells).hex()+' ffffffff0000','positionok')
                state=bot.policy_rng.getstate()
                self.assertEqual(bot.choose(),(60,50))
                self.assertEqual(bot.policy_rng.getstate(),state)
                self.assertTrue(bot.last_report['root_selection']['forced_immediate_win'])
            finally:bot.close()

    def test_incompatible_modes_rejected_before_loading_settings(self):
        for kwargs in ({'diagnostic_truth':True},{'belief_model':'no-file'},{'information_strategy':'lifetime'},{'blend':'raw'}):
            options=dict(blend='correction',root_policy='no-file');options.update(kwargs)
            with self.assertRaisesRegex(ValueError,'root selection requires'):
                TeacherBot(self.observer,self.teacher,**options)


@unittest.skipUnless(all(any(p['id']==identity for p in catalog()) for identity in POLICIES),
                     'run after immutable policy registration')
class FrozenRootPolicies(unittest.TestCase):
    def test_fair_transport_and_portable_settings(self):
        for identity in POLICIES:
            executable,receipt=build_policy(identity)
            self.assertFalse(receives_opponent_setup(receipt['policy']))
            self.assertNotIn('AI_DIAGNOSTIC_TRUTH',receipt['policy']['defines'])
            with tempfile.TemporaryDirectory() as temp:
                result=subprocess.run([str(executable)],cwd=temp,input='opponent-setup rejected\n',
                                      capture_output=True,text=True,timeout=10)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('rejects opponent setup',result.stderr)
            name=Path(receipt['policy']['root_policy']).name
            self.assertIn(name,receipt['runtime_sha256'])

    def test_python_native_and_reused_process_parity(self):
        with tempfile.TemporaryDirectory() as temp:
            for identity in POLICIES:
                paths=[]
                for label,backend,reuse in (('python','python',None),('native','openmp',False),('pooled','openmp',True)):
                    path=Path(temp)/(identity+label+'.fmtour');paths.append(path)
                    with contextlib.redirect_stdout(io.StringIO()):
                        run(identity,'teacher-context-v1-normal',path,rounds=1,seed=2049001,jobs=1,
                            families=['uniform'],max_plies=40,backend=backend,reuse_processes=reuse)
                    self.assertEqual(verify(path)['errors'],0)
                with Tournament(paths[0]) as baseline:
                    for path in paths[1:]:
                        with Tournament(path) as candidate:
                            for row in baseline.games():self.assertEqual(baseline.game(row['id']),candidate.game(row['id']))


if __name__=='__main__':unittest.main()
