"""Focused runner contract tests; no validation games are played."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
import new_campaign_cycle as runner
from setup_dataset import DEVELOPMENT


class RunnerContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.directory=self.base/'cycle-101-contract'
        self.directory.mkdir()
        self.patch=patch.object(runner,'BASE',self.base);self.patch.start()
        self.plan=dict(cycle=101,baseline='control',opponent='honest',policies=['control','candidate'],
            new_policies=[],contrasts=[['candidate','control']],seed=1,rounds=1,jobs=1,
            max_plies=40,backend='openmp',setup_mode='referee',families=list(DEVELOPMENT),
            hypotheses=['A fixed mechanism test'],dataset=dict(
                path='tests/datasets/classic-generalization-v1',split='development',offset=0))
        self.save()

    def tearDown(self):
        self.patch.stop();self.temp.cleanup()

    def save(self):
        runner.write(self.directory/'plan.json',self.plan)

    def test_real_development_corpus_selection(self):
        self.assertEqual(runner.check_plan(self.directory),self.plan)

    def test_family_mismatch_rejected(self):
        self.plan['families']=list(reversed(DEVELOPMENT));self.save()
        with self.assertRaisesRegex(ValueError,'families'):
            runner.check_plan(self.directory)

    def test_no_wrapping_out_of_range_records(self):
        self.plan['dataset']['offset']=64;self.save()
        with self.assertRaises(ValueError):runner.check_plan(self.directory)

    def test_nonreferee_and_old_campaign_rejected(self):
        self.plan['setup_mode']='policy-owned';self.save()
        with self.assertRaisesRegex(ValueError,'referee'):runner.check_plan(self.directory)
        self.plan['setup_mode']='referee';self.plan['cycle']=1;self.save()
        with self.assertRaisesRegex(ValueError,'101'):runner.check_plan(self.directory)

    def test_overview_preserves_hypothesis_and_unscored_errors(self):
        standing=dict(wins=1,draws=2,losses=1,errors=3)
        runner.write(self.directory/'result.json',dict(
            standings={'candidate':standing},comparisons={}))
        runner.overview()
        text=(self.base/'OVERVIEW.md').read_text()
        self.assertIn('A fixed mechanism test',text)
        self.assertIn('honest; development corpus',text)
        self.assertIn('1 / 2 / 1 | 50.0% | 3',text)


if __name__=='__main__':unittest.main()
