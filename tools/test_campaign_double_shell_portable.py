"""Portable qualification of frozen C22 native deployment policies."""
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
from feldmarschall import Engine,Position,parse_square
from information_strategy_cycle import digest
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

DIRECTORY=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-22-double-bomb-shell'
POLICIES=('student-fortress-deployment-v1-normal','student-double-bomb-shell-v1-normal')
SOURCE_SHA='73fb906cb4db1889b028d88e994a582607da716858fe813556a4cf17a821f19e'

class FrozenDoubleShellPortableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'docs/ai-honest-campaign-2026-10-15/research/deployment-double-shell/geometry-and-history.json'
        layouts=json.loads(path.read_text())['existing_and_candidate_layouts']
        cls.expected={POLICIES[0]:layouts['Fortress']['setup'],POLICIES[1]:layouts['DoubleShellFortress']['setup']}
        with Tournament(ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour') as saved:cls.game=saved.game(9)
        cls.states,_=replay(cls.game);cls.events=public_events(cls.game,cls.states)
        cls.evidence=dict(scope='Portable frozen-native mechanism checks; no new strength games.',
            test_source_sha256=digest(Path(__file__)),policies={})
    @classmethod
    def tearDownClass(cls):
        (DIRECTORY/'portable-qualification.json').write_text(json.dumps(cls.evidence,indent=2)+'\n')
    def portable(self,identity,tmp):
        program,_=build_policy(identity);target=Path(tmp)/identity;shutil.copytree(program.parent,target)
        return target/program.name
    def bot(self,program,tmp):
        with patch('feldmarschall.ROOT',Path(tmp)):return Engine(shlex.quote(str(program)))
    def test_frozen_receipts_sources_and_archive_integrity(self):
        frozen=json.loads((DIRECTORY/'frozen-policies.json').read_text())
        for identity in POLICIES:
            spec=get_policy(identity);self.assertEqual(spec,frozen[identity]);self.assertFalse(receives_opponent_setup(spec))
            program,receipt=build_policy(identity);self.assertEqual(receipt['policy'],spec)
            self.assertEqual(digest(ROOT/spec['archive']),spec['source_sha256'])
            self.assertEqual(digest(program),receipt['executable_sha256'])
            for name,sha in receipt['runtime_sha256'].items():self.assertEqual(digest(program.parent/name),sha)
            with zipfile.ZipFile(ROOT/spec['archive']) as archive:
                import hashlib
                self.assertEqual(hashlib.sha256(archive.read('src/core/ai_deploy.c')).hexdigest(),SOURCE_SHA)
            self.evidence['policies'][identity]=dict(integrity=True,archive_sha256=spec['source_sha256'],
                runtime_sha256=receipt['runtime_sha256'],deployment_source_sha256=SOURCE_SHA)
    def test_outside_checkout_identity_exact_own_setup_and_legal_initial_moves(self):
        for identity in POLICIES:
            records=[]
            with tempfile.TemporaryDirectory(prefix='portable-double-shell-') as tmp:
                program=self.portable(identity,tmp)
                result=subprocess.run([str(program),'--identity'],cwd=tmp,capture_output=True,text=True,check=True)
                self.assertEqual(result.stdout.strip(),identity)
                bot=self.bot(program,tmp)
                try:
                    for army in (0,1):
                        for seed in (1,17,791,239001):
                            for line in ('new '+('red','blue')[army],'rules 0','difficulty normal','seed '+str(seed)):bot.send(line)
                            own=bot.ask('setup','setup');self.assertEqual(own,self.expected[identity])
                            selected=tuple(map(parse_square,bot.ask('go','move').split()))
                            position=Position();position.place(army,own);position.place(1-army,self.game[('blue_setup','red_setup')[army]])
                            self.assertIn(selected,position.moves(army))
                            records.append(dict(army=army,seed=seed,setup_exact=True,legal_selected=list(selected)))
                finally:bot.close()
            self.evidence['policies'].setdefault(identity,{})['portable_initial_records']=records
    def test_public_history_strict_move_and_rng_parity_after_identical_own_setup(self):
        records=[]
        with tempfile.TemporaryDirectory(prefix='portable-double-shell-history-') as tmp:
            programs=[self.portable(identity,tmp) for identity in POLICIES]
            for army in (0,1):
                bots=[self.bot(program,tmp) for program in programs]
                try:
                    for identity,bot in zip(POLICIES,bots):
                        for line in ('new '+('red','blue')[army],'rules 0','difficulty normal','seed 2391003'):bot.send(line)
                        # Consume each frozen policy's genuine own deployment.
                        # Then force identical own ranks without resetting RNG.
                        self.assertEqual(bot.ask('setup','setup'),self.expected[identity])
                        bot.send('setup '+self.game[('red_setup','blue_setup')[army]])
                    for ply,event in enumerate(self.events[:120]):
                        if ply%2==army:
                            moves=[tuple(map(parse_square,bot.ask('go','move').split())) for bot in bots]
                            self.assertEqual(moves[0],moves[1]);position=Position();position.cells=self.states[ply][:]
                            self.assertIn(moves[0],position.moves(army))
                            records.append(dict(army=army,ply=ply,selected=list(moves[0]),legal=True,identical=True))
                        for bot in bots:bot.send(event)
                finally:
                    for bot in bots:bot.close()
        self.assertEqual(len(records),120)
        self.evidence['public_history_parity']=dict(events_per_side=120,decisions=120,
            own_setup_generated_before_forcing_common_army=True,rng_not_reset_after_own_generation=True,records=records)

if __name__=='__main__':unittest.main()
