"""Opponent knowledge of our own Flag/Spy never reveals enemy ranks to us."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from ai_registry import ROOT, get_policy
from feldmarschall import LAKES


class InformedOpponent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='informed-opponent-')
        cls.programs = {}
        policy = get_policy('teacher-context-v1-normal')
        for mode, extra in (('base', []), ('informed', ['AI_ROLLOUT_INFORMED_OPPONENT'])):
            path = Path(cls.temp.name)/mode
            subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Isrc/core',
                            *['-D'+d for d in policy['teacher_defines']+extra],
                            '-o',str(path),*policy['teacher_sources']],cwd=ROOT,
                           check=True,capture_output=True)
            cls.programs[mode] = path

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def search(self, mode, root, pieces):
        cells = [254 if sq in LAKES else 255 for sq in range(100)]
        for sq, cell in pieces.items(): cells[sq] = cell
        result = subprocess.run([str(self.programs[mode]),'--audit'],
                    input=f'search {root} 3 {bytes(cells).hex()} ffffffff0000\n',
                    capture_output=True,text=True,check=True,timeout=20)
        rows = [line.split() for line in result.stdout.splitlines()]
        self.assertFalse(any(row[0]=='error' for row in rows))
        return [r for r in rows if r[0]=='decision']

    def test_only_opponent_initial_view_receives_root_flag_and_spy(self):
        for root in (0,1):
            pieces = {99:11,80:9,64:0,90:6,0:16|11,19:16|9,20:16|8,54:16|4}
            if root:
                pieces = {99-sq: cell^16 for sq,cell in pieces.items()}
            base, informed = (self.search(mode,root,pieces) for mode in ('base','informed'))
            root_view = next(bytes.fromhex(r[4]) for r in base if int(r[1])==root)
            enemy_view = next(bytes.fromhex(r[4]) for r in base if int(r[1])!=root)
            for row in informed:
                view = bytes.fromhex(row[4])
                if int(row[1])==root:
                    self.assertEqual(view,root_view)
                else:
                    for sq, cell in enumerate(enemy_view):
                        true = pieces.get(sq)
                        if true is not None and bool(true&16)==bool(root) and true&15 in (9,11):
                            self.assertEqual(view[sq],true|32)
                        else:
                            self.assertEqual(view[sq],cell)

    def test_artificial_opponent_disclosures_never_enter_public_trajectory(self):
        pieces = {99:11,80:9,64:0,90:6,0:16|11,19:16|9,20:16|8,54:16|4}
        rows = self.search('informed',0,pieces)
        self.assertTrue(any(int(r[1])==1 for r in rows))
        for row in rows:
            if row[5]=='-': continue
            events = bytes.fromhex(row[5])
            for i in range(0,len(events),5):
                src,dst,attacker,defender,outcome = events[i:i+5]
                distance=abs(src//10-dst//10)+abs(src%10-dst%10)
                if defender==255 and distance==1:
                    self.assertEqual(attacker,255)

    def test_other_concealed_root_ranks_remain_masked_to_opponent(self):
        first = {99:11,80:9,64:0,90:6,0:16|11,19:16|9,20:16|8,54:16|4}
        second = dict(first);second[64],second[90]=second[90],second[64]
        def initial_decision(pieces):
            return next(row for row in self.search('informed',0,pieces) if row[1:3]==['1','0'])
        self.assertEqual(initial_decision(first),initial_decision(second))


if __name__=='__main__':unittest.main()
