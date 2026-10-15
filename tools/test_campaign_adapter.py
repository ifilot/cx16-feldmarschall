"""Exercise campaign hooks through the real observer and rollout adapter."""
import json
import contextlib
import io
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch

from ai_registry import ROOT, build_policy
from feldmarschall import COUNTS, LAKES, parse_square, square_name
from teacher_bot import TeacherBot
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay


BASE='teacher-context-v1-normal'
OPTIONS=[dict(world_sampling='latin'),dict(world_sampling='uniform'),
         dict(campaign_strategy='activation'),dict(campaign_strategy='recurrence'),
         dict(paired_confidence=True)]


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program,_=build_policy(BASE);cls.bundle=program.parent
        cls.tournament=ROOT/'docs/ai-vs-msdos-2026-10-15/teacher-context-v1-normal.fmtour'
        with Tournament(cls.tournament) as tournament:cls.game=tournament.game(9)

    def bot(self,**options):
        return TeacherBot(self.bundle/'observer',self.bundle/'teacher',samples=8,depth=4,
                          blend='correction',strategic=True,context=True,**options)

    def initialize(self,bot,army):
        bot.rng.seed(719)
        for command in ['new '+('red','blue')[army],'rules 0','difficulty normal','seed 719',
                        'setup '+self.game[('red_setup','blue_setup')[army]]]:bot.observer.send(command)

    def test_adaptive_depth_uses_only_public_legal_action_count(self):
        from campaign_depth import depth_for_actions
        bot=self.bot(adaptive_depth=True)
        try:
            self.initialize(bot,0)
            bot.choose()
            count=len(bot.last_report['values'])
            self.assertEqual(bot.last_report['adaptive_depth'],depth_for_actions(4,count))
            cells=[254 if sq in LAKES else 255 for sq in range(100)]
            cells[50],cells[40],cells[99]=0,16|32|11,11
            lost=COUNTS[:];lost[11]-=1
            bot.observer.ask(f'position 0 {bytes(lost).hex()} {bytes(cells).hex()} ffffffffffff','positionok')
            self.assertEqual(bot.choose(),(50,40))
            self.assertEqual(bot.last_report['adaptive_depth'],8)
            with self.assertRaisesRegex(ValueError,'rejects opponent setup'):
                bot.diagnostic_event(['opponent-setup',self.game['blue_setup']])
        finally:bot.close()
        with self.assertRaisesRegex(ValueError,'isolate honest adaptive'):
            self.bot(adaptive_depth=True,diagnostic_truth=True)

    def test_parent_anchor_wiring_preserves_the_legal_fallback_score(self):
        bot=self.bot(correction_anchor='parent')
        try:
            self.initialize(bot,0)
            bot.choose()
            parent=bot.last_report['parent']
            row=next(row for row in bot.last_report['values'] if tuple(row['move'])==parent)
            self.assertEqual(row['correction'],0)
            self.assertEqual(row['value'],row['parent_score'])
            self.assertEqual(bot.last_report['correction_anchor']['parent_correction'],0)
        finally:bot.close()
        with self.assertRaisesRegex(ValueError,'isolate honest legal-parent'):
            self.bot(correction_anchor='parent',diagnostic_truth=True)

    def test_flag_interceptor_receives_public_shuttle_and_reports_coverage(self):
        bot=self.bot(campaign_strategy='flag-interceptor')
        try:
            self.initialize(bot,0)
            shuttle=bot.observer.ask('public','public').split()[-1]
            with patch.object(bot.campaign_module,'evaluate',wraps=bot.campaign_module.evaluate) as hook:
                bot.choose()
            self.assertEqual(hook.call_count,1)
            self.assertEqual(hook.call_args.args[-1],shuttle)
            self.assertIn('flag_interceptor',bot.last_report)
            self.assertIn('active',bot.last_report['flag_interceptor'])
        finally:bot.close()

    def test_real_hooks_are_called_and_reported(self):
        import campaign_sampling,campaign_strategy,campaign_search
        for options in OPTIONS:
            with self.subTest(options=options):
                bot=self.bot(**options)
                try:
                    self.initialize(bot,0)
                    if 'world_sampling' in options:
                        with patch.object(bot.world_sampler,'sample_worlds',wraps=bot.world_sampler.sample_worlds) as hook:
                            move=bot.choose();self.assertEqual(hook.call_count,1)
                        expected=(campaign_sampling.StratifiedSampler if options['world_sampling']=='latin'
                                  else campaign_sampling.UniformSampler)
                        self.assertIsInstance(bot.world_sampler,expected)
                    elif 'campaign_strategy' in options:
                        with patch.object(bot.campaign_module,'adjustments',wraps=bot.campaign_module.adjustments) as hook:
                            move=bot.choose();self.assertEqual(hook.call_count,1)
                        self.assertTrue(bot.last_report['campaign_adjustments'])
                    else:
                        with patch.object(campaign_search,'paired_selection',wraps=campaign_search.paired_selection) as hook:
                            move=bot.choose();self.assertEqual(hook.call_count,1)
                        self.assertEqual(bot.last_report['paired_selection']['samples'],8)
                    self.assertIn(move,[tuple(row['move']) for row in bot.last_report['values']])
                finally:bot.close()

    def test_recurrence_memory_resets_through_actual_new_game_protocol(self):
        bot=self.bot(campaign_strategy='recurrence')
        commands=['new red','seed 719','setup '+self.game['red_setup']]+['go']*18
        commands+=['new red','seed 719','setup '+self.game['red_setup'],'go','quit']
        with patch.object(bot.campaign_module,'reset',wraps=bot.campaign_module.reset) as reset, \
             patch.object(sys,'stdin',io.StringIO('\n'.join(commands)+'\n')), \
             contextlib.redirect_stdout(io.StringIO()):
            bot.run() # closes the real observer/teacher in its finally block
        self.assertEqual(reset.call_count,2)
        self.assertEqual(len(bot.campaign_module.history),1)
        self.assertEqual(bot.last_report['recurrence']['quiet_decisions'],0)

    def test_hidden_enemy_nibbles_do_not_change_complete_reports(self):
        for options in OPTIONS:
            for army in (0,1):
                with self.subTest(options=options,army=army):
                    reports=[]
                    for changed in (False,True):
                        bot=self.bot(**options)
                        try:
                            self.initialize(bot,army)
                            _,board,lost,shuttle=bot.observer.ask('public','public').split()
                            cells=list(bytes.fromhex(board))
                            if changed:
                                for sq,cell in enumerate(cells):
                                    if cell<254 and bool(cell&16)!=bool(army) and not cell&32:
                                        cells[sq]=(cell&240)|(sq%12)
                            bot.observer.ask(f'position {army} {lost} {bytes(cells).hex()} {shuttle}','positionok')
                            bot.choose();reports.append(bot.last_report)
                        finally:bot.close()
                    self.assertEqual(reports[0],reports[1])

    def test_immediate_flag_capture_keeps_priority_for_every_hook(self):
        for options in OPTIONS:
            for army in (0,1):
                with self.subTest(options=options,army=army):
                    bot=self.bot(**options)
                    try:
                        cells=[254 if sq in LAKES else 255 for sq in range(100)]
                        cells[50]=16*army # own Marshal
                        cells[40]=16*(1-army)|32|11 # disclosed enemy Flag
                        cells[99]=16*army|11
                        lost=COUNTS[:];lost[11]-=1
                        bot.observer.send('new '+('red','blue')[army])
                        bot.observer.ask(f'position {army} {bytes(lost).hex()} {bytes(cells).hex()} ffffffffffff','positionok')
                        self.assertEqual(bot.choose(),(50,40))
                        if 'paired_confidence' in options:
                            self.assertTrue(bot.last_report['paired_selection']['forced_immediate_win'])
                    finally:bot.close()

    def test_honest_hooks_reject_private_setup_and_privileged_combinations(self):
        for options in OPTIONS:
            bot=self.bot(**options)
            try:
                with self.assertRaisesRegex(ValueError,'rejects opponent setup'):
                    bot.diagnostic_event(['opponent-setup',self.game['blue_setup']])
            finally:bot.close()
            with self.assertRaisesRegex(ValueError,'honest teacher'):
                self.bot(diagnostic_truth=True,**options)

    def test_default_adapter_matches_frozen_subprocess_on_140_public_roots(self):
        # Run the immutable old Python adapter in a fresh interpreter so imports
        # resolve from its frozen bundle, rather than the current working tree.
        script='''import json,sys
sys.path.insert(0,sys.argv[1])
from teacher_bot import TeacherBot
b=TeacherBot(sys.argv[1]+'/observer',sys.argv[1]+'/teacher',samples=8,depth=4,blend='correction',strategic=True,context=True)
try:
 for line in sys.stdin:
  r=json.loads(line)
  for c in r.get('commands',[]):
   if c.startswith('seed '):b.rng.seed(int(c.split()[1]))
   b.observer.send(c)
  if r.get('choose'): b.choose();out=b.last_report
  elif r.get('native'):out=b.observer.ask('go','move')
  else:out=None
  print(json.dumps(out),flush=True)
finally:b.close()
'''
        old=subprocess.Popen([sys.executable,'-c',script,str(self.bundle)],stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        bot=self.bot();tested=0;orientations=set();families=set()
        def old_request(**request):
            old.stdin.write(json.dumps(request)+'\n');old.stdin.flush()
            line=old.stdout.readline()
            if not line:raise AssertionError(old.stderr.read())
            return json.loads(line)
        try:
            with Tournament(self.tournament) as tournament:
                longest={}
                for row in tournament.games():
                    if row['result']!='error' and row['plies']>=20 and (row['family'] not in longest or row['plies']>longest[row['family']]['plies']):longest[row['family']]=row
                games=[tournament.game(row['id']) for _,row in sorted(longest.items())]
            self.assertEqual(len(games),7)
            for game in games:
                states,_=replay(game);events=public_events(game,states)
                for army in (0,1):
                    eligible=list(range(army,min(len(events),500),2))
                    selected={eligible[i*len(eligible)//10] for i in range(10)}
                    self.assertEqual(len(selected),10)
                    seed=game['seed']
                    commands=['new '+('red','blue')[army],'rules 0','difficulty normal','seed '+str(seed),
                              'setup '+game[('red_setup','blue_setup')[army]]]
                    bot.rng.seed(seed)
                    for command in commands:bot.observer.send(command)
                    old_request(commands=commands)
                    for ply,event in enumerate(events[:max(selected)+1]):
                        if ply%2==army:
                            if ply in selected:
                                bot.choose();reference=old_request(choose=True)
                                self.assertEqual(json.loads(json.dumps(bot.last_report)),reference,(game['id'],army,ply))
                                tested+=1;orientations.add(army);families.add(game['family'])
                            else:self.assertEqual(bot.observer.ask('go','move'),old_request(native=True))
                            command='played '+' '.join(event.split()[1:3])
                            bot.observer.ask(command,'playedok');old_request(commands=[command])
                        bot.observer.send(event);old_request(commands=[event])
            self.assertEqual(tested,140);self.assertEqual(orientations,{0,1});self.assertEqual(len(families),7)
        finally:
            bot.close();old.stdin.close();old.wait(timeout=15);old.stdout.close();old.stderr.close()
            self.assertEqual(old.returncode,0)


if __name__=='__main__':unittest.main()
