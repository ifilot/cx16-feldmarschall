"""Native masked-policy exchange extension, quiet stopping and bounded cost."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from ai_registry import ROOT, get_policy
from feldmarschall import LAKES


def world(pieces):
    cells = [254 if square in LAKES else 255 for square in range(100)]
    for square, piece in pieces.items():
        cells[square] = piece
    return bytes(cells).hex()


class PolicyQuiescence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='feld-quiescence-')
        cls.executables = {}
        policy = get_policy('teacher-context-v1-normal')
        for name, extra in (('base', []), ('extended', ['AI_ROLLOUT_QUIESCENCE'])):
            executable = Path(cls.directory.name) / name
            command = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Isrc/core', '-o', str(executable)]
            command += ['-D' + define for define in policy['teacher_defines'] + extra]
            command += policy['teacher_sources']
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
            cls.executables[name] = executable

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def run_search(self, mode, pieces, depth=1):
        result = subprocess.run([str(self.executables[mode]), '--audit'],
                                input=f'search 0 {depth} {world(pieces)} ffffffff0000\n',
                                capture_output=True, text=True, check=True, timeout=15)
        actions = {}
        decisions = []
        for line in result.stdout.splitlines():
            words = line.split()
            self.assertNotEqual(words[0], 'error', line)
            if words[0] == 'action':
                actions[tuple(map(int, words[1:3]))] = tuple(map(int, words[3:5]))
            elif words[0] == 'decision':
                decisions.append(words)
            elif words[0] == 'done':
                nodes, reference = map(int, words[1:3])
        return dict(actions=actions, decisions=decisions, nodes=nodes, reference=reference)

    def test_transient_capture_is_evaluated_after_masked_recapture(self):
        pieces = {99: 11, 0: 16|11, 64: 5, 54: 16|8, 44: 16|3, 80: 6, 90: 4}
        base = self.run_search('base', pieces)
        extended = self.run_search('extended', pieces)
        self.assertEqual(base['actions'][(64, 54)], (10, 10))
        self.assertEqual(extended['actions'][(64, 54)], (-20, 10))
        recapture = [words for words in extended['decisions']
                     if words[1:3] == ['1', '1'] and words[5].startswith('4036')]
        self.assertTrue(recapture)
        self.assertEqual(recapture[0][-2:], ['44', '54'])
        self.assertLessEqual(extended['nodes'], 5*len(extended['actions'])+4)

    def test_quiet_leaf_does_not_apply_extra_quiet_move(self):
        pieces = {99: 11, 0: 16|11, 80: 6, 20: 16|4}
        base = self.run_search('base', pieces)
        extended = self.run_search('extended', pieces)
        self.assertEqual(base['actions'], extended['actions'])
        self.assertEqual(base['reference'], extended['reference'])
        self.assertEqual(extended['nodes'], 2*len(extended['actions'])+1)
        # Every leaf probe sees only the original proposed move in its path.
        self.assertTrue(all(len(bytes.fromhex(words[5])) == 5
                            for words in extended['decisions'] if words[1:3] == ['1', '1']))

    def test_leaf_opponent_policy_is_invariant_to_hidden_enemy_rank_swap(self):
        first = {99: 11, 0: 16|11, 64: 5, 54: 16|8, 44: 16|3, 80: 6, 90: 4}
        second = dict(first)
        second[80], second[90] = second[90], second[80]
        def leaf(pieces):
            result = self.run_search('extended', pieces)
            return next(words for words in result['decisions']
                        if words[1:3] == ['1', '1'] and words[5].startswith('4036'))
        # Includes initial view, public trajectory, masked decision board,
        # casualties, shuttle state, permitted memory, RNG and chosen action.
        self.assertEqual(leaf(first), leaf(second))

    def test_deep_request_respects_fixed_public_trajectory_capacity(self):
        pieces = {99: 11, 0: 16|11, 64: 5, 54: 16|8, 44: 16|3, 80: 6, 90: 4}
        result = self.run_search('extended', pieces, depth=12)
        self.assertTrue(result['actions'])
        self.assertTrue(all(words[5] == '-' or len(bytes.fromhex(words[5])) <= 65
                            for words in result['decisions']))


if __name__ == '__main__':
    unittest.main()
