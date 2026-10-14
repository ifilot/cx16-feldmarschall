"""Check diversity constraints and selection independence from side/opponent."""
import unittest
import ctypes
import subprocess
from collections import Counter

from benchmark_ai_selection import choose_weights, layouts, selected_cases
from optimize_ai_deployments import trials
from feldmarschall import ROOT, GLYPHS, setup_squares


def next_random(state):
    state ^= (state << 7) & 65535
    state ^= state >> 9
    state ^= (state << 8) & 65535
    return state


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        target = ROOT / 'build/ai-selection-runtime.so'
        target.parent.mkdir(exist_ok=True)
        subprocess.run(['gcc', '-shared', '-fPIC', '-O2', '-Wno-unknown-pragmas', '-Isrc/core',
                        '-o', str(target), *['src/core/' + name + '.c' for name in
                            ('pieces', 'board', 'rules', 'random', 'ai_level', 'setup', 'ai_deploy')]],
                       cwd=ROOT, check=True)
        cls.lib = ctypes.CDLL(str(target))
        cls.cells = (ctypes.c_uint8 * 100).in_dll(cls.lib, 'board')
        cls.level = ctypes.c_uint8.in_dll(cls.lib, 'ai_difficulty')
        cls.rules = ctypes.c_uint8.in_dll(cls.lib, 'game_rules')
        cls.lib.random_next.restype = ctypes.c_uint16

    def test_constrained_optimum(self):
        weights = choose_weights([1, .8, .6, .1])
        self.assertEqual(weights, (5, 4, 1, 0))
        self.assertEqual(sum(weights), 10)
        self.assertEqual(max(weights), 5)

    def test_block_selection(self):
        retained = layouts()
        policy = {'layouts': retained, 'weights': dict(zip(retained, (5, 3, 2, 0)))}
        cases = trials(61261014, 20, ['v020', 'planned', 'adaptive', 'easy', 'greedy'])
        actual, blocks = selected_cases(cases, policy, 1234)
        self.assertEqual((actual, blocks), selected_cases(cases, policy, 1234))
        self.assertEqual(len(blocks), 140)
        self.assertEqual(len(set(actual.values())), 3)
        for start in range(0, len(cases), 5):
            self.assertEqual(len({actual[i] for i in range(start, start + 5)}), 1)
        # Public opponent layout and opponent name cannot influence the draw.
        altered = [{**case, 'opponent': 'different', 'opponent_setup': 'ignored'} for case in cases]
        self.assertEqual((actual, blocks), selected_cases(altered, policy, 1234))

    def test_runtime_all_seeds_and_both_orientations(self):
        retained = layouts()
        names = ['fortress', 'setup-d83d63408255', 'setup-815ddb0df689']
        self.rules.value = 0
        for level in (1, 2):
            self.level.value = level
            for blue in (0, 1):
                counts = Counter()
                self.lib.board_clear()
                other_squares = setup_squares(1 - blue)
                for sq in other_squares:
                    self.cells[sq] = 11 | (16 if not blue else 0)
                for seed in range(1, 65536):
                    draw = next_random(seed)
                    while draw > 65530:
                        draw = next_random(draw)
                    ticket = (draw - 1) % 10
                    index = 0 if ticket < (4 if level == 2 else 5) else 1 if ticket < 9 else 2
                    self.lib.random_seed(seed)
                    self.lib.setup_ai(blue)
                    actual = ''.join(GLYPHS[self.cells[sq] & 15] for sq in setup_squares(blue))
                    self.assertEqual(actual, retained[names[index]])
                    self.assertTrue(all(self.cells[sq] == (11 | (16 if not blue else 0)) for sq in other_squares))
                    self.assertEqual(self.lib.random_next(), next_random(draw))
                    counts[index] += 1
                weights = (4, 5, 1) if level == 2 else (5, 4, 1)
                for index, weight in enumerate(weights):
                    self.assertLessEqual(abs(counts[index] - weight * 6553), 5)

    def test_random_fallback_preserves_board_and_rng(self):
        for level, rules in [(0, 0), (3, 0), *[(level, rules) for level in (1, 2) for rules in range(1, 64)]]:
            self.level.value, self.rules.value = level, rules
            for blue in (0, 1):
                self.lib.board_clear(); self.lib.random_seed(42)
                self.lib.setup_random(blue)
                expected, random_state = bytes(self.cells), self.lib.random_next()
                self.lib.board_clear(); self.lib.random_seed(42)
                self.lib.setup_ai(blue)
                self.assertEqual(bytes(self.cells), expected)
                self.assertEqual(self.lib.random_next(), random_state)


if __name__ == '__main__':
    unittest.main()
