"""Real root-score bridge wiring, public event history and honest mode isolation."""
import unittest
from unittest.mock import patch

from ai_registry import ROOT,build_policy
from campaign_belief_values import adjustments
from teacher_bot import TeacherBot
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

MODEL=ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json'

class CaptureBridgeAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program,_=build_policy('teacher-context-v1-normal');cls.bundle=program.parent
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:
            cls.game=saved.game(9)
        states,_=replay(cls.game);cls.events=public_events(cls.game,states)

    def bot(self,mode):
        return TeacherBot(self.bundle/'observer',self.bundle/'teacher',samples=8,depth=4,
            blend='correction',strategic=True,context=True,joint_belief_model=MODEL,root_capture_mode=mode)

    def initialize(self,bot,army):
        bot.rng.seed(917)
        for line in ['new '+('red','blue')[army],'seed 917','rules 0','difficulty normal',
                     'setup '+self.game[('red_setup','blue_setup')[army]],*self.events[:80]]:
            bot.joint_model.observe(line.split());bot.observer.send(line)

    def test_real_bridge_changes_only_reported_capture_values_and_keeps_worlds(self):
        import campaign_belief_values
        for army in (0,1):
            baseline=self.bot(None)
            try:
                self.initialize(baseline,army);baseline.choose();original=baseline.last_report
                for mode in ('counts','joint'):
                    bot=self.bot(mode)
                    try:
                        self.initialize(bot,army)
                        with patch.object(campaign_belief_values,'adjustments',wraps=adjustments) as hook:
                            bot.choose()
                        self.assertEqual(hook.call_count,1)
                        self.assertEqual(hook.call_args.args[-1],mode)
                        report=bot.last_report
                        deltas={tuple(r['move']):r['adjustment'] for r in report['root_capture_beliefs']['values']}
                        for before,after in zip(original['values'],report['values']):
                            self.assertEqual(before['move'],after['move'])
                            self.assertEqual(before['sample_mean'],after['sample_mean'])
                            self.assertEqual(before['correction'],after['correction'])
                            self.assertAlmostEqual(after['value']-before['value'],deltas.get(tuple(before['move']),0))
                        self.assertFalse(report['root_capture_beliefs']['behavioral_reweighting'])
                    finally:bot.close()
            finally:baseline.close()

    def test_bridge_rejects_missing_model_or_privileged_combination_before_starting(self):
        for options in (dict(root_capture_mode='counts'),
                        dict(root_capture_mode='joint',joint_belief_model=MODEL,diagnostic_truth=True),
                        dict(root_capture_mode='joint',joint_belief_model=MODEL,correction_anchor='parent')):
            with self.assertRaisesRegex(ValueError,'isolate'):
                TeacherBot('unused','unused',blend='correction',**options)
        with self.assertRaisesRegex(ValueError,'unknown root capture'):
            TeacherBot('unused','unused',root_capture_mode='other')

if __name__=='__main__':unittest.main()
