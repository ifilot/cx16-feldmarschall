"""Rank-capable endpoint routes: native/reference parity and policy isolation."""
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
import zipfile

from ai_registry import ROOT,get_policy
from campaign_routes import geometric_pursuit,capable_pursuit
from feldmarschall import LAKES,COUNTS


def corridor(attacker=8,defender=0):
    cells=[254]*100
    for square in range(5,100,10):cells[square]=255
    cells[5],cells[94],cells[95],cells[55]=16|11,11,attacker,16|defender
    return cells


class CapableRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory(prefix='feld-capable-routes-')
        cls.folder=Path(cls.directory.name)
        policy=get_policy('teacher-context-v1-normal')
        with zipfile.ZipFile(ROOT/policy['archive']) as archive:
            archive.extractall(cls.folder/'source')
        (cls.folder/'source/src/native/teacher_rollout.c').write_bytes((ROOT/'src/native/teacher_rollout.c').read_bytes())
        probe=cls.folder/'source/probe.c'
        probe.write_text('#define main teacher_main\n#include "src/native/teacher_rollout.c"\n#undef main\n'
            'int main(void){char cells[202];game_rules=0;while(scanf("%200s",cells)==1){'
            'if(!hex(cells,board,100))return 2;printf("%d %d\\n",pursuit(0),pursuit(1));}return 0;}\n')
        cls.programs={}
        for mode,extra in (('geometric',[]),('capable',['AI_ROLLOUT_CAPABLE_ROUTES'])):
            for kind in ('probe','teacher'):
                program=cls.folder/(mode+'-'+kind)
                sources=(['probe.c'] if kind=='probe' else policy['teacher_sources'][:1])+policy['teacher_sources'][1:]
                command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I.','-Isrc/core','-o',str(program)]
                command+=['-D'+define for define in policy['teacher_defines']+extra]+sources
                subprocess.run(command,cwd=cls.folder/'source',check=True,capture_output=True)
                cls.programs[(mode,kind)]=program

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def test_stronger_and_equal_defenders_block_the_same_attacker(self):
        for attacker,defender in ((8,0),(3,3)):
            cells=corridor(attacker,defender)
            self.assertEqual(geometric_pursuit(cells,0),-36)
            self.assertEqual(capable_pursuit(cells,0),-400)
        cells=corridor(0,3)
        self.assertEqual(capable_pursuit(cells,0),-36)

    def test_miner_capability_was_already_present_in_old_evaluation(self):
        for attacker,expected in ((7,-36),(3,-400)):
            cells=corridor(attacker,10)
            self.assertEqual(geometric_pursuit(cells,0),expected)
            self.assertEqual(capable_pursuit(cells,0),expected)

    def test_spy_attack_exception_and_friendly_mobile_coordination(self):
        cells=corridor(9,0)
        self.assertEqual(capable_pursuit(cells,0),-36)
        cells[75]=8 # Friendly weaker blocker may move out of the route.
        self.assertEqual(capable_pursuit(cells,0),-36)

    def test_native_matches_reference_on_150_inventory_consistent_worlds(self):
        rng=random.Random(2390021)
        worlds=[]
        legal=[square for square in range(100) if square not in LAKES]
        for _ in range(150):
            cells=[254 if square in LAKES else 255 for square in range(100)]
            squares=rng.sample(legal,80)
            for army in (0,1):
                ranks=[rank for rank,count in enumerate(COUNTS) for _ in range(count)]
                rng.shuffle(ranks)
                # Keep Flag and a random subset of the mobile/nonmobile pieces.
                retained=[rank for rank in ranks if rank==11 or rng.random()<.65]
                for square,rank in zip(squares[army*40:(army+1)*40],retained):
                    cells[square]=rank|(16 if army else 0)
            worlds.append(cells)
        payload=''.join(bytes(cells).hex()+'\n' for cells in worlds)
        for mode,reference in (('geometric',geometric_pursuit),('capable',capable_pursuit)):
            result=subprocess.run([str(self.programs[(mode,'probe')])],input=payload,
                                  capture_output=True,text=True,check=True)
            expected=[(reference(cells,0),reference(cells,1)) for cells in worlds]
            actual=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
            self.assertEqual(expected,actual)

    def test_evaluation_does_not_change_any_masked_rollout_policy_decision(self):
        cells=[254 if square in LAKES else 255 for square in range(100)]
        for square,piece in {99:11,0:16|11,64:5,54:16|8,44:16|3,80:6,90:4}.items():cells[square]=piece
        payload='search 0 4 '+bytes(cells).hex()+' ffffffff0000\n'
        results=[]
        for mode in ('geometric','capable'):
            result=subprocess.run([str(self.programs[(mode,'teacher')]),'--audit','--strategic'],
                                  input=payload,capture_output=True,text=True,check=True)
            results.append([line for line in result.stdout.splitlines() if line.startswith('decision ')])
        self.assertTrue(results[0])
        self.assertEqual(results[0],results[1])
        # Without strategic evaluation the complete search reports also match.
        outputs=[subprocess.run([str(self.programs[(mode,'teacher')])],input=payload,
                  capture_output=True,text=True,check=True).stdout for mode in ('geometric','capable')]
        self.assertEqual(outputs[0],outputs[1])


if __name__=='__main__':unittest.main()
