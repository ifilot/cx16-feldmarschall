"""Mechanical qualification; only previously designated development history."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import random
import shlex
import subprocess
import tempfile
import time
import unittest

from ai_registry import ROOT,build_policy,get_policy
from campaign_belief_values import gain,worths,native_expected
from campaign_native_template import NativeTemplateBot as Baseline
from new_campaign_objectives_bot import NativeTemplateBot as Candidate
from new_campaign_objectives import goal_values,goal_packet
from feldmarschall import COUNTS,Engine
from test_campaign_native_template import AlterPublicNibbles
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


class NumericTests(unittest.TestCase):
    def test_exact_rational_mixture_and_exchangeable_reduction(self):
        rng=random.Random(2026101607);lost=[0]*12;worth=worths(lost)
        for _ in range(600):
            remaining=list(COUNTS);f=rng.randrange(4097);b=rng.randrange(4097-f)
            weights=[rng.randrange(100)for _ in range(10)];total=sum(weights)
            marginal=[n/total for n in weights]+[0.,0.]
            cells=[255]*100;cells[35]=28
            table=goal_values(cells,0,lost,remaining,{35:marginal},[f]*100,[b]*100)
            for actor in range(10):
                conditional=sum(Fraction(n,total)*gain(actor,r,worth)for r,n in enumerate(weights))
                value=(f*2000+b*gain(actor,10,worth)+(4096-f-b)*conditional)/4096
                self.assertEqual(table[actor][35],int(value))
            h=sum(remaining[:10]);exchange=[n/h for n in remaining[:10]]+[0.,0.]
            cells[35]|=64
            table=goal_values(cells,0,lost,remaining,{35:exchange},[f]*100,[b]*100)
            for actor in range(10):self.assertEqual(table[actor][35],native_expected(actor,True,remaining,worth))

    def test_packet_signed_and_validation(self):
        table=[[0]*100 for _ in range(10)];table[0][0]=-400;table[9][99]=2000
        packet=goal_packet(table);self.assertEqual(len(packet),4000);self.assertEqual(packet[:4],'fe70');self.assertEqual(packet[-4:],'07d0')
        table[0][0]=-401
        with self.assertRaises(ValueError):goal_packet(table)


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        executable,_=build_policy('student-fortress-template-flag-bomb-v1-normal')
        cls.base=executable.parent/'observer';cls.directory=tempfile.TemporaryDirectory(prefix='new-objectives-tests-');cls.new=Path(cls.directory.name)/'observer'
        policy=get_policy('student-fortress-template-flag-bomb-v1-normal')
        replacements={'src/core/ai.c':'tools/new_campaign_objectives_ai.c','src/native/engine.c':'tools/new_campaign_objectives_engine.c'}
        sources=[replacements.get(source,source)for source in policy['sources']]
        subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow','-Isrc/core',
                        *['-D'+define for define in policy['defines']],'-DAI_TRACE','-o',str(cls.new),*sources],cwd=ROOT,check=True)
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour')as store:cls.game=store.game(9)
        states,_=replay(cls.game);cls.events=public_events(cls.game,states)

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def make(self,kind,army,alter=False,observer=None):
        wrapper=AlterPublicNibbles(Engine(shlex.quote(str(observer or self.new))),alter)
        bot=kind(wrapper)
        for command in ('new '+('red','blue')[army],'rules 0','seed 7231','setup '+self.game[('red_setup','blue_setup')[army]]):bot.observe(command.split())
        return bot,wrapper

    def test_default_off_all_prefix_choices_parity_both_colors(self):
        for army in (0,1):
            bots=[self.make(Baseline,army,observer=self.base)[0],self.make(Baseline,army)[0]]
            try:
                for ply in range(120):
                    if ply%2==army:self.assertEqual(bots[0].choose(),bots[1].choose())
                    for bot in bots:bot.observe(self.events[ply].split())
            finally:
                for bot in bots:bot.close()

    def test_full_persistent_policy_private_nibbles_reset_one_go_both_colors(self):
        self.elapsed=[];self.changed=0
        for army in (0,1):
            pairs=[self.make(Candidate,army,alter)for alter in(False,True)]
            base,_=self.make(Baseline,army)
            try:
                for ply in range(120):
                    if ply%2==army:
                        moves=[]
                        for bot,wrapper in pairs:
                            before=len(wrapper.calls);started=time.perf_counter();moves.append(bot.choose());self.elapsed.append(time.perf_counter()-started)
                            calls=wrapper.calls[before:];self.assertEqual(calls.count('go'),1)
                            self.assertEqual(sum(c.startswith('goal-priors ')for c in calls),1)
                            self.assertFalse(any(c.startswith(('opponent-setup','search '))for c in calls))
                        self.assertEqual(*moves);self.changed+=moves[0]!=base.choose()
                    for bot,_ in pairs:bot.observe(self.events[ply].split())
                    base.observe(self.events[ply].split())
                for bot,wrapper in pairs:
                    bot.observe(['new',('red','blue')[army]]);self.assertIsNone(bot.last_report)
                    bot.observe(['setup',self.game[('red_setup','blue_setup')[army]]]);self.assertIsNotNone(bot.choose())
            finally:
                for bot,_ in pairs:bot.close()
                base.close()
        print(json.dumps(dict(persistent_decisions=120,private_nibble_pairs=120,changed_vs_baseline=self.changed,
             wall_seconds=sum(self.elapsed),mean_adapter_seconds=sum(self.elapsed)/len(self.elapsed),max_adapter_seconds=max(self.elapsed))))

    def test_goal_api_rejects_malformed_and_requires_fresh_base_packet(self):
        bot,wrapper=self.make(Candidate,0)
        try:
            with self.assertRaises(RuntimeError):wrapper.ask('goal-priors '+goal_packet([[0]*100 for _ in range(10)]),'goal-priorsok')
            bot.choose()
            bot.observe(['new','red'])
            with self.assertRaises(RuntimeError):wrapper.ask('goal-priors '+'0'*4000,'goal-priorsok')
        finally:bot.close()

    def test_capture_scores_unchanged_through_both_color_histories(self):
        class Ranked(AlterPublicNibbles):
            def ask(self,line,prefix):
                if line!='go':return super().ask(line,prefix)
                self.engine.send('ranked');self.scores={}
                while True:
                    words=self.engine.read().split()
                    if words[0]=='candidate':self.scores[tuple(map(int,words[1:3]))]=int(words[3])
                    elif words[0]=='move':return ' '.join(words[1:])
                    elif words[0]=='error':raise RuntimeError(' '.join(words))
        checked=0
        for army in (0,1):
            bots=[]
            for kind in (Baseline,Candidate):
                wrapper=Ranked(Engine(shlex.quote(str(self.new))))
                bot=kind(wrapper)
                for command in ('new '+('red','blue')[army],'rules 0','seed 7231','setup '+self.game[('red_setup','blue_setup')[army]]):bot.observe(command.split())
                bots.append(bot)
            try:
                for ply in range(160):
                    if ply%2==army:
                        for bot in bots:bot.choose()
                        cells=bytes.fromhex(bots[0].last_report['public_board_hex'])
                        capture=[move for move in bots[0].observer.scores if cells[move[1]]<254]
                        self.assertEqual(set(bots[0].observer.scores),set(bots[1].observer.scores))
                        for move in capture:self.assertEqual(bots[0].observer.scores[move],bots[1].observer.scores[move]);checked+=1
                    for bot in bots:bot.observe(self.events[ply].split())
            finally:
                for bot in bots:bot.close()
        self.assertGreater(checked,100);print(json.dumps(dict(unchanged_capture_scores=checked)))


if __name__=='__main__':unittest.main()
