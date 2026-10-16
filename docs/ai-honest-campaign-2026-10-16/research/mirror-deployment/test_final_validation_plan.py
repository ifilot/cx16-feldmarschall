"""Synthetic branch tests; never read actual screen outcomes or launch games."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import ai_registry
spec=importlib.util.spec_from_file_location('final_plan',HERE/'prepare_final_validation.py')
planner=importlib.util.module_from_spec(spec);spec.loader.exec_module(planner)


class FinalBranches(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.base=self.root/'campaign';self.here=self.base/'research/mirror';self.here.mkdir(parents=True)
        self.protocol=json.loads((HERE/'FINAL-VALIDATION-PROTOCOL.json').read_text())
        self.patches=[patch.object(planner,k,v)for k,v in [('ROOT',self.root),('BASE',self.base),('HERE',self.here)]]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in self.patches:p.stop()
        self.temp.cleanup()

    def screens(self,means):
        for key in ('dos_screen','honest_screen'):
            d=self.base/key;d.mkdir()
            plan=b'{}\n';(d/'plan.json').write_bytes(plan)
            result=dict(attempts=2,verified_games=2,comparisons={
                identity+' minus '+self.protocol['baseline']:dict(metrics=dict(score=dict(mean=mean)))
                for identity,mean in zip(self.protocol['candidate_order'],means)})
            (d/'result.json').write_text(json.dumps(result))
            (d/'audit.json').write_text(json.dumps(dict(passed=True,attempts=2)))
            (d/'checks.log').write_text('Synthetic fixture, no games\n')
            manifest={p.name:planner.sha(p)for p in d.iterdir()}
            (d/'manifest.json').write_text(json.dumps(manifest))
            self.protocol[key]=dict(directory=str(d.relative_to(self.root)),plan_sha256=hashlib.sha256(plan).hexdigest())
        (self.here/'FINAL-VALIDATION-PROTOCOL.json').write_text(json.dumps(self.protocol))

    def test_larger_positive_mean_selected(self):
        self.screens([.01,.03]);result=planner.prepare(True)
        self.assertEqual(result['selected_policy'],self.protocol['candidate_order'][1])
        self.assertEqual(result['planned_attempts'],2048)
        self.assertEqual(result['games_launched'],0)

    def test_exact_tie_uses_fixed_mirror(self):
        self.screens([.02,.02]);result=planner.prepare(True)
        self.assertEqual(result['selected_policy'],self.protocol['candidate_order'][0])

    def test_no_positive_mean_prepares_single_policy_replication(self):
        self.screens([0.,-.01]);result=planner.prepare(True)
        self.assertIsNone(result['selected_policy'])
        self.assertEqual(result['branch'],'unchanged-best-score-replication')
        self.assertEqual(result['planned_attempts'],1024)
        plan=json.loads((self.root/result['directory']/'plan.json').read_text())
        self.assertEqual(plan['policies'],[self.protocol['baseline']]);self.assertEqual(plan['contrasts'],[])
        self.assertEqual(plan['rounds'],512);self.assertEqual(plan['seed'],3119001)

    def test_no_authorization_cannot_prepare(self):
        self.screens([.1,.2])
        with self.assertRaisesRegex(ValueError,'Parent authorization'):planner.prepare(False)
        self.assertFalse(list(self.base.glob('cycle-119*')))


if __name__=='__main__':unittest.main()
