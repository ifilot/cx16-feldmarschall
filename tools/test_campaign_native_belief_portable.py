"""Frozen native-belief policies remain portable and tied to immutable inputs."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from ai_registry import ROOT,build_policy,get_policy,receives_opponent_setup
from feldmarschall import Engine
from information_strategy_cycle import digest
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

POLICIES=('student-counts-belief-objectives-v3-normal','student-joint-belief-objectives-v3-normal')
DIRECTORY=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-16-native-belief-objectives-v3'


class NativeBeliefPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:
            cls.game=saved.game(9)
        states,_=replay(cls.game);cls.events=public_events(cls.game,states)

    def test_archive_receipt_model_and_current_driver_identity(self):
        frozen=json.loads((DIRECTORY/'frozen-policies.json').read_text())
        evidence={}
        for identity in POLICIES:
            spec=get_policy(identity);self.assertEqual(spec,frozen[identity]);self.assertFalse(receives_opponent_setup(spec))
            program,receipt=build_policy(identity)
            self.assertEqual(receipt['policy'],spec)
            self.assertEqual(digest(ROOT/spec['archive']),spec['source_sha256'])
            self.assertEqual(digest(program),receipt['executable_sha256'])
            for name,sha in receipt['runtime_sha256'].items():self.assertEqual(digest(program.parent/name),sha)
            with zipfile.ZipFile(ROOT/spec['archive']) as archive:
                for name in ('campaign_native_beliefs.py','campaign_belief_values.py','campaign_joint_beliefs.py',
                             'calibrated_beliefs.py','feldmarschall.py'):
                    self.assertEqual(archive.read('tools/'+name),(program.parent/name).read_bytes())
                self.assertEqual((ROOT/'tools/campaign_native_beliefs.py').read_bytes(),(program.parent/'campaign_native_beliefs.py').read_bytes())
                model=Path(spec['joint_belief_model'])
                self.assertEqual(archive.read(str(model)),(program.parent/model.name).read_bytes())
                self.assertEqual(digest(program.parent/model.name),spec['joint_belief_model_sha256'])
            evidence[identity]=dict(source_sha256=spec['source_sha256'],runtime_sha256=receipt['runtime_sha256'],
                model_sha256=spec['joint_belief_model_sha256'],current_driver_equals_frozen=True)
        (DIRECTORY/'native-frozen-integrity.json').write_text(json.dumps(dict(passed=True,policies=evidence,
            test_source_sha256=digest(Path(__file__))),indent=2)+'\n')

    def test_retained_unqualified_versions_reject_the_public_protocol(self):
        for identity in POLICIES:
            for version in (1,2):
                previous=identity.replace('-v3-',f'-v{version}-');spec=get_policy(previous)
                self.assertNotIn('AI_DIAGNOSTICS',spec['defines'])
                program,_=build_policy(previous)
                response=subprocess.run([str(program.parent/'observer')],input='public\nquit\n',
                    text=True,capture_output=True,check=True)
                self.assertIn('error unknown command',response.stdout)
                self.assertNotIn('public ',response.stdout)

    def test_frozen_launchers_identity_setup_and_public_history_outside_checkout(self):
        for identity in POLICIES:
            program,_=build_policy(identity)
            for army in (0,1):
                with tempfile.TemporaryDirectory(prefix='portable-native-beliefs-') as tmp:
                    portable=Path(tmp)/'runtime';shutil.copytree(program.parent,portable)
                    executable=portable/program.name
                    result=subprocess.run([str(executable),'--identity'],cwd=tmp,text=True,capture_output=True,check=True)
                    self.assertEqual(result.stdout.strip(),identity)
                    with patch('feldmarschall.ROOT',Path(tmp)):bot=Engine(shlex.quote(str(executable)))
                    try:
                        for command in ['new '+('red','blue')[army],'rules 0','difficulty normal','seed 1729',
                                        'setup '+self.game[('red_setup','blue_setup')[army]]]:bot.send(command)
                        first=bot.ask('go','move');self.assertEqual(len(first.split()),2)
                        for event in self.events[:80]:bot.send(event)
                        self.assertEqual(len(bot.ask('go','move').split()),2)
                        public=bot.ask('public','public').split();self.assertEqual(int(public[0]),army)
                        for cell in bytes.fromhex(public[1]):
                            if cell<254 and bool(cell&16)!=bool(army) and not cell&32:self.assertEqual(cell&15,12)
                        bot.send('new '+('red','blue')[army]);bot.send('seed 1729')
                        bot.send('setup '+self.game[('red_setup','blue_setup')[army]])
                        self.assertEqual(bot.ask('go','move'),first)
                    finally:bot.close()


if __name__=='__main__':unittest.main()
