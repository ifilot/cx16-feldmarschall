"""Tests of the information/control analysis, no tournament execution."""
import hashlib
import json
import unittest
from audit_opening_actions import (OUT,ROOT,TEMPLATES,compatibility,empirical_information,
                                  predict,summarize,first_own_quiet)
from feldmarschall import Position,GLYPHS


class OpeningAudit(unittest.TestCase):
    def test_hard_constraint_includes_revealed_scout(self):
        self.assertEqual(compatibility(dict(origin=9,revealed_rank=None)),tuple(range(8)))
        self.assertEqual(compatibility(dict(origin=9,revealed_rank=8)),(0,2))

    def test_analyzer_detects_extra_action_information(self):
        rows=[dict(template=t,event=[t,50,None],origin=0,compatible=list(range(8)),
                   rng_index=k,split='training'if k<4 else'heldout')
              for t in range(8)for k in range(8)]
        self.assertAlmostEqual(empirical_information(rows)[
            'plugin_template_action_conditional_mi_given_compatibility_mask_bits'],3.)
        self.assertGreater(summarize(rows)['heldout_means']['flag_logscore_gain_bits'],0.)

    def test_identical_action_has_no_classifier_information(self):
        rows=[dict(template=t,event=[30,40,None],origin=0,compatible=list(range(8)),
                   rng_index=k,split='training'if k<4 else'heldout')
              for t in range(8)for k in range(8)]
        summary=summarize(rows)
        self.assertEqual(summary['all_samples_information']['plugin_template_action_mi_bits'],0.)
        self.assertEqual(summary['heldout_means']['flag_logscore_gain_bits'],0.)
        self.assertEqual(predict(rows[:0],[30,40,None],range(8)),[.125]*8)

    def test_actual_results_have_no_increment_and_preserve_true_template(self):
        d=json.loads((OUT/'result.json').read_text())
        self.assertEqual(len(d['raw_rows']),256)
        for row in d['raw_rows']:
            self.assertIn(row['template'],row['compatible'])
            self.assertEqual(row['compatible'],list(compatibility(row)))
        for summary in d['summaries'].values():
            self.assertEqual(summary['all_samples_information'][
                'plugin_template_action_conditional_mi_given_compatibility_mask_bits'],0.)
            self.assertEqual(summary['heldout_means']['flag_logscore_gain_bits'],0.)
            self.assertEqual(summary['heldout_means']['action_top_flag_tie_accuracy'],.5)

    def test_original_config_and_source_hashes_unchanged(self):
        config=json.loads((OUT/'config.json').read_text())
        result=json.loads((OUT/'result.json').read_text())
        self.assertEqual(result['config_sha256'],hashlib.sha256((OUT/'config.json').read_bytes()).hexdigest())
        for source,expected in config['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),expected)
        self.assertEqual(len(set(config['private_research_move_rng_seeds'])),8)
        self.assertTrue(all(1<=s<=65535 for s in config['private_research_move_rng_seeds']))

    def test_own_first_move_uses_only_public_enemy_occupancy(self):
        config=json.loads((OUT/'config.json').read_text())
        for own in config['own_formations'].values():
            selected=first_own_quiet(own)
            for template in TEMPLATES:
                p=Position();p.place(0,own);p.place(1,template)
                self.assertIn(selected,p.moves(0))
                self.assertIsNone(p.cells[selected[1]])


if __name__=='__main__':unittest.main()
