"""Exact original startup capture, both deployment branches and private inputs."""
from collections import Counter
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from ai_registry import ROOT
from campaign_dos_deployment import (EXPECTED,ORIGINAL_COUNTS,_cpu,generate_setup,
                                     load_assets,rng_next,templates)
from feldmarschall import valid_setup

ASSETS=ROOT/'ai/msdos1990'
SETUP_ASSETS=ROOT/'docs/ai-honest-campaign-2026-10-15/research/dos-deployment-original-v1'


def flag_can_reach_front_without_bomb(ranks):
    seen={ranks.index(0)};queue=list(seen)
    for square in queue:
        row,col=divmod(square,10)
        if row==3:return True
        for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
            r,c=row+dr,col+dc;other=r*10+c
            if 0<=r<4 and 0<=c<10 and other not in seen and ranks[other]!=11:
                seen.add(other);queue.append(other)
    return False


class OriginalDeployment(unittest.TestCase):
    def test_entire_captured_real_startup_dgroup_matches_original_return(self):
        entry=(SETUP_ASSETS/'BOARD-ENTRY-DS.BIN').read_bytes()
        expected=(SETUP_ASSETS/'BOARD-RETURN-DS.BIN').read_bytes()
        self.assertEqual(hashlib.sha256(entry).hexdigest(),'6656e1591176efb58e5f78c16aabe18221eb4a8d78347d8c49e64fc1fe0a337f')
        self.assertEqual(hashlib.sha256(expected).hexdigest(),'1958ffea95187486cad49cef292fc0455d29236bcd8288f3aa735ed14e0bdeb3')
        cpu=_cpu(ASSETS,load_assets(ASSETS,SETUP_ASSETS));cpu.write(0x1800,entry)
        seed=cpu.word(0x3544)|(cpu.word(0x3546)<<16);level=cpu.word(0x3e90)
        self.assertEqual((seed,level),(0x25768654,1))
        cpu.call(0x1ddd,(0x0100,))  # original capture: AH nonzero, low byte zero
        self.assertEqual(cpu.read(0x1800,len(expected)),expected)
        setup,audit=generate_setup(ASSETS,seed,level,SETUP_ASSETS)
        self.assertTrue(valid_setup(setup));self.assertEqual(audit['post_rng_state'],0x33472c32)
        self.assertEqual(audit['physical_ranks'],[cpu.word(0x3e9e+72*r+6*c) for r in range(1,5) for c in range(1,11)])

    def test_colonel_table_branch_matches_exact_table_mirror_and_three_rng_draws(self):
        original=templates(ASSETS,SETUP_ASSETS);seen=set();checked=0
        for seed in range(1,97):
            state,first=rng_next(seed)
            if first%5==0:continue
            state,which=rng_next(state);state,mirror=rng_next(state)
            index=which%4+4;mirrored=bool(mirror%2)
            values=original[index]
            if mirrored:values=[v for row in range(4) for v in reversed(values[10*row:10*(row+1)])]
            setup,audit=generate_setup(ASSETS,seed,3,SETUP_ASSETS)
            self.assertEqual(audit['physical_ranks'],values)
            self.assertEqual(audit['post_rng_state'],state)
            self.assertEqual((audit['template_index'],audit['mirrored']),(index,mirrored))
            self.assertTrue(valid_setup(setup));seen.add((index,mirrored));checked+=1
        self.assertGreater(checked,50);self.assertEqual(len(seen),8)

    def test_procedural_and_template_paths_all_difficulties_return_legal_inventory(self):
        branches=Counter()
        for level in range(1,6):
            for seed in range(1,25):
                setup,audit=generate_setup(ASSETS,seed,level,SETUP_ASSETS)
                self.assertTrue(valid_setup(setup))
                self.assertEqual(Counter(audit['physical_ranks']),dict(enumerate(ORIGINAL_COUNTS)))
                branches[level,audit['branch']]+=1
                if level==3:
                    self.assertEqual(audit['physical_ranks'].index(0)//10,0)
                    self.assertFalse(flag_can_reach_front_without_bomb(audit['physical_ranks']))
        for level in (3,4,5):
            self.assertGreater(branches[level,'original-procedural'],0)
            self.assertGreater(branches[level,'original-template'],0)
        for level in (1,2):self.assertEqual(branches[level,'original-template'],0)

    def test_all_eight_fixed_original_tables_have_complete_adjacent_bomb_screens(self):
        for values in templates(ASSETS,SETUP_ASSETS):
            flag=values.index(0);row,col=divmod(flag,10)
            self.assertEqual(row,0)
            adjacent=[(row+dr,col+dc) for dr,dc in ((-1,0),(1,0),(0,-1),(0,1))
                      if 0<=row+dr<4 and 0<=col+dc<10]
            self.assertTrue(all(values[r*10+c]==11 for r,c in adjacent))

    def test_only_own_private_rng_and_difficulty_are_inputs_and_calls_are_deterministic(self):
        a=generate_setup(ASSETS,0xffffffff,3,SETUP_ASSETS)
        b=generate_setup(ASSETS,0xffffffff,3,SETUP_ASSETS)
        self.assertEqual(a,b)
        with self.assertRaises(TypeError):generate_setup(ASSETS,1,opponent_setup='forbidden')
        for bad in (-1,0x100000000,True,1.5):
            with self.assertRaises(ValueError):generate_setup(ASSETS,bad,3,SETUP_ASSETS)
        for bad in (0,6,True,2.5):
            with self.assertRaises(ValueError):generate_setup(ASSETS,1,bad,SETUP_ASSETS)

    def test_frozen_asset_archive_is_portable_and_identical_without_split_paths(self):
        archive=SETUP_ASSETS/'generator-assets.zip'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),
                         '258ca0750bdabff2b4e052ab78c6c5ed28db3140daa8b956366720eef63d1a0c')
        with tempfile.TemporaryDirectory(prefix='dos-setup-portable-') as temporary:
            with zipfile.ZipFile(archive) as bundle:bundle.extractall(temporary)
            self.assertEqual(generate_setup(temporary,0x25768654,1),
                             generate_setup(ASSETS,0x25768654,1,SETUP_ASSETS))

    def test_changed_original_assets_rejected_before_execution_and_files_unchanged(self):
        before={name:hashlib.sha256(((SETUP_ASSETS if name.startswith('ovl6.') else ASSETS)/name).read_bytes()).hexdigest()
                for name in EXPECTED}
        with tempfile.TemporaryDirectory(prefix='dos-setup-corrupt-') as temporary:
            folder=Path(temporary)
            for name in ('ovl6.cod','ovl6.rel'):shutil.copy2(SETUP_ASSETS/name,folder/name)
            code=bytearray((folder/'ovl6.cod').read_bytes());code[0]^=1;(folder/'ovl6.cod').write_bytes(code)
            with self.assertRaisesRegex(ValueError,'integrity'):generate_setup(ASSETS,1,3,folder)
        generate_setup(ASSETS,2,3,SETUP_ASSETS)
        after={name:hashlib.sha256(((SETUP_ASSETS if name.startswith('ovl6.') else ASSETS)/name).read_bytes()).hexdigest()
               for name in EXPECTED}
        self.assertEqual(before,after)


if __name__=='__main__':unittest.main()
