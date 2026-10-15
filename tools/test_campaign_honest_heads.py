"""Plan-only preparation, immutable input guards and direct fair-null reporting."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import campaign_honest_heads as heads


class HonestHeads(unittest.TestCase):
    def test_prespecified_direct_matches_and_no_self_play(self):
        document=heads.plan(); heads.validate_plan(document)
        self.assertEqual([m['seed'] for m in document['matches']],[2250001,2260001,2270001])
        self.assertEqual(document['planned_games'],4200)
        self.assertTrue(all(m['policy']!=m['opponent'] for m in document['matches']))
        for key,value in (('rounds',99),('setup_mode','policy-owned'),('null_score',0)):
            changed=copy.deepcopy(document);changed[key]=value
            with self.assertRaises(ValueError):heads.validate_plan(changed)

    def test_prepare_and_audit_without_running_games_then_detect_recipe_and_plan_changes(self):
        with tempfile.TemporaryDirectory(prefix='honest-head-plan-') as temporary:
            root=Path(temporary);(root/'source.zip').write_bytes(b'frozen archive proof')
            prefix=[dict(id='catalog-sentinel')]
            def policy(identity):
                return dict(id=identity,difficulty='normal',archive='source.zip',
                            source_sha256=heads.digest(root/'source.zip'))
            with patch.object(heads,'ROOT',root),patch.object(heads,'catalog',return_value=prefix),\
                    patch.object(heads,'get_policy',side_effect=policy),patch('tournament.run') as runner:
                folder=root/'cohort';heads.prepare(folder);heads.audit(folder)
                runner.assert_not_called()
                self.assertEqual(list(folder.glob('*.fmtour')),[])
                with self.assertRaises(ValueError):heads.prepare(folder)
                # Appending unrelated IDs is safe; rewriting any old ID is not.
                prefix.append(dict(id='future-added-policy'));heads.audit(folder)
                prefix[0]['id']='rewritten'
                with self.assertRaises(ValueError):heads.audit(folder)
                prefix[0]['id']='catalog-sentinel'
                (folder/'plan.json').write_text('{}')
                with self.assertRaises(ValueError):heads.audit(folder)

    def test_score_and_intervals_translate_around_half_without_mutating_report(self):
        report=dict(match=dict(policy='candidate'),summary=dict(games=10,errors=2,
                    standings=dict(candidate=dict(wins=4,draws=2,losses=2,score=.625))),
                    complete_pair_statistics=dict(complete_pairs=3,metrics=dict(score=dict(
                        mean=.6,interval_95=[.51,.7],interval_98_3333=[.48,.72]))))
        original=copy.deepcopy(report);result=heads.score_endpoint(report)
        self.assertEqual(report,original)
        self.assertEqual(result['all_attempt_score_bounds'],[.5,.7])
        self.assertAlmostEqual(result['paired_score_minus_half']['mean'],.1)
        self.assertAlmostEqual(result['paired_score_minus_half']['interval_95'][0],.01)
        self.assertTrue(result['exceeds_half_95'])
        self.assertFalse(result['exceeds_half_98_3333'])

    def test_failed_attempt_keeps_prefix_and_traceback_without_starting_other_matches(self):
        with tempfile.TemporaryDirectory(prefix='honest-head-failure-') as temporary:
            folder=Path(temporary);document=heads.plan()
            def fail(first,second,path,**kwargs):
                path.write_bytes(b'preserved failure prefix')
                raise RuntimeError('simulated engine failure')
            with patch.object(heads,'freeze_analysis'),patch.object(heads,'audit',return_value=(document,{})),\
                    patch('tournament.run',side_effect=fail) as runner:
                with self.assertRaisesRegex(RuntimeError,'simulated engine failure'):heads.run(folder)
                self.assertEqual(runner.call_count,1)
            prefix=folder/(document['matches'][0]['name']+'.fmtour')
            self.assertEqual(prefix.read_bytes(),b'preserved failure prefix')
            self.assertIn('simulated engine failure',prefix.with_suffix('.log').read_text())
            self.assertTrue((folder/'manifest.json').exists())

    def test_all_errors_remain_unscored_and_have_no_bootstrap_endpoint(self):
        report=dict(match=dict(policy='candidate'),summary=dict(games=4,errors=4,
                    standings=dict(candidate=dict(wins=0,draws=0,losses=0,score=None))),
                    complete_pair_statistics=None)
        result=heads.score_endpoint(report)
        self.assertEqual(result['all_attempt_score_bounds'],[0,1])
        self.assertIsNone(result['paired_score'])
        self.assertEqual(result['official_scored']['losses'],0)


if __name__=='__main__':unittest.main()
