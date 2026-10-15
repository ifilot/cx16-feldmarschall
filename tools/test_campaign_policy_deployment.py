"""Native deployment opt-in, legacy byte parity and forced-army move parity."""
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
import zipfile

from ai_registry import ROOT,get_policy
from feldmarschall import Engine,valid_setup
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


class PolicyDeployment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='feld-policy-deployment-')
        folder=Path(cls.temp.name)
        (folder/'before-source').mkdir()
        original=folder/'before-source/engine.c'
        policy=get_policy('student-guard-v1-normal')
        # Compare against immutable original source, so this remains a useful
        # legacy check after the deployment guard itself has been committed.
        with zipfile.ZipFile(ROOT/policy['archive']) as archive:
            original.write_bytes(archive.read('src/native/engine.c'))
        cls.programs={}
        for name,source,extra in (('before',str(original),[]),('legacy',policy['sources'][0],[]),
                                   ('validated',policy['sources'][0],['AI_POLICY_DEPLOYMENT'])):
            program=folder/name
            command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow',
                     '-DFELDMARSCHALL_AI_ID="deployment-test-v1-normal"','-Isrc/core','-o',str(program)]
            command+=['-D'+define for define in policy['defines']+extra]
            command+=[source]+policy['sources'][1:]
            subprocess.run(command,cwd=ROOT,capture_output=True,check=True)
            cls.programs[name]=program
        # Read the existing validated data, rather than duplicating it by hand.
        text=(ROOT/'src/core/ai_deploy.c').read_text()
        import re
        from feldmarschall import GLYPHS
        arrays=re.findall(r'\{([0-9,]+)\}',text)
        cls.layouts={''.join(GLYPHS[int(rank)] for rank in array.split(',')) for array in arrays}
        assert len(cls.layouts)==3 and all(valid_setup(s) for s in cls.layouts)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def engine(self,name,difficulty='normal'):
        return Engine(shlex.quote(str(self.programs[name]))+' --difficulty '+difficulty)

    def test_default_observer_binary_is_byte_identical_before_and_after_guard(self):
        self.assertEqual(self.programs['before'].read_bytes(),self.programs['legacy'].read_bytes())

    def test_normal_and_hard_select_only_validated_mixture_on_both_sides(self):
        for difficulty in ('normal','hard'):
            engine=self.engine('validated',difficulty)
            try:
                responses={}
                for side in ('red','blue'):
                    selected=set()
                    for seed in range(1,101):
                        for line in ('new '+side,'rules 0','seed '+str(seed)):engine.send(line)
                        setup=engine.ask('setup','setup')
                        self.assertIn(setup,self.layouts);selected.add(setup)
                        if side=='red':responses[seed]=setup
                        else:self.assertEqual(setup,responses[seed])
                    self.assertEqual(selected,self.layouts)
            finally:engine.close()

    def test_easy_keeps_legacy_random_setup_exactly(self):
        engines=[self.engine(name,'easy') for name in ('legacy','validated')]
        try:
            for seed in (1,17,791,239001):
                answers=[]
                for engine in engines:
                    for line in ('new blue','rules 0','seed '+str(seed)):engine.send(line)
                    answers.append(engine.ask('setup','setup'))
                self.assertEqual(answers[0],answers[1]);self.assertTrue(valid_setup(answers[0]))
        finally:
            for engine in engines:engine.close()

    def test_fixed_armies_keep_120_forced_history_moves_identical(self):
        source=ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour'
        with Tournament(source) as tournament:game=tournament.game(9)
        states,_=replay(game);events=public_events(game,states)
        tested=0
        for side in (0,1):
            engines=[self.engine(name) for name in ('legacy','validated')]
            try:
                for engine in engines:
                    for line in ('new '+('red','blue')[side],'rules 0','seed 2391003',
                                 'setup '+game[('red_setup','blue_setup')[side]]):engine.send(line)
                for ply,event in enumerate(events[:120]):
                    if ply%2==side:
                        outputs=[engine.ask('go','move') for engine in engines]
                        self.assertEqual(outputs[0],outputs[1])
                        tested+=1
                    for engine in engines:engine.send(event)
            finally:
                for engine in engines:engine.close()
        self.assertEqual(tested,120)


if __name__=='__main__':unittest.main()
