"""Rational probability oracle and private-rank invariance for compact priors."""
from fractions import Fraction
import ctypes as C
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from ai_registry import ROOT
from feldmarschall import COUNTS, GLYPHS, LAKES, setup_squares

FLAGS = ['AI_MISSIONS', 'AI_MEMORY', 'AI_STUDENT', 'AI_STUDENT_V2',
         'AI_STUDENT_PRODUCTION', 'AI_STUDENT_COOP_GUARD']
SOURCES = ['pieces', 'board', 'rules', 'setup', 'random', 'ai_deploy', 'ai',
           'ai_level', 'ai_mission', 'ai_memory', 'ai_student']


class CompactBackrowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='compact-backrow-tests-')
        path = Path(cls.tmp.name)/'core.so'
        subprocess.run(['gcc', '-shared', '-fPIC', '-O2', '-std=c99', '-Wno-unknown-pragmas',
                        '-Isrc/core', '-DAI_TEST', '-DAI_BACKROW_PRIOR', *['-D'+f for f in FLAGS],
                        '-o', str(path), *['src/core/'+s+'.c' for s in SOURCES]], cwd=ROOT, check=True)
        cls.lib = C.CDLL(str(path))
        cls.board = (C.c_uint8*100).in_dll(cls.lib, 'board')
        cls.rules = C.c_uint8.in_dll(cls.lib, 'game_rules')
        cls.level = C.c_uint8.in_dll(cls.lib, 'ai_difficulty')
        cls.lib.ai_test_backrow_value.argtypes = [C.c_uint8, C.POINTER(C.c_uint8), C.c_uint8, C.c_uint8]
        cls.lib.ai_test_backrow_value.restype = C.c_int16
        cls.lib.ai_test_backrow_gain.argtypes = [C.c_uint8, C.c_uint8]
        cls.lib.ai_test_backrow_gain.restype = C.c_int16
        cls.lib.random_seed.argtypes = [C.c_uint16]
        cls.lib.random_next.restype = C.c_uint16
        cls.lib.ai_move.argtypes = [C.c_uint8, C.POINTER(C.c_uint8), C.POINTER(C.c_uint8), C.POINTER(C.c_uint8)]
        baseline = Path(cls.tmp.name)/'baseline.so'
        subprocess.run(['gcc', '-shared', '-fPIC', '-O2', '-std=c99', '-Wno-unknown-pragmas',
                        '-Isrc/core', '-DAI_TEST', *['-D'+f for f in FLAGS],
                        '-o', str(baseline), *['src/core/'+s+'.c' for s in SOURCES]], cwd=ROOT, check=True)
        cls.baseline = C.CDLL(str(baseline))
        cls.baseline.random_seed.argtypes = [C.c_uint16]
        cls.baseline.random_next.restype = C.c_uint16
        cls.baseline.ai_move.argtypes = cls.lib.ai_move.argtypes

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def fixture(self, army, seed):
        rng = random.Random(seed)
        cells = [254 if sq in LAKES else 255 for sq in range(100)]
        ranks = [r for r, count in enumerate(COUNTS) for _ in range(count)]
        for sq, rank in zip(setup_squares(army), ranks):
            cells[sq] = army*16 | rank
        enemy = ranks[:]
        rng.shuffle(enemy)
        lost = [0]*12
        for sq, rank in zip(setup_squares(1-army), enemy):
            if rank != 11 and rng.random() < .25:
                lost[rank] += 1
                continue
            revealed = rng.random() < .35
            moved = rank < 10 and rng.random() < .4
            cells[sq] = (1-army)*16 | (rank if revealed else rng.randrange(12)) | int(revealed)*32 | int(moved)*64
        return cells, lost

    def hidden(self, cells, army, lost):
        seen = [0]*12
        for cell in cells:
            if cell < 254 and bool(cell&16) != bool(army) and cell&32:
                seen[cell&15] += 1
        return [n-l-s for n, l, s in zip(COUNTS, lost, seen)]

    def test_values_stay_within_three_gain_points_of_exact_rational_prior(self):
        checked = 0
        for army in (0, 1):
            for seed in range(24):
                cells, lost = self.fixture(army, 3199000+seed)
                self.board[:] = cells
                self.rules.value = 0
                self.level.value = 1
                self.lib.ai_reset()
                losses = (C.c_uint8*12)(*lost)
                hidden = self.hidden(cells, army, lost)
                unknown = [sq for sq, cell in enumerate(cells) if cell < 254 and bool(cell&16) != bool(army) and not cell&32]
                unmoved = [sq for sq in unknown if not cells[sq]&64]
                row = [sq for sq in unmoved if sq//10 == (9 if army else 0)]
                for rank in range(10):
                    for square in unknown:
                        got = self.lib.ai_test_backrow_value(army*16, losses, rank, square)
                        gains = [self.lib.ai_test_backrow_gain(rank, r) for r in range(12)]
                        mobile = Fraction(sum(n*g for n, g in zip(hidden[:10], gains[:10])), sum(hidden[:10])) if sum(hidden[:10]) else Fraction(0)
                        flag = Fraction(0)
                        bomb = Fraction(0)
                        if not cells[square]&64:
                            if hidden[11]:
                                flag = Fraction(397 if square in row else 1, len(unmoved)+396*len(row))
                                bomb = hidden[10]*(1-flag)/(len(unmoved)-1) if len(unmoved) > 1 else Fraction(0)
                            else:
                                bomb = Fraction(hidden[10], len(unmoved))
                        exact = 2000*flag+gains[10]*bomb+mobile*(1-flag-bomb)
                        self.assertLessEqual(abs(got-int(exact)), 3, (army, seed, rank, square, got, exact))
                        self.assertGreaterEqual(got, -400)
                        self.assertLessEqual(got, 2000)
                        checked += 1
        self.assertGreater(checked, 5000)

    def test_private_nibbles_never_change_choices_or_rng_both_sides(self):
        for army in (0, 1):
            cells, lost = self.fixture(army, 3199171)
            baseline = None
            for nibble in range(12):
                self.board[:] = [(cell&240)|nibble if cell < 254 and bool(cell&16) != bool(army) and not cell&32 else cell for cell in cells]
                self.rules.value = 0
                self.level.value = 1
                self.lib.ai_reset()
                self.lib.random_seed(1990)
                source = C.c_uint8(255)
                target = C.c_uint8(255)
                self.lib.ai_move(army*16, (C.c_uint8*12)(*lost), C.byref(source), C.byref(target))
                result = (source.value, target.value, self.lib.random_next())
                if baseline is None:
                    baseline = result
                self.assertEqual(result, baseline)

    def test_other_difficulties_and_rule_fallback_match_unchanged_native(self):
        for army in (0, 1):
            cells, lost = self.fixture(army, 3199261)
            for level, rules in ((0, 0), (2, 0), (1, 1), (1, 63)):
                results = []
                for lib in (self.lib, self.baseline):
                    (C.c_uint8*100).in_dll(lib, 'board')[:] = cells
                    C.c_uint8.in_dll(lib, 'game_rules').value = rules
                    C.c_uint8.in_dll(lib, 'ai_difficulty').value = level
                    lib.ai_reset()
                    lib.random_seed(1990)
                    source = C.c_uint8(255)
                    target = C.c_uint8(255)
                    lib.ai_move(army*16, (C.c_uint8*12)(*lost), C.byref(source), C.byref(target))
                    results.append((source.value, target.value, lib.random_next()))
                self.assertEqual(*results)


if __name__ == '__main__':
    unittest.main()
