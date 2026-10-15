"""Behavioral checks for original instructions, state continuity and DOS transport."""
import json
from pathlib import Path
import random
import shlex
import subprocess
import tempfile
import unittest

from ai_registry import ROOT,build_policy
from feldmarschall import Engine,Position,random_setup,new_rng,GLYPHS,FLAG
from msdos1990 import OriginalAI,OriginalCPU,ORIGINAL_RANK

ASSETS=ROOT/'ai/msdos1990'

class OriginalExecution(unittest.TestCase):
    def test_fast_jit_matches_frozen_instruction_counted_core(self):
        import importlib.util
        executable,_=build_policy('msdos-1990-v1-normal')
        spec=importlib.util.spec_from_file_location('original1990_counted_reference',executable.parent/'msdos1990.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for side in (0,1):
            rng=new_rng(2346+side);setups=[random_setup(rng),random_setup(rng)]
            reference=module.OriginalAI(ASSETS,side,setups,31)
            fast=OriginalAI(ASSETS,side,setups,31)
            self.assertEqual(reference.cpu.checkpoint(),fast.cpu.checkpoint())
            for ply in range(200):
                legal=fast.position.moves(ply%2)
                if not legal:break
                if ply%2==side:
                    chosen=reference.choose();self.assertEqual(fast.choose(),chosen)
                    self.assertEqual(reference.cpu.checkpoint(),fast.cpu.checkpoint())
                else:chosen=rng.choice(legal)
                src,dst=chosen;cell=fast.position.cells[dst]
                if cell:
                    a,d=fast.position.cells[src][1],cell[1]
                    reference.observe(src,dst,a,d);fast.observe(src,dst,a,d)
                    if d==FLAG:break
                else:reference.observe(src,dst);fast.observe(src,dst)
                self.assertEqual(reference.cpu.checkpoint(),fast.cpu.checkpoint())

    def test_original_geometry_and_resident_rng(self):
        cpu=OriginalCPU(ASSETS)
        for row in range(-2,12):
            for col in range(-2,12):
                expected=0<=row<10 and 0<=col<10 and not(row in (4,5) and col in (2,3,6,7))
                self.assertEqual(bool(cpu.call(0x1569,(row,col))),expected)
        state=65535;cpu.put_word(0x3544,state);cpu.put_word(0x3546,0)
        for _ in range(1000):
            state=(state*0x015a4e35+1)&0xffffffff
            self.assertEqual(cpu.call(0xc07e,segment=0x1000),(state>>16)&32767)
            self.assertEqual(cpu.word(0x3544)|(cpu.word(0x3546)<<16),state)

    def test_initial_knowledge_orientation_and_checkpoint(self):
        rng=new_rng(43199);setups=[random_setup(rng),random_setup(rng)]
        for side in (0,1):
            ai=OriginalAI(ASSETS,side,setups,119)
            self.assertEqual([ai.cpu.word(0x4232+49*i+9) for i in range(40) if ai.cpu.word(0x4232+49*i+9)!=12],[0,10])
            before=ai.cpu.checkpoint();first=ai.choose();after=ai.cpu.checkpoint()
            ai.cpu.restore(before);second=ai.choose()
            self.assertEqual(first,second);self.assertEqual(after,ai.cpu.checkpoint())
            self.assertIn(first,ai.position.moves(side))

    def test_long_histories_match_independent_referee(self):
        production,_=build_policy('student-guard-v1-normal')
        for side in (0,1):
            rng=new_rng(6192+side);setups=[random_setup(rng),random_setup(rng)]
            ai=OriginalAI(ASSETS,side,setups,33)
            engine=Engine(shlex.quote(str(production)))
            truth=Position()
            for army in (0,1):truth.place(army,setups[army])
            engine.send('seed 61');engine.send('new '+('blue' if side==0 else 'red'));engine.send('setup '+setups[1-side])
            battles=0
            try:
                for ply in range(250):
                    army=ply%2
                    if not truth.moves(army):break
                    if army==side:move=ai.choose()
                    else:
                        from feldmarschall import parse_square
                        move=tuple(map(parse_square,engine.ask('go','move').split()))
                    self.assertIn(move,truth.moves(army));src,dst=move
                    from feldmarschall import square_name
                    squares=' '.join(map(square_name,move));target=truth.cells[dst]
                    if target:
                        a,d=truth.cells[src][1],target[1];truth.fight(src,dst,a,d);battles+=1
                        ai.observe(src,dst,a,d);engine.send(f'battle {squares} {GLYPHS[a]} {GLYPHS[d]}')
                        if d==FLAG:break
                    else:
                        truth.move(src,dst);ai.observe(src,dst);engine.send('moved '+squares)
                    self.assertEqual(ai.position.cells,truth.cells)
                    self.assertEqual(ai.position.shuttle,truth.shuttle)
                self.assertGreater(battles,5)
            finally:engine.close()

    def test_frozen_protocol_and_missing_truth_fail_closed(self):
        exe,receipt=build_policy('msdos-1990-v1-normal')
        self.assertEqual(subprocess.check_output([str(exe),'--identity'],text=True).strip(),'msdos-1990-v1-normal')
        rng=new_rng(17);setups=[random_setup(rng),random_setup(rng)]
        broken=subprocess.run([str(exe)],input='feldmarschall\nnew red\nsetup '+setups[0]+'\ngo\n',text=True,capture_output=True,timeout=10)
        self.assertNotEqual(broken.returncode,0);self.assertIn('needs both initial physical armies',broken.stdout)
        command='\n'.join(['feldmarschall','seed 77','new red','setup '+setups[0],'opponent-setup '+setups[1],'go','stats','quit',''])
        good=subprocess.run([str(exe)],input=command,text=True,capture_output=True,timeout=10)
        self.assertEqual(good.returncode,0,good.stderr+good.stdout)
        self.assertIn('move ',good.stdout);self.assertIn('original physical-rank access preserved',good.stdout)
        self.assertTrue(any('/lib/' in name for name in receipt['runtime_sha256']))

if __name__=='__main__':unittest.main()
