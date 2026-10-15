"""Real CLI/direct adapter checks for public correlated setup beliefs."""
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
from feldmarschall import Engine,parse_square
from teacher_bot import TeacherBot
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

MODEL=ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json'
CONTROL=ROOT/'ai/models/flag-row-prior-control-v1.json'


class JointAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program,_=build_policy('teacher-context-v1-normal');cls.bundle=program.parent
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:
            cls.game=saved.game(9)
        cls.states,_=replay(cls.game);cls.events=public_events(cls.game,cls.states)

    def bot(self,model=MODEL):
        return TeacherBot(self.bundle/'observer',self.bundle/'teacher',samples=8,depth=4,
                          blend='correction',strategic=True,context=True,joint_belief_model=model)

    def send(self,bot,line):
        bot.joint_model.observe(line.split());bot.observer.send(line)

    def initialize(self,bot,army):
        bot.rng.seed(917)
        for line in ['new '+('red','blue')[army],'seed 917','rules 0','difficulty normal',
                     'setup '+self.game[('red_setup','blue_setup')[army]]]:self.send(bot,line)

    def cli(self,model=MODEL):
        args=[sys.executable,str(ROOT/'tools/teacher_bot.py'),'--observer',str(self.bundle/'observer'),
              '--teacher',str(self.bundle/'teacher'),'--samples','8','--depth','4','--blend','correction',
              '--strategic','--context','--joint-belief-model',str(model)]
        return Engine(shlex.join(args))

    def test_real_cli_matches_direct_adapter_on_both_public_prefixes(self):
        for model in (MODEL,CONTROL):
            for army in (0,1):
                bot=self.bot(model);cli=self.cli(model)
                try:
                    self.initialize(bot,army)
                    for line in ['new '+('red','blue')[army],'seed 917','rules 0','difficulty normal',
                                 'setup '+self.game[('red_setup','blue_setup')[army]]]:cli.send(line)
                    for ply,event in enumerate(self.events[:96]):
                        if ply%8==army:
                            self.assertIs(bot.world_sampler,bot.joint_model)
                            with patch.object(bot.joint_model,'sample_worlds',wraps=bot.joint_model.sample_worlds) as sample:
                                move=bot.choose();self.assertEqual(sample.call_count,1)
                            self.assertEqual(move,tuple(map(parse_square,cli.ask('go','move').split())))
                            self.assertEqual(cli.ask('public','public'),bot.observer.ask('public','public'))
                        self.send(bot,event);cli.send(event)
                finally:bot.close();cli.close()

    def test_hidden_nibble_mutations_preserve_complete_reports_after_history(self):
        for model in (MODEL,CONTROL):
            for army in (0,1):
                reports=[]
                for mutate in (False,True):
                    bot=self.bot(model)
                    try:
                        self.initialize(bot,army)
                        for event in self.events[:80]:self.send(bot,event)
                        if mutate:
                            original=bot.observer.ask
                            def masked_response(line,prefix):
                                value=original(line,prefix)
                                if line=='public':
                                    side,board,lost,shuttle=value.split();cells=list(bytes.fromhex(board))
                                    for sq,cell in enumerate(cells):
                                        if cell<254 and bool(cell&16)!=bool(army) and not cell&32:cells[sq]=(cell&240)|(sq%12)
                                    return ' '.join((side,bytes(cells).hex(),lost,shuttle))
                                return value
                            with patch.object(bot.observer,'ask',side_effect=masked_response):bot.choose()
                        else:bot.choose()
                        reports.append(copy.deepcopy(bot.last_report))
                    finally:bot.close()
                self.assertEqual(reports[0],reports[1])

    def test_cli_new_resets_public_memory_and_repeats_deterministic_game(self):
        cli=self.cli()
        try:
            moves=[]
            for repeat in range(2):
                for line in ['new red','seed 917','setup '+self.game['red_setup']]:cli.send(line)
                moves.append(cli.ask('go','move'))
                for event in self.events[:40]:cli.send(event)
            self.assertEqual(moves[0],moves[1])
        finally:cli.close()

    def test_model_ablation_keeps_identical_priors_and_training_provenance(self):
        joint=json.loads(MODEL.read_text());control=json.loads(CONTROL.read_text())
        self.assertEqual(joint['weights'],control['weights']);self.assertEqual(joint['phi'],control['phi'])
        self.assertEqual(joint['training'],control['training']);self.assertEqual(control['theta'],[0.,0.])
        self.assertNotEqual(joint['theta'],control['theta'])

    def test_joint_mode_rejects_privilege_and_other_experiment_combinations(self):
        for option in [dict(diagnostic_truth=True),dict(information_strategy='lifetime'),
                       dict(world_sampling='latin'),dict(campaign_strategy='activation'),
                       dict(paired_confidence=True),dict(adaptive_depth=True),dict(belief_model='unused')]:
            with self.assertRaisesRegex(ValueError,'isolate'):
                TeacherBot('unused','unused',joint_belief_model=MODEL,**option)

    def test_registered_joint_policies_run_from_portable_copied_bundles(self):
        policies=[p for p in catalog() if '--joint-belief-model' in p.get('driver_args',[])]
        if not policies:self.skipTest('joint recipes not registered yet; rerun after freeze')
        self.assertGreaterEqual(len(policies),2)
        for policy in policies:
            self.assertFalse(receives_opponent_setup(policy))
            program,_=build_policy(policy['id'])
            with tempfile.TemporaryDirectory(prefix='portable-joint-') as tmp:
                portable=Path(tmp)/'bundle';shutil.copytree(program.parent,portable)
                executable=portable/program.name
                # Start outside the checkout as well as copying outside it;
                # successful imports must come from the frozen portable bundle.
                with patch('feldmarschall.ROOT',Path(tmp)):
                    bot=Engine(shlex.quote(str(executable)))
                try:
                    for command in ['new red','seed 917','setup '+self.game['red_setup']]:bot.send(command)
                    move=bot.ask('go','move');self.assertEqual(len(move.split()),2)
                    for event in self.events[:80]:bot.send(event)
                    self.assertEqual(len(bot.ask('go','move').split()),2)
                finally:bot.close()


if __name__=='__main__':unittest.main()
