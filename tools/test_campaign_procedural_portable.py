"""Frozen procedural-policy launchers must carry the intended model portably."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from ai_registry import ROOT, build_policy, get_policy, receives_opponent_setup
from campaign_native_template import NativeTemplateBot
from campaign_procedural_beliefs import ProceduralTemplateBeliefs
from feldmarschall import Engine, Position, parse_square, valid_setup
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay

POLICIES = ('student-template-backrow-background-v1-normal',
            'student-template-structured-background-v1-normal',
            'student-backrow-only-v1-normal')


class ProceduralPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builds = {p: build_policy(p) for p in POLICIES}
        with Tournament(ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour') as saved:
            cls.game = saved.game(9)
        cls.states, _ = replay(cls.game)
        cls.events = public_events(cls.game, cls.states)

    def test_receipts_and_assets_match_frozen_recipes(self):
        for identity, (program, receipt) in self.builds.items():
            spec = get_policy(identity)
            self.assertFalse(receives_opponent_setup(spec))
            self.assertEqual(receipt['policy'], spec)
            model = Path(spec['procedural_belief_model'])
            self.assertEqual(hashlib.sha256((program.parent/model.name).read_bytes()).hexdigest(), spec['procedural_belief_model_sha256'])
            launcher = program.read_text()
            self.assertIn('str(p / '+repr(model.name)+')', launcher)
            self.assertIn('campaign_procedural_beliefs.py', receipt['runtime_sha256'])
            for name, sha in receipt['runtime_sha256'].items():
                self.assertEqual(hashlib.sha256((program.parent/name).read_bytes()).hexdigest(), sha)

    def test_outside_checkout_exact_model_history_choices_both_sides(self):
        for identity, (program, _) in self.builds.items():
            with tempfile.TemporaryDirectory(prefix='procedural-portable-') as tmp:
                target = Path(tmp)/'runtime'
                shutil.copytree(program.parent, target)
                executable = target/program.name
                result = subprocess.run([str(executable), '--identity'], cwd=tmp, capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout.strip(), identity)
                spec = get_policy(identity)
                decisions = 0
                for army in (0, 1):
                    with patch('feldmarschall.ROOT', Path(tmp)):
                        portable = Engine(shlex.quote(str(executable)))
                    reference = NativeTemplateBot(target/'observer', model=ProceduralTemplateBeliefs.load(target/Path(spec['procedural_belief_model']).name))
                    try:
                        for line in ('new '+('red', 'blue')[army], 'rules 0', 'seed 2399961'):
                            portable.send(line)
                            reference.observe(line.split())
                        generated = portable.ask('setup', 'setup')
                        self.assertTrue(valid_setup(generated))
                        self.assertEqual(generated, reference.observe(['setup']))
                        forced = 'setup '+self.game[('red_setup', 'blue_setup')[army]]
                        portable.send(forced)
                        reference.observe(forced.split())
                        for ply, event in enumerate(self.events[:120]):
                            if ply%2 == army:
                                selected = tuple(map(parse_square, portable.ask('go', 'move').split()))
                                self.assertEqual(selected, reference.choose())
                                position = Position()
                                position.cells = self.states[ply][:]
                                self.assertIn(selected, position.moves(army))
                                decisions += 1
                            portable.send(event)
                            reference.observe(event.split())
                    finally:
                        portable.close()
                        reference.close()
                self.assertEqual(decisions, 120)


if __name__ == '__main__':
    unittest.main()
