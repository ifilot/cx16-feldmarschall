"""Fair information-hook integration, default parity and victory protection."""
import types
import unittest

from ai_registry import ROOT, build_policy
from feldmarschall import COUNTS, LAKES
from teacher_bot import TeacherBot


class InformationAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        executable, _ = build_policy('teacher-context-v1-normal')
        cls.observer, cls.teacher = executable.parent/'observer', executable.parent/'teacher'

    def bot(self, strategy=None):
        return TeacherBot(self.observer, self.teacher, samples=2, depth=4,
                          blend='correction', strategic=True, context=True,
                          information_strategy=strategy)

    def root(self, bot):
        cells = [254 if sq in LAKES else 255 for sq in range(100)]
        cells[60], cells[99], cells[50] = 8, 11, 16 | 32 | 11
        lost = COUNTS[:]; lost[11] -= 1
        bot.observer.ask('position 0 '+bytes(lost).hex()+' '+bytes(cells).hex()+' ffffffff0000', 'positionok')

    def test_empty_hook_preserves_all_scores_and_decision(self):
        reports = []
        for hooked in (False, True):
            bot = self.bot()
            try:
                self.root(bot)
                if hooked: bot.information_module = types.SimpleNamespace(adjustments=lambda *args: {})
                bot.choose(); reports.append(bot.last_report)
            finally: bot.close()
        self.assertEqual(*reports)

    def test_winning_flag_capture_survives_arbitrary_negative_hook(self):
        bot = self.bot()
        try:
            self.root(bot)
            bot.information_module = types.SimpleNamespace(
                adjustments=lambda cells,army,lost,histories,moves: {(60,50): -1000000})
            self.assertEqual(bot.choose(), (60,50))
        finally: bot.close()

    def test_privileged_and_fair_modes_cannot_be_combined(self):
        with self.assertRaisesRegex(ValueError, 'cannot use diagnostic truth'):
            TeacherBot(self.observer,self.teacher,diagnostic_truth=True,information_strategy='lifetime')

    def test_callbacks_are_limited_to_legal_finite_adjustments(self):
        for bad in ({(0,99): 1}, {(60,50): float('nan')}):
            bot = self.bot()
            try:
                self.root(bot)
                bot.information_module = types.SimpleNamespace(adjustments=lambda *args: bad)
                with self.assertRaisesRegex(ValueError, 'invalid information-strategy'): bot.choose()
            finally: bot.close()

    def test_hook_does_not_change_legal_actions_or_public_input(self):
        for strategy in ('lifetime', 'objectives', 'followthrough'):
            bot = self.bot(strategy)
            try:
                self.root(bot)
                before = bot.observer.ask('public','public')
                self.assertEqual(bot.choose(), (60,50))
                self.assertEqual(bot.observer.ask('public','public'), before)
                self.assertEqual(bot.last_report['information_strategy'],strategy)
            finally: bot.close()


if __name__ == '__main__': unittest.main()
