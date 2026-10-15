"""Campaign harness invariants, using canonical tournament report fixtures."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import campaign_cycle as campaign
import ai_registry
import information_strategy_cycle as analysis


def recipe(identity):
    return dict(id=identity, defines=[], driver='teacher', driver_args=[],
                archive='ai/sources/'+identity+'.zip', source_sha256=identity)


def fixture(directory):
    plan=dict(cycle=2, policies=['baseline','candidate'], baseline='baseline',opponent='dos',
              seed=2090001,rounds=1,jobs=4,max_plies=1000,backend='openmp',
              families=campaign.FAMILIES,new_policies=[],hypotheses=['Hypothesis'],
              contrasts=[['candidate','baseline']])
    frozen={p:recipe(p) for p in ['baseline','candidate','dos']}
    before=list(frozen.values())
    campaign.write(directory/'plan.json',plan)
    campaign.write(directory/'frozen-policies.json',frozen)
    campaign.write(directory/'registry-before.json',dict(policies=before))
    campaign.write(directory/'registration.json',dict(epoch=time.time()-10,
                   plan_sha256=campaign.digest(directory/'plan.json')))
    for p in plan['policies']:(directory/(p+'.fmtour')).write_bytes(b'artifact')
    def result(path, match, plan, frozen):
        identity=match['policy']
        wins=4 if identity=='baseline' else 6
        # Canonical standings have no errors field: errors belong to summary.
        summary=dict(games=14,errors=2,standings={identity:dict(wins=wins,draws=2,
                           losses=10-wins,score=(wins+1)/12)})
        report=dict(summary=summary,execution_seconds=1,
                    verification=dict(native_replayed_all_states=14))
        pairs={0:('uniform',dict(score=.25 if identity=='baseline' else .75))}
        return report,pairs,[('same-game','same-armies','same-seed')]
    return plan,frozen,before,result


class HarnessTests(unittest.TestCase):
    def test_source_archive_content_corruption_rejected_before_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'source.zip';archive.write_bytes(b'changed source')
            spec=dict(id='example-v1-normal',archive='source.zip',source_sha256='0'*64)
            with patch.object(ai_registry,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'Source archive failed integrity'):
                    ai_registry.build_policy(spec['id'],policy=spec)

    def test_interaction_uses_only_common_complete_pairs_across_four_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);directory=base/'cycle-01';directory.mkdir()
            plan,frozen,before,result=fixture(directory)
            plan.update(cycle=1,policies=['baseline','candidate','baseline32','candidate32'])
            for p in plan['policies'][2:]:
                frozen[p]=recipe(p);before.append(frozen[p])
                (directory/(p+'.fmtour')).write_bytes(b'artifact')
            campaign.write(directory/'plan.json',plan)
            campaign.write(directory/'frozen-policies.json',frozen)
            campaign.write(directory/'registry-before.json',dict(policies=before))
            registration=json.loads((directory/'registration.json').read_text())
            registration['plan_sha256']=campaign.digest(directory/'plan.json')
            campaign.write(directory/'registration.json',registration)
            scores=dict(baseline=.1,candidate=.2,baseline32=.3,candidate32=.7)
            def analyzed(path,match,plan,frozen):
                report,_,signature=result(path,match,plan,frozen)
                identity=match['policy']
                pairs={0:('uniform',dict(score=scores[identity]))}
                # Excluded pair missing from candidate32 must never contribute.
                if identity!='candidate32':pairs[1]=('uniform',dict(score=1))
                return report,pairs,signature
            with patch.object(campaign,'BASE',base),patch.object(campaign,'catalog',return_value=before), \
                 patch.object(campaign,'get_policy',side_effect=frozen.__getitem__), \
                 patch.object(campaign,'validate_metadata'),patch.object(campaign,'analyze_match',side_effect=analyzed):
                report=campaign.evaluate(directory)
            interaction=report['comparisons']['model by sampling-budget interaction']
            self.assertEqual(interaction['complete_pairs'],1)
            self.assertAlmostEqual(interaction['metrics']['score']['mean'],.3)

    def test_canonical_errors_survive_cumulative_overview(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);directory=base/'cycle-01';directory.mkdir()
            plan,frozen,before,result=fixture(directory)
            with patch.object(campaign,'BASE',base),patch.object(campaign,'catalog',return_value=before), \
                 patch.object(campaign,'get_policy',side_effect=frozen.__getitem__), \
                 patch.object(campaign,'validate_metadata'),patch.object(campaign,'analyze_match',side_effect=result):
                report=campaign.evaluate(directory)
            self.assertEqual(report['errors'],4)
            overview=(base/'OVERVIEW.md').read_text()
            self.assertIn('| 4 / 2 / 6 | 41.7% | 2 |',overview)
            self.assertIn('| 6 / 2 / 4 | 58.3% | 2 |',overview)

    def test_plan_mutation_is_rejected_before_any_game_or_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);plan,_,_,_=fixture(directory)
            plan['seed']+=1;campaign.write(directory/'plan.json',plan)
            with patch.object(campaign,'run') as runner,patch.object(campaign,'analyze_match') as analyzer:
                with self.assertRaises(AssertionError):campaign.evaluate(directory)
                runner.assert_not_called();analyzer.assert_not_called()

    def test_frozen_policy_recipe_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);_,frozen,before,_=fixture(directory)
            changed=copy.deepcopy(frozen);changed['candidate']['source_sha256']='changed'
            with patch.object(campaign,'catalog',return_value=before), \
                 patch.object(campaign,'get_policy',side_effect=changed.__getitem__), \
                 patch.object(campaign,'run') as runner:
                with self.assertRaises(AssertionError):campaign.evaluate(directory)
                runner.assert_not_called()

    def test_existing_catalog_entry_cannot_be_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);_,_,before,_=fixture(directory)
            changed=copy.deepcopy(before);changed[0]['driver_args']=['--diagnostic-truth']
            with patch.object(campaign,'catalog',return_value=changed),patch.object(campaign,'run') as runner:
                with self.assertRaises(AssertionError):campaign.evaluate(directory)
                runner.assert_not_called()

    def test_unmatched_armies_or_seeds_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);_,frozen,before,result=fixture(directory)
            def different(path,match,plan,frozen):
                report,pairs,signature=result(path,match,plan,frozen)
                if match['policy']=='candidate':signature=['different setup']
                return report,pairs,signature
            with patch.object(campaign,'catalog',return_value=before), \
                 patch.object(campaign,'get_policy',side_effect=frozen.__getitem__), \
                 patch.object(campaign,'validate_metadata'),patch.object(campaign,'analyze_match',side_effect=different):
                with self.assertRaisesRegex(AssertionError,'Unmatched'):campaign.evaluate(directory)

    def test_metadata_validates_all_fixed_matching_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);plan,frozen,_,_=fixture(directory)
            match=dict(policy='candidate',opponent='dos',seed=plan['seed'],rounds=plan['rounds'])
            correct=dict(status='complete',seed=plan['seed'],rounds=1,max_plies=1000,
                         families=campaign.FAMILIES,rules='classic',backend='openmp',
                         participants=[dict(policy=frozen[p]) for p in ('candidate','dos')])
            class FakeTournament:
                data=correct;count=14
                def __init__(self,path):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def metadata(self):return self.data
                def games(self):return [None]*self.count
            with patch.object(analysis,'Tournament',FakeTournament):
                analysis.validate_metadata(directory/'artifact',match,plan,frozen)
                for key,value in [('status','running'),('seed',1),('rounds',2),('max_plies',999),
                                  ('families',['uniform']),('rules','optional'),('backend','python'),
                                  ('participants',list(reversed(correct['participants'])))]:
                    with self.subTest(key=key):
                        FakeTournament.data=dict(correct,**{key:value})
                        with self.assertRaises(AssertionError):analysis.validate_metadata(directory/'artifact',match,plan,frozen)
                FakeTournament.data=correct;FakeTournament.count=13
                with self.assertRaises(AssertionError):analysis.validate_metadata(directory/'artifact',match,plan,frozen)

    def test_new_diagnostic_policy_is_rejected_before_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);plan,_,before,_=fixture(directory)
            (directory/'frozen-policies.json').unlink()
            plan['new_policies']=[dict(id='bad-v1-normal',defines=['AI_DIAGNOSTIC_TRUTH'])]
            campaign.write(directory/'plan.json',plan)
            with patch.object(campaign,'catalog',return_value=before),patch.object(campaign,'register') as register:
                with self.assertRaises(AssertionError):campaign.freeze(directory)
                register.assert_not_called()


if __name__=='__main__':unittest.main()
