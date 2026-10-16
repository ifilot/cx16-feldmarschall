"""Regression cases for prospective control reuse and physical error totals."""
import unittest
from audit_honest_campaign import summarize_executions

class SharedControlAccountingTests(unittest.TestCase):
    def test_destination_can_finish_before_the_source_study(self):
        result = summarize_executions(
            [dict(attempts=2000, errors=8)],
            {'control': (1000, 5), 'net': (1000, 3)},
            [dict(source='fork/control', destination='net/control', attempts=1000)],
            {'net/control', 'net/treatment'})
        self.assertEqual(result['unique_saved_attempts'], 2000)
        self.assertEqual(result['reused_comparison_attempts'], 0)
        self.assertEqual(result['declared_reused_control_attempts'], 1000)
        self.assertEqual(result['unique_saved_unscored_errors'], 8)

    def test_both_completed_studies_count_control_games_and_errors_once(self):
        result = summarize_executions(
            [dict(attempts=2000, errors=9), dict(attempts=2000, errors=8)],
            {'control': (1000, 5), 'fork': (1000, 4), 'net': (1000, 3)},
            [dict(source='fork/control', destination='net/control', attempts=1000)],
            {'fork/control', 'fork/treatment', 'net/control', 'net/treatment'})
        self.assertEqual(result['completed_attempts'], 4000)
        self.assertEqual(result['unique_saved_attempts'], 3000)
        self.assertEqual(result['reused_comparison_attempts'], 1000)
        self.assertEqual(result['errors_preserved_unscored'], 17)
        self.assertEqual(result['unique_saved_unscored_errors'], 12)

    def test_duplicate_execution_without_a_declared_source_is_rejected(self):
        with self.assertRaises(AssertionError):
            summarize_executions([dict(attempts=2000, errors=10)],
                                 {'control': (1000, 5)}, [], {'control'})

if __name__ == '__main__':
    unittest.main()
