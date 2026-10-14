"""Shared root legality, private-rank masking, RNG separation and parser checks."""
import copy
import json
from pathlib import Path
import random
import subprocess
import unittest

from feldmarschall import ROOT, COUNTS, GLYPHS, LAKES, Position, random_setup
from teacher_bot import TeacherBot


def search(cells, army=0, depth=4, audit=False, strategic=False):
    command = [str(ROOT / 'build/feldmarschall-teacher-rollout')]
    if audit: command.append('--audit')
    if strategic: command.append('--strategic')
    result = subprocess.run(command, input=f'search {army} {depth} {bytes(cells).hex()} ffffffff0000\n',
                            text=True, capture_output=True, check=True)
    actions, decisions = {}, []
    for line in result.stdout.splitlines():
        words = line.split()
        if words[0] == 'action': actions[tuple(map(int, words[1:3]))] = tuple(map(int, words[3:]))
        elif words[0] == 'decision': decisions.append(words)
        else: assert words[0] == 'done', words
    return actions, decisions


class RolloutTests(unittest.TestCase):
    def test_root_actions_and_reproducibility(self):
        rng = random.Random(90261014)
        for army in (0, 1):
            position = Position()
            for side in (0, 1): position.place(side, random_setup(rng))
            cells = [254 if sq in LAKES else 255 if cell is None else cell[1] | (16 if cell[0] else 0)
                     for sq, cell in enumerate(position.cells)]
            actions, _ = search(cells, army)
            self.assertEqual(set(actions), set(position.moves(army)))
            self.assertEqual((actions, []), search(cells, army))

    def test_identical_information_cannot_change_policy_decisions(self):
        rng = random.Random(91261014)
        position = Position()
        for side in (0, 1): position.place(side, random_setup(rng))
        cells = [254 if sq in LAKES else 255 if cell is None else cell[1] | (16 if cell[0] else 0)
                 for sq, cell in enumerate(position.cells)]
        changed = cells[:]
        enemy = [sq for sq, cell in enumerate(cells) if cell < 254 and cell & 16]
        flag = next(sq for sq in enemy if (cells[sq] & 15) == 11)
        bomb = next(sq for sq in enemy if (cells[sq] & 15) == 10 and sq // 10 == flag // 10)
        changed[flag], changed[bomb] = changed[bomb], changed[flag]
        _, first = search(cells, audit=True)
        _, second = search(changed, audit=True)
        decisions = {}
        matches = future_matches = 0
        for row in [*first, *second]:
            # Same initial permitted view and public action/observation history
            # must yield the same RNG, current view, private OWN policy state
            # and action, despite different unobservable world assignments.
            key = tuple(row[i] for i in (1, 2, 4, 5, 7))
            action = tuple(row[i] for i in (3, 6, 8, 9, 10))
            if key in decisions:
                self.assertEqual(decisions[key], action); matches += 1
                future_matches += row[5] != '-'
            decisions[key] = action
            army = int(row[1]); view = bytes.fromhex(row[6])
            self.assertTrue(all((cell & 15) == 12 for cell in view
                               if cell < 254 and bool(cell & 16) != bool(army) and not cell & 32))
        self.assertGreater(matches, 10)
        self.assertGreater(future_matches, 0)

    def test_quiet_progress_shaping_is_not_material(self):
        cells = [255] * 100
        for sq in LAKES: cells[sq] = 254
        for sq, cell in {60: 0, 99: 11, 0: 11 | 16 | 32, 9: 10 | 16 | 32}.items(): cells[sq] = cell
        plain, _ = search(cells, depth=1)
        strategic, _ = search(cells, depth=1, strategic=True)
        self.assertEqual(plain[(60, 50)][0], 0)
        self.assertGreater(strategic[(60, 50)][0], strategic[(60, 70)][0])

    def test_teacher_adapter_receives_only_permitted_board(self):
        rng = random.Random(92261014)
        bot = TeacherBot(ROOT / 'build/feldmarschall-teacher-observer', ROOT / 'build/feldmarschall-teacher-rollout',
                         samples=2, depth=3, blend='correction', strategic=True)
        try:
            bot.observer.send('new red')
            setup = random_setup(rng); bot.observer.send('setup ' + setup)
            position = Position(); position.place(0, setup); position.place(1, '?' * 40, known=False)
            self.assertIn(bot.choose(), position.moves(0))
            self.assertGreater(bot.last_report['nodes'], 0)
        finally: bot.close()


if __name__ == '__main__': unittest.main()
