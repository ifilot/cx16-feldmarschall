"""Check the privileged-information ablation and isolation of ordinary policies."""
import json
from pathlib import Path
import random
import tempfile
import unittest

from ai_registry import ROOT, build_policy, catalog, get_policy, receives_opponent_setup
from feldmarschall import Engine, GLYPHS, LAKES, Position, square_name
from teacher_bot import TeacherBot
from tournament import run
from tournament_store import Tournament, verify

DIAGNOSTIC = 'teacher-context-truth-diagnostic-v1-normal'
FLAG_SPY = 'teacher-context-flag-spy-diagnostic-v1-normal'
FLAG_ONLY = 'teacher-context-flag-diagnostic-v1-normal'
CONTROL = 'teacher-context-v1-normal'
DOS = 'msdos-1990-v2-normal'


class TruthTeacher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program, _ = build_policy(DIAGNOSTIC)
        cls.control, _ = build_policy(CONTROL)
        with Tournament(ROOT / 'docs/ai-vs-msdos-2026-10-15/teacher-context-v1-normal.fmtour') as tournament:
            # A complete observed history exercises captures, movement and loss accounting.
            cls.game = tournament.game(9)

    def bot(self, diagnostic=True, knowledge='all'):
        program = self.program if diagnostic else self.control
        return TeacherBot(program.parent/'observer', program.parent/'teacher', samples=2,
                          depth=4, blend='correction', strategic=True, context=True,
                          diagnostic_truth=diagnostic, diagnostic_knowledge=knowledge)

    def send(self, bot, text):
        words = text.split()
        bot.diagnostic_event(words)
        if words[0] != 'opponent-setup': bot.observer.send(text)

    def initialize(self, bot, side, game=None):
        game = game or self.game
        self.send(bot, 'new ' + ('red', 'blue')[side])
        self.send(bot, 'setup ' + game[('red_setup', 'blue_setup')[side]])
        if bot.diagnostic_truth:
            self.send(bot, 'opponent-setup ' + game[('blue_setup', 'red_setup')[side]])

    def test_only_explicit_diagnostic_and_dos_receive_enemy_setup(self):
        granted = {p['id'] for p in catalog() if receives_opponent_setup(p)}
        self.assertEqual(granted, {DIAGNOSTIC, FLAG_SPY, FLAG_ONLY, 'msdos-1990-v1-normal', DOS})
        bot = self.bot(False)
        try:
            with self.assertRaisesRegex(ValueError, 'rejects opponent setup'):
                bot.diagnostic_event(['opponent-setup', self.game['blue_setup']])
            self.initialize(bot, 0)
            with self.assertRaisesRegex(RuntimeError, 'unknown command'):
                bot.observer.ask('diagnostic-truth ' + 'ff'*100, 'diagnostic-truthok')
            _, cells, _, _ = bot.observer.ask('public', 'public').split()
            self.assertTrue(all(c & 15 == 12 for c in bytes.fromhex(cells) if c < 254 and c & 16))
        finally: bot.close()

    def test_truth_history_both_sides_and_reset(self):
        for side in (0, 1):
            bot = self.bot()
            try:
                self.initialize(bot, side)
                physical = Position()
                for army, key in enumerate(('red_setup', 'blue_setup')): physical.place(army, self.game[key])
                for ply, (src, dst) in enumerate(self.game['moves'][:120]):
                    if ply in (0, 35, 75):
                        self.assertIn(bot.choose(), physical.moves(side))
                        cells = bytes.fromhex(bot.last_report['board_hex'])
                        for sq, cell in enumerate(physical.cells):
                            if cell:
                                self.assertEqual(cells[sq] & 15, cell[1])
                                if cell[0] != side: self.assertTrue(cells[sq] & 32)
                                else: self.assertEqual(bool(cells[sq] & 32), cell[3])
                            else: self.assertEqual(cells[sq], 254 if sq in LAKES else 255)
                    names = square_name(src) + ' ' + square_name(dst)
                    if physical.cells[dst] is None:
                        text = 'moved ' + names
                        physical.move(src, dst)
                    else:
                        a, d = physical.cells[src][1], physical.cells[dst][1]
                        text = 'battle ' + names + ' ' + GLYPHS[a] + ' ' + GLYPHS[d]
                        physical.fight(src, dst, a, d)
                    self.send(bot, text)
                    self.assertEqual(bot.truth.cells, physical.cells)
                self.assertEqual(bot.truth_plies, 120)
                self.initialize(bot, 1-side)
                self.assertEqual(bot.truth_plies, 0)
                self.assertIn(bot.choose(), bot.truth.moves(1-side))
                with self.assertRaisesRegex(ValueError, 'late diagnostic setup'):
                    bot.diagnostic_event(['opponent-setup', self.game['blue_setup']])
            finally: bot.close()

    def test_missing_and_inconsistent_truth_fail_explicitly(self):
        bot = self.bot()
        try:
            self.send(bot, 'new red')
            self.send(bot, 'setup ' + self.game['red_setup'])
            with self.assertRaisesRegex(ValueError, 'needs both armies'): bot.choose()
            self.send(bot, 'opponent-setup ' + self.game['blue_setup'])
            with self.assertRaisesRegex(RuntimeError, 'truth mismatch'):
                bot.observer.ask('diagnostic-truth ' + 'ff'*100, 'diagnostic-truthok')
        finally: bot.close()

    def test_flag_spy_only_keeps_other_ranks_masked(self):
        for side in (0, 1):
            bot = self.bot(knowledge='flag-spy')
            try:
                self.initialize(bot, side)
                bot.choose()
                cells = bytes.fromhex(bot.last_report['board_hex'])
                known = []
                for sq, cell in enumerate(bot.truth.cells):
                    if cell is None or cell[0] == side: continue
                    if cell[1] in (9, 11):
                        self.assertEqual(cells[sq] & 15, cell[1]); self.assertTrue(cells[sq] & 32)
                        known.append(cell[1])
                    else:
                        self.assertEqual(cells[sq] & 15, 12); self.assertFalse(cells[sq] & 32)
                self.assertEqual(sorted(known), [9, 11])
            finally: bot.close()

    def test_flag_spy_choices_ignore_other_private_rank_assignments(self):
        changed = dict(self.game)
        setup = list(changed['blue_setup'])
        first, second = setup.index('1'), setup.index('4')
        setup[first], setup[second] = setup[second], setup[first]
        changed['blue_setup'] = ''.join(setup)
        reports = []
        for game in (self.game, changed):
            bot = self.bot(knowledge='flag-spy')
            try:
                self.initialize(bot, 0, game)
                bot.choose()
                reports.append(bot.last_report)
            finally: bot.close()
        self.assertEqual(reports[0], reports[1])

    def test_rollout_masks_our_unrevealed_ranks_from_opponent(self):
        import subprocess
        bot = self.bot()
        try:
            self.initialize(bot, 0)
            bot.choose()
            army, board, _, shuttle = bot.observer.ask('public', 'public').split()
            state = bot.observer.ask('strategy', 'strategy')
            result = subprocess.run([str(self.program.parent/'teacher'), '--strategic', '--context', '--audit'],
                input=f'search {army} 4 {board} {shuttle} {state}\n', text=True, capture_output=True, check=True)
            counts = [0, 0]
            for line in result.stdout.splitlines():
                if not line.startswith('decision '): continue
                row = line.split(); mover = int(row[1]); counts[mover] += 1
                cells = bytes.fromhex(row[6])
                if mover == 0:
                    self.assertTrue(all(c & 15 < 12 for c in cells if c < 254))
                else:
                    self.assertTrue(all(c & 15 == 12 for c in cells if c < 254 and not c & 16 and not c & 32))
            self.assertTrue(all(counts))
        finally: bot.close()

    def test_python_native_and_pool_reuse_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary)/f'{name}.fmtour' for name in ('python', 'native', 'pooled')]
            for path, backend, reuse in zip(paths, ('python', 'openmp', 'openmp'), (None, False, True)):
                run(DIAGNOSTIC, DOS, path, seed=1940099, rounds=2, families=['uniform'],
                    max_plies=24, jobs=1, backend=backend, reuse_processes=reuse)
                self.assertEqual(verify(path)['errors'], 0)
            with Tournament(paths[0]) as reference:
                for path in paths[1:]:
                    with Tournament(path) as other:
                        for row in reference.games(): self.assertEqual(reference.game(row['id']), other.game(row['id']))


if __name__ == '__main__': unittest.main()
