"""Double-shell deployment certificates, native routing and default identity."""
import json
import ctypes
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
import zipfile

from ai_registry import ROOT,get_policy
from feldmarschall import Engine,valid_setup
from research_deployment_double_shell import geometry

EVIDENCE=ROOT/'docs/ai-honest-campaign-2026-10-15/research/deployment-double-shell'

class DoubleShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='double-shell-build-');folder=Path(cls.temp.name)
        spec=get_policy('student-validated-deployment-v1-normal');cls.programs={}
        original=folder/'ai_deploy.c'
        with zipfile.ZipFile(ROOT/spec['archive']) as archive:original.write_bytes(archive.read('src/core/ai_deploy.c'))
        for name,extra in [('before',[]),('default',[]),('control',['AI_DEPLOY_FORTRESS_ONLY']),
                           ('candidate',['AI_DEPLOY_FORTRESS_ONLY','AI_DEPLOY_DOUBLE_SHELL'])]:
            sources=[str(original) if source=='src/core/ai_deploy.c' and name=='before' else source for source in spec['sources']]
            command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow','-Isrc/core',
                     '-DFELDMARSCHALL_AI_ID="double-shell-research"']+['-D'+d for d in spec['defines']+extra]
            program=folder/name;subprocess.run(command+sources+['-o',str(program)],cwd=ROOT,capture_output=True,check=True)
            cls.programs[name]=program
        data=json.loads((EVIDENCE/'geometry-and-history.json').read_text())['existing_and_candidate_layouts']
        cls.base=data['Fortress']['setup'];cls.candidate=data['DoubleShellFortress']['setup']
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def engine(self,name):return Engine(shlex.quote(str(self.programs[name])))
    def setup(self,bot,side,seed,difficulty='normal',rules=0):
        for line in ('new '+side,'rules '+str(rules),'difficulty '+difficulty,'seed '+str(seed)):bot.send(line)
        return bot.ask('setup','setup')
    def test_default_binary_byte_identical_to_frozen_validated_deployment(self):
        self.assertEqual(self.programs['before'].read_bytes(),self.programs['default'].read_bytes())
    def test_candidate_requires_matched_fixed_fortress_control(self):
        result=subprocess.run(['gcc','-E','-Isrc/core','-DAI_DEPLOY_DOUBLE_SHELL',
                               'src/core/ai_deploy.c'],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('requires the matched AI_DEPLOY_FORTRESS_ONLY control',result.stderr)
    def test_exact_three_swaps_inventory_fixed_flag_spy_and_front_row(self):
        a,b=self.base,self.candidate
        self.assertTrue(valid_setup(b));self.assertEqual(sorted(a),sorted(b));self.assertEqual(a[:10],b[:10])
        self.assertEqual(a.index('F'),b.index('F'));self.assertEqual(a.index('S'),b.index('S'))
        self.assertEqual({i for i in range(40) if a[i]!=b[i]},{10,28,21,33,32,37})
        self.assertFalse(geometry(b)['trapped_mobile_squares'])
    def test_two_disjoint_bomb_vertex_cuts(self):
        inner={20,31};outer={10,21,32};self.assertFalse(inner&outer)
        self.assertTrue(all(self.candidate[i]=='B' for i in inner|outer))
        self.assertEqual(geometry(self.candidate)['min_bomb_captures_from_front'],2)
        for cut in (inner,outer):
            # Keeping only this cut and replacing every other Bomb by mobile
            # units still separates every front entry from the Flag.
            seen=set(range(10))-cut;todo=list(seen)
            while todo:
                sq=todo.pop();r,c=divmod(sq,10)
                for nxt in (sq-10 if r else -1,sq+10 if r<3 else -1,sq-1 if c else -1,sq+1 if c<9 else -1):
                    if nxt>=0 and nxt not in cut and nxt not in seen:seen.add(nxt);todo.append(nxt)
            self.assertNotIn(30,seen)
    def test_classic_both_sides_many_seeds_exact_arm_and_unchanged_rng(self):
        bots={name:self.engine(name) for name in ('control','candidate')}
        try:
            for difficulty in ('normal','hard'):
                for side in ('red','blue'):
                    for seed in range(1,101):
                        for name,bot in bots.items():
                            self.assertEqual(self.setup(bot,side,seed,difficulty),self.base if name=='control' else self.candidate)
                            # Explicit same army erases deployment differences;
                            # ensuing random-consuming native decisions expose
                            # any accidental extra RNG draw in setup.
                            bot.send('setup '+self.base)
                        self.assertEqual(bots['control'].ask('go','move'),bots['candidate'].ask('go','move'))
        finally:
            for bot in bots.values():bot.close()
    def test_easy_and_optional_rules_keep_default_random_setup(self):
        bots={name:self.engine(name) for name in ('default','control','candidate')}
        try:
            for difficulty,rules in [('easy',0),('normal',1)]:
                for side in ('red','blue'):
                    for seed in (1,23,9123,239001):
                        answers=[self.setup(bot,side,seed,difficulty,rules) for bot in bots.values()]
                        self.assertTrue(valid_setup(answers[0]));self.assertEqual(len(set(answers)),1)
        finally:
            for bot in bots.values():bot.close()

    def test_real_setup_function_independent_of_enemy_board_contents(self):
        folder=Path(self.temp.name);stub=folder/'private_input_probe.c'
        stub.write_text('''#include <stdint.h>
#include "board.h"
#include "ai.h"
#include "setup.h"
uint8_t board[SQUARES], game_rules=0, ai_difficulty=AI_NORMAL;
uint16_t random_next(void) { return 123u; }
void setup_random(uint8_t blue) { (void)blue; }
''')
        library=folder/'probe.so'
        subprocess.run(['gcc','-O2','-shared','-fPIC','-Wno-unknown-pragmas','-Isrc/core',
                        '-DAI_DEPLOY_FORTRESS_ONLY','-DAI_DEPLOY_DOUBLE_SHELL',
                        'src/core/ai_deploy.c',str(stub),'-o',str(library)],cwd=ROOT,check=True,capture_output=True)
        native=ctypes.CDLL(str(library));cells=(ctypes.c_uint8*100).in_dll(native,'board')
        for blue in (0,1):
            own=[(3-i//10)*10+i%10 if blue else 60+i for i in range(40)]
            outputs=[]
            for salt in (0,1,7,11,31,91,254):
                for sq in range(100):cells[sq]=(sq*17+salt)%256
                before=list(cells);native.setup_ai(blue)
                outputs.append([cells[sq] for sq in own])
                self.assertTrue(all(cells[sq]==before[sq] for sq in range(100) if sq not in own))
            self.assertTrue(all(values==outputs[0] for values in outputs))

if __name__=='__main__':unittest.main()
