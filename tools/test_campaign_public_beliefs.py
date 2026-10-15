"""Real shared Teacher adapter wiring for public template/objective beliefs."""
import contextlib
import copy
import io
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch

from ai_registry import ROOT,build_policy
from campaign_inverse_objectives import ObjectiveSampler
from campaign_template_beliefs import TemplateMixtureBeliefs
from feldmarschall import COUNTS,Engine,LAKES,parse_square
from teacher_bot import TeacherBot
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

MODEL=ROOT/'ai/models/own-flag-motion-beliefs-v1.json'

class PublicBeliefAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program,_=build_policy('teacher-context-v1-normal');cls.bundle=program.parent
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:cls.game=saved.game(9)
        states,_=replay(cls.game);cls.events=public_events(cls.game,states)

    def model(self,kind):return TemplateMixtureBeliefs() if kind=='template' else ObjectiveSampler.load(MODEL)
    def bot(self,model,**kwargs):
        return TeacherBot(self.bundle/'observer',self.bundle/'teacher',samples=8,depth=4,
            strategic=True,context=True,blend='correction',public_belief=model,**kwargs)
    def commands(self,army):
        return ['new '+('red','blue')[army],'rules 0','difficulty normal','seed 719',
                'setup '+self.game[('red_setup','blue_setup')[army]]]
    def initialize(self,bot,army):
        bot.rng.seed(719)
        for command in self.commands(army)+self.events[:80]:
            bot.public_belief.observe(command.split());bot.observer.send(command)

    def test_real_cli_matches_direct_public_prefixes_for_both_models_and_sides(self):
        for kind in ('template','objective'):
            for army in (0,1):
                bot=self.bot(self.model(kind))
                cli=Engine(shlex.join([sys.executable,str(ROOT/'tools/teacher_bot.py'),
                    '--observer',str(self.bundle/'observer'),'--teacher',str(self.bundle/'teacher'),
                    '--samples','8','--depth','4','--blend','correction','--strategic','--context']+
                    (['--template-prior'] if kind=='template' else ['--objective-belief-model',str(MODEL)])))
                try:
                    self.initialize(bot,army)
                    for command in self.commands(army)+self.events[:80]:cli.send(command)
                    with patch.object(bot.world_sampler,'sample_worlds',wraps=bot.world_sampler.sample_worlds) as hook:
                        move=bot.choose();self.assertEqual(hook.call_count,1)
                    self.assertEqual(move,tuple(map(parse_square,cli.ask('go','move').split())))
                    self.assertEqual(bot.last_report['public_beliefs']['class'],type(bot.public_belief).__name__)
                finally:bot.close();cli.close()

    def test_hidden_nibbles_preserve_full_reports(self):
        for kind in ('template','objective'):
            for army in (0,1):
                reports=[]
                for mutate in (False,True):
                    bot=self.bot(self.model(kind))
                    try:
                        self.initialize(bot,army);original=bot.observer.ask
                        def query(line,prefix):
                            result=original(line,prefix)
                            if mutate and line=='public':
                                side,board,lost,shuttle=result.split();cells=list(bytes.fromhex(board))
                                for sq,c in enumerate(cells):
                                    if c<254 and bool(c&16)!=bool(army) and not c&32:cells[sq]=(c&240)|(sq%12)
                                return ' '.join((side,bytes(cells).hex(),lost,shuttle))
                            return result
                        with patch.object(bot.observer,'ask',side_effect=query):bot.choose()
                        reports.append(copy.deepcopy(bot.last_report))
                    finally:bot.close()
                self.assertEqual(reports[0],reports[1])

    def test_run_generated_setup_callback_and_every_actual_input(self):
        for kind in ('template','objective'):
            bot=self.bot(self.model(kind));commands=['feldmarschall','new red','rules 0','seed 728','setup','isready','go','quit']
            with patch.object(bot.public_belief,'observe',wraps=bot.public_belief.observe) as observe:
                with patch('sys.stdin',io.StringIO('\n'.join(commands)+'\n')),contextlib.redirect_stdout(io.StringIO()) as output:
                    bot.run()
                calls=[c.args[0] for c in observe.call_args_list]
                self.assertEqual([c for c in calls if len(c)!=2 or c[0]!='setup'],[c.split() for c in commands])
                generated=next(c[1] for c in calls if c[0]=='setup' and len(c)==2)
                self.assertIn('setup '+generated,output.getvalue());self.assertIn('move ',output.getvalue())
                self.assertEqual(len(calls),len(commands)+1)

    def test_mode_isolation_and_private_setup_rejection(self):
        options=[dict(diagnostic_truth=True),dict(diagnostic_knowledge='flag'),dict(information_strategy='lifetime'),
                 dict(belief_model=MODEL),dict(root_policy=MODEL),dict(world_sampling='latin'),
                 dict(campaign_strategy='activation'),dict(paired_confidence=True),dict(adaptive_depth=True),
                 dict(joint_belief_model=MODEL),dict(correction_anchor='parent'),dict(belief_sweeps=0),dict(root_capture_mode='counts')]
        for option in options:
            with self.assertRaisesRegex(ValueError,'isolate honest public beliefs'):self.bot(self.model('objective'),**option)
        with self.assertRaisesRegex(ValueError,'correction blend'):
            TeacherBot(None,None,public_belief=self.model('objective'))
        with self.assertRaisesRegex(ValueError,'observe and sample_worlds'):
            TeacherBot(None,None,blend='correction',public_belief=object())
        for kind in ('template','objective'):
            bot=self.bot(self.model(kind))
            with patch('sys.stdin',io.StringIO('opponent-setup '+self.game['blue_setup']+'\n')):
                with self.assertRaisesRegex(ValueError,'rejects opponent setup'):bot.run()
        result=subprocess.run([sys.executable,str(ROOT/'tools/teacher_bot.py'),'--template-prior','--objective-belief-model',str(MODEL)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('not allowed with',result.stderr)

    def test_immediate_flag_capture_priority_with_public_sampler(self):
        class PublicCopy:
            def observe(self,words):pass
            def sample_worlds(self,cells,lost,histories,rng,army,samples):return [(cells[:],1.) for _ in range(samples)]
        for army in (0,1):
            bot=self.bot(PublicCopy())
            try:
                cells=[254 if sq in LAKES else 255 for sq in range(100)]
                cells[50]=16*army;cells[40]=16*(1-army)|32|11;cells[99]=16*army|11
                lost=COUNTS[:];lost[11]-=1
                bot.observer.send('new '+('red','blue')[army])
                bot.observer.ask(f'position {army} {bytes(lost).hex()} {bytes(cells).hex()} ffffffffffff','positionok')
                self.assertEqual(bot.choose(),(50,40))
            finally:bot.close()

    def test_absent_option_exact_frozen_default_reports_on_140_roots(self):
        # Reuse the established subprocess audit: the old module imports only
        # its immutable bundle, and compares entire reports on both sides and
        # seven families, preserving actual public and strategic history.
        from test_campaign_adapter import AdapterTests
        AdapterTests.setUpClass()
        audit=AdapterTests('test_default_adapter_matches_frozen_subprocess_on_140_public_roots')
        audit.test_default_adapter_matches_frozen_subprocess_on_140_public_roots()

if __name__=='__main__':unittest.main()
