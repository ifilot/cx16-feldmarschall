"""Qualify the frozen combination without using strength-validation games."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from ai_registry import ROOT, build_policy, get_policy, receives_opponent_setup
from feldmarschall import Engine, Position, parse_square
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay

BASE = 'student-template-flag-bomb-v1-normal'
COMBO = 'student-fortress-template-flag-bomb-v1-normal'
DIRECTORY = ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-27-fortress-template-combination'


class FortressTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builds = {p: build_policy(p) for p in (BASE, COMBO)}
        with Tournament(ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour') as saved:
            cls.game = saved.game(9)
        cls.states, _ = replay(cls.game)
        cls.events = public_events(cls.game, cls.states)

    def test_only_deployment_define_and_identity_change(self):
        specs = [get_policy(p).copy() for p in (BASE, COMBO)]
        self.assertEqual(set(specs[1]['defines'])-set(specs[0]['defines']), {'AI_DEPLOY_FORTRESS_ONLY'})
        for spec in specs:
            self.assertFalse(receives_opponent_setup(spec))
        receipts = [self.builds[p][1] for p in (BASE, COMBO)]
        for name, sha in receipts[0]['runtime_sha256'].items():
            if name not in ('engine', 'observer'):
                self.assertEqual(sha, receipts[1]['runtime_sha256'][name], name)

    def test_portable_exact_fortress_and_legal_moves_both_colors(self):
        geometry = ROOT/'docs/ai-honest-campaign-2026-10-15/research/deployment-double-shell/geometry-and-history.json'
        expected = json.loads(geometry.read_text())['existing_and_candidate_layouts']['Fortress']['setup']
        program = self.builds[COMBO][0]
        with tempfile.TemporaryDirectory(prefix='fortress-template-') as tmp:
            target = Path(tmp)/'runtime'
            shutil.copytree(program.parent, target)
            executable = target/program.name
            identity = subprocess.run([str(executable), '--identity'], cwd=tmp, capture_output=True, text=True, check=True)
            self.assertEqual(identity.stdout.strip(), COMBO)
            with patch('feldmarschall.ROOT', Path(tmp)):
                bot = Engine(shlex.quote(str(executable)))
            try:
                for army in (0, 1):
                    for seed in (1, 17, 2399761):
                        for command in ('new '+('red', 'blue')[army], 'rules 0', 'seed '+str(seed)):
                            bot.send(command)
                        self.assertEqual(bot.ask('setup', 'setup'), expected)
                        move = tuple(map(parse_square, bot.ask('go', 'move').split()))
                        position = Position()
                        position.place(army, expected)
                        position.place(1-army, self.game[('blue_setup', 'red_setup')[army]])
                        self.assertIn(move, position.moves(army))
            finally:
                bot.close()

    def test_identical_choices_after_common_setup_without_resetting_rng(self):
        for army in (0, 1):
            bots = [Engine(shlex.quote(str(self.builds[p][0]))) for p in (BASE, COMBO)]
            try:
                for bot in bots:
                    for command in ('new '+('red', 'blue')[army], 'rules 0', 'seed 2399871'):
                        bot.send(command)
                    bot.ask('setup', 'setup')
                    bot.send('setup '+self.game[('red_setup', 'blue_setup')[army]])
                for ply, event in enumerate(self.events[:120]):
                    if ply%2 == army:
                        moves = [tuple(map(parse_square, bot.ask('go', 'move').split())) for bot in bots]
                        self.assertEqual(moves[0], moves[1])
                        position = Position()
                        position.cells = self.states[ply][:]
                        self.assertIn(moves[0], position.moves(army))
                    for bot in bots:
                        bot.send(event)
            finally:
                for bot in bots:
                    bot.close()


if __name__ == '__main__':
    unittest.main()
