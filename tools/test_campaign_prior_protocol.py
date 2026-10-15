"""Exercise Q12 priors through the real native observer protocol."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from ai_registry import ROOT, get_policy
from feldmarschall import COUNTS, LAKES


class PriorProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='feld-prior-protocol-')
        cls.folder = Path(cls.temp.name)
        cls.policy = get_policy('teacher-context-v1-normal')
        cls.programs = {}
        for mode, defines in (('base', []), ('belief', ['AI_BELIEF_PRIORS'])):
            program = cls.folder / mode
            subprocess.run(cls.recipe(program, defines), cwd=ROOT, check=True, capture_output=True)
            cls.programs[mode] = program

    @classmethod
    def recipe(cls, program, extra=()):
        return ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Wno-format-overflow',
                '-Isrc/core', '-o', str(program),
                *['-D'+d for d in cls.policy['defines']+list(extra)], *cls.policy['sources']]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_protocol(self, commands, mode='belief'):
        result = subprocess.run([str(self.programs[mode])], input='\n'.join(commands+['quit'])+'\n',
                                text=True, capture_output=True, check=True, timeout=15)
        return result.stdout.splitlines()

    def fixture(self, blue=False):
        cells = [254 if square in LAKES else 255 for square in range(100)]
        for square, cell in {84:0, 74:10, 99:11, 30:16|12, 39:16|12, 20:16|32|8}.items():
            cells[square] = cell
        lost = COUNTS[:]
        for rank in (8, 10, 11): lost[rank] -= 1
        flag, bomb = [0]*100, [0]*100
        flag[39], bomb[30] = 4096, 4096
        if blue:
            cells = [(cell ^ 16) if cell < 254 else cell for cell in reversed(cells)]
            flag.reverse(); bomb.reverse()
        position = f'position {int(blue)} {bytes(lost).hex()} {bytes(cells).hex()} ffffffff0000'
        return position, flag, bomb

    @staticmethod
    def packet(flag, bomb):
        return ''.join(f'{value:04x}' for value in flag+bomb)

    def test_valid_packet_routes_quiet_move_for_both_armies_without_disclosure(self):
        for blue in (False, True):
            position, flag, bomb = self.fixture(blue)
            baseline = self.run_protocol([position, 'seed 1', 'ranked', 'public'])
            posterior = self.run_protocol([position, 'belief-priors '+self.packet(flag, bomb).upper(),
                                           'seed 1', 'ranked', 'public', 'strategy'])
            self.assertIn('belief-priorsok', posterior)
            self.assertNotEqual([r for r in baseline if r.startswith('move ')],
                                [r for r in posterior if r.startswith('move ')])
            self.assertEqual([r for r in baseline if r.startswith('public ')],
                             [r for r in posterior if r.startswith('public ')])
            state = bytes.fromhex(next(r.split()[1] for r in posterior if r.startswith('strategy ')))
            self.assertEqual(state[-401], 17 if blue else 1)
            goal_source = 114 if blue else 85
            self.assertEqual(state[goal_source], 60 if blue else 39)

    def test_invalid_packets_leave_entire_prior_and_memory_state_unchanged(self):
        position, flag, bomb = self.fixture()
        packet = self.packet(flag, bomb)
        overflow = '1001'+packet[4:]
        bad_sum = list(flag); bad_sum[30] = 1
        invalid = ['', packet[:-1], packet+'0', 'g'+packet[1:], overflow,
                   self.packet(bad_sum, bomb), packet+' extra', '0'*1200]
        for bad in invalid:
            commands = [position, 'belief-priors '+packet, 'seed 1', 'ranked', 'strategy',
                        'belief-priors '+bad, 'strategy', 'isready']
            rows = self.run_protocol(commands)
            self.assertIn('error belief-priors', rows)
            states = [row for row in rows if row.startswith('strategy ')]
            self.assertEqual(len(states), 2)
            self.assertEqual(states[0], states[1])
            self.assertEqual(rows[-1], 'readyok')

    def test_new_game_and_position_reset_clear_every_prior_byte(self):
        position, flag, bomb = self.fixture()
        for reset in ('new red', 'new blue', position):
            rows = self.run_protocol([position, 'belief-priors '+self.packet(flag,bomb),
                                      'strategy', reset, 'strategy'])
            states = [bytes.fromhex(row.split()[1]) for row in rows if row.startswith('strategy ')]
            self.assertEqual(states[0][-401], 1)
            self.assertEqual(states[1][-401:], bytes(401))

    def test_macro_off_rejects_command_and_preserves_strategy(self):
        position, flag, bomb = self.fixture()
        # A short malformed command avoids exercising legacy 512-byte line splitting.
        rows = self.run_protocol([position, 'strategy', 'belief-priors 0000', 'strategy'], 'base')
        self.assertTrue(any(row.startswith('error') for row in rows))
        self.assertEqual(*[row for row in rows if row.startswith('strategy ')])

    def test_default_engine_binary_is_identical_to_frozen_student(self):
        # Current context observers gained a separate guarded diagnostic command.
        # Compare the default production recipe against its immutable source.
        policy = get_policy('student-guard-v1-normal')
        binaries = []
        for mode, overlay in (('original', False), ('current', True)):
            folder = self.folder/mode; folder.mkdir()
            with zipfile.ZipFile(ROOT/policy['archive']) as archive:
                archive.extractall(folder)
            if overlay:
                for name in ('src/native/engine.c', 'src/core/ai.c', 'src/core/ai.h'):
                    (folder/name).write_bytes((ROOT/name).read_bytes())
            program = folder/'engine'
            command = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Wno-format-overflow',
                       '-Isrc/core', '-o', str(program),
                       *['-D'+d for d in policy['defines']], *policy['sources']]
            subprocess.run(command, cwd=folder, check=True, capture_output=True)
            binaries.append(program.read_bytes())
        self.assertEqual(*binaries)


if __name__ == '__main__':
    unittest.main()
