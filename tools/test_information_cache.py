"""A completed cohort cannot be reused under different frozen settings."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_registry import ROOT
from information_strategy_cycle import analyze_phase, document_digest, matches

OUT=ROOT/'docs/ai-fair-information-2026-10-15'


class CohortCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((OUT/'plan.json').read_text())
        cls.frozen=json.loads((OUT/'frozen-policies.json').read_text())

    def test_valid_cache_preserves_verified_report_without_replaying(self):
        with patch('information_strategy_cycle.analyze_match',side_effect=AssertionError('Unexpected replay')):
            result=analyze_phase(OUT,'pilot',self.plan,self.frozen)
        self.assertEqual(result['plan_sha256'],document_digest(self.plan))
        self.assertEqual(sum(m['summary']['games'] for m in result['matches'].values()),490)

    def test_changed_seed_is_rejected(self):
        plan=copy.deepcopy(self.plan);plan['cohorts']['pilot']['dos_seed']+=1
        with self.assertRaisesRegex(AssertionError,'Cached plan differs'):
            analyze_phase(OUT,'pilot',plan,self.frozen)

    def test_changed_policy_recipe_is_rejected(self):
        frozen=copy.deepcopy(self.frozen);frozen[self.plan['baseline']]['model']='Different model'
        with self.assertRaisesRegex(AssertionError,'Cached policies differ'):
            analyze_phase(OUT,'pilot',self.plan,frozen)

    def test_metadata_is_checked_even_if_cache_binding_is_rewritten(self):
        plan=copy.deepcopy(self.plan);plan['cohorts']['pilot']['dos_seed']+=1
        report=json.loads((OUT/'pilot/report.json').read_text())
        report['plan_sha256']=document_digest(plan)
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary);phase=out/'pilot';phase.mkdir()
            (phase/'report.json').write_text(json.dumps(report))
            for match in matches(self.plan,'pilot'):
                name=match['name']+'.fmtour'
                (phase/name).symlink_to(OUT/'pilot'/name)
            with self.assertRaises(AssertionError):analyze_phase(out,'pilot',plan,self.frozen)


if __name__=='__main__':unittest.main()
