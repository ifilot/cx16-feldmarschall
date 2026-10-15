"""Real adapter/CLI wiring and frozen-baseline parity for learned rank swaps."""
import copy
import json
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_registry import ROOT,build_policy,catalog,receives_opponent_setup
from campaign_swap_beliefs import SwapBeliefs
from feldmarschall import COUNTS,Engine,LAKES,parse_square,square_name
from teacher_bot import TeacherBot
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

MODEL=ROOT/'ai/models/public-history-beliefs-v1.json'
POLICIES=('teacher-unweighted-beliefs-v1-normal','teacher-swap-beliefs-v1-normal')


class SwapAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program,_=build_policy('teacher-calibrated-beliefs-v1-normal');cls.bundle=program.parent
        cls.tournament=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour'
        with Tournament(cls.tournament) as saved:cls.game=saved.game(9)
        cls.states,_=replay(cls.game);cls.events=public_events(cls.game,cls.states)

    def bot(self,sweeps):
        return TeacherBot(self.bundle/'observer',self.bundle/'teacher',samples=8,depth=4,
                          blend='correction',strategic=True,context=True,belief_model=MODEL,belief_sweeps=sweeps)

    def initialize(self,bot,army):
        bot.rng.seed(819)
        for line in ['new '+('red','blue')[army],'rules 0','difficulty normal','seed 819',
                     'setup '+self.game[('red_setup','blue_setup')[army]]]:bot.observer.send(line)

    def cli(self,sweeps):
        return Engine(shlex.join([sys.executable,str(ROOT/'tools/teacher_bot.py'),
            '--observer',str(self.bundle/'observer'),'--teacher',str(self.bundle/'teacher'),
            '--samples','8','--depth','4','--blend','correction','--strategic','--context',
            '--belief-model',str(MODEL),'--belief-sweeps',str(sweeps)]))

    def test_zero_and_four_sweep_hooks_match_real_cli_public_prefixes(self):
        for sweeps in (0,4):
            for army in (0,1):
                bot=self.bot(sweeps);cli=self.cli(sweeps)
                try:
                    self.initialize(bot,army)
                    for line in ['new '+('red','blue')[army],'rules 0','difficulty normal','seed 819',
                                 'setup '+self.game[('red_setup','blue_setup')[army]]]:cli.send(line)
                    for ply,event in enumerate(self.events[:96]):
                        if ply%8==army:
                            self.assertIsInstance(bot.world_sampler,SwapBeliefs)
                            with patch.object(bot.world_sampler,'sample_worlds',wraps=bot.world_sampler.sample_worlds) as sample:
                                move=bot.choose();self.assertEqual(sample.call_count,1)
                            self.assertEqual(move,tuple(map(parse_square,cli.ask('go','move').split())))
                            report=bot.last_report['swap_beliefs']
                            self.assertEqual(report['sweeps'],sweeps);self.assertEqual(report['chains'],8)
                            self.assertEqual(bot.last_report['effective_samples'],8.)
                            self.assertTrue(report['finite_burn_in_approximation'])
                        bot.observer.send(event);cli.send(event)
                finally:bot.close();cli.close()

    def test_hidden_nibbles_preserve_entire_reports_after_public_history(self):
        for sweeps in (0,4):
            for army in (0,1):
                reports=[]
                for mutate in (False,True):
                    bot=self.bot(sweeps)
                    try:
                        self.initialize(bot,army)
                        for event in self.events[:80]:bot.observer.send(event)
                        original=bot.observer.ask
                        def public_input(line,prefix):
                            result=original(line,prefix)
                            if mutate and line=='public':
                                side,board,lost,shuttle=result.split();cells=list(bytes.fromhex(board))
                                for sq,cell in enumerate(cells):
                                    if cell<254 and bool(cell&16)!=bool(army) and not cell&32:cells[sq]=(cell&240)|(sq%12)
                                return ' '.join((side,bytes(cells).hex(),lost,shuttle))
                            return result
                        with patch.object(bot.observer,'ask',side_effect=public_input):bot.choose()
                        reports.append(copy.deepcopy(bot.last_report))
                    finally:bot.close()
                self.assertEqual(reports[0],reports[1])

    def test_immediate_public_flag_capture_preserved(self):
        for sweeps in (0,4):
            for army in (0,1):
                bot=self.bot(sweeps)
                try:
                    cells=[254 if sq in LAKES else 255 for sq in range(100)]
                    cells[50]=16*army;cells[40]=16*(1-army)|32|11;cells[99]=16*army|11
                    lost=COUNTS[:];lost[11]-=1
                    bot.observer.send('new '+('red','blue')[army])
                    bot.observer.ask(f'position {army} {bytes(lost).hex()} {bytes(cells).hex()} ffffffffffff','positionok')
                    self.assertEqual(bot.choose(),(50,40))
                finally:bot.close()

    def test_experiments_and_privileged_inputs_are_rejected_including_zero_sweeps(self):
        for sweeps in (0,4):
            for options in [dict(diagnostic_truth=True),dict(information_strategy='lifetime'),dict(root_policy='unused'),
                            dict(world_sampling='latin'),dict(campaign_strategy='activation'),dict(paired_confidence=True),
                            dict(adaptive_depth=True),dict(joint_belief_model='unused'),dict(correction_anchor='parent')]:
                with self.assertRaisesRegex(ValueError,'isolate honest rank-swap'):
                    TeacherBot('unused','unused',belief_model=MODEL,blend='correction',belief_sweeps=sweeps,**options)
            with self.assertRaisesRegex(ValueError,'frozen belief model'):
                TeacherBot('unused','unused',blend='correction',belief_sweeps=sweeps)
            bot=self.bot(sweeps)
            try:
                with self.assertRaisesRegex(ValueError,'rejects opponent setup'):
                    bot.diagnostic_event(['opponent-setup',self.game['blue_setup']])
            finally:bot.close()

    def test_option_absent_preserves_frozen_learned_reports_on_140_public_roots(self):
        script='''import sys,json
sys.path.insert(0,sys.argv[1])
from teacher_bot import TeacherBot
b=TeacherBot(sys.argv[1]+'/observer',sys.argv[1]+'/teacher',samples=8,depth=4,blend='correction',strategic=True,context=True,belief_model=sys.argv[1]+'/public-history-beliefs-v1.json')
try:
 for line in sys.stdin:
  r=json.loads(line)
  for c in r.get('commands',[]):
   if c.startswith('seed '):b.rng.seed(int(c.split()[1]))
   b.observer.send(c)
  if r.get('choose'):b.choose();out=b.last_report
  elif r.get('native'):out=b.observer.ask('go','move')
  else:out=None
  print(json.dumps(out),flush=True)
finally:b.close()
'''
        old=subprocess.Popen([sys.executable,'-c',script,str(self.bundle)],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        bot=self.bot(None);tested=0
        self.assertIs(bot.world_sampler,bot.belief_model)
        def request(**value):
            old.stdin.write(json.dumps(value)+'\n');old.stdin.flush();line=old.stdout.readline()
            if not line:raise AssertionError(old.stderr.read())
            return json.loads(line)
        try:
            with Tournament(self.tournament) as saved:
                longest={}
                for row in saved.games():
                    if row['result']!='error' and row['plies']>=20 and (row['family'] not in longest or row['plies']>longest[row['family']]['plies']):longest[row['family']]=row
                games=[saved.game(row['id']) for _,row in sorted(longest.items())]
            self.assertEqual(len(games),7)
            for game in games:
                states,_=replay(game);events=public_events(game,states)
                for army in (0,1):
                    eligible=list(range(army,min(len(events),500),2));selected={eligible[i*len(eligible)//10] for i in range(10)}
                    self.assertEqual(len(selected),10);bot.rng.seed(game['seed'])
                    commands=['new '+('red','blue')[army],'rules 0','difficulty normal','seed '+str(game['seed']),
                              'setup '+game[('red_setup','blue_setup')[army]]]
                    for command in commands:bot.observer.send(command)
                    request(commands=commands)
                    for ply,event in enumerate(events[:max(selected)+1]):
                        if ply%2==army:
                            if ply in selected:
                                bot.choose();reference=request(choose=True)
                                self.assertNotIn('swap_beliefs',bot.last_report)
                                self.assertEqual(json.loads(json.dumps(bot.last_report)),reference,(game['id'],army,ply));tested+=1
                            else:self.assertEqual(bot.observer.ask('go','move'),request(native=True))
                            command='played '+' '.join(event.split()[1:3])
                            bot.observer.ask(command,'playedok');request(commands=[command])
                        bot.observer.send(event);request(commands=[event])
            self.assertEqual(tested,140)
        finally:
            bot.close();old.stdin.close();old.wait(timeout=15);old.stdout.close();old.stderr.close()
            self.assertEqual(old.returncode,0)

    def test_registered_swap_bundles_are_portable_outside_checkout(self):
        registered={p['id']:p for p in catalog()}
        if not all(p in registered for p in POLICIES):self.skipTest('rerun after both swap policies registered')
        for identity in POLICIES:
            self.assertFalse(receives_opponent_setup(registered[identity]))
            program,_=build_policy(identity)
            with tempfile.TemporaryDirectory(prefix='portable-swaps-') as tmp:
                portable=Path(tmp)/'bundle';shutil.copytree(program.parent,portable)
                with patch('feldmarschall.ROOT',Path(tmp)):bot=Engine(shlex.quote(str(portable/program.name)))
                try:
                    for command in ['new red','seed 819','setup '+self.game['red_setup']]:bot.send(command)
                    self.assertEqual(len(bot.ask('go','move').split()),2)
                    for event in self.events[:80]:bot.send(event)
                    self.assertEqual(len(bot.ask('go','move').split()),2)
                finally:bot.close()


if __name__=='__main__':unittest.main()
