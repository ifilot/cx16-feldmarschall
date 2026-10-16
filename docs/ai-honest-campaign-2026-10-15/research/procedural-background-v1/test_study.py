"""Frozen split, public posterior and scored-result reconstruction tests."""
import hashlib
import json
import math
import unittest
from structural_model import ROOT,StructuralModel,fit_row_odds
from study import OUT,EPSILONS,predict,primary
from feldmarschall import GLYPHS
from campaign_dos_deployment import rng_next


class FrozenStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=json.loads((OUT/'protocol.json').read_text())
        cls.generation=json.loads((OUT/'generation-evidence.json').read_text())
        cls.training=json.loads((OUT/'trained-model.json').read_text())
        cls.selection=json.loads((OUT/'calibration-selection.json').read_text())
        cls.result=json.loads((OUT/'result.json').read_text())
        cls.calibration=json.loads((OUT/'calibration-public-prefixes.json').read_text())
        cls.heldout=json.loads((OUT/'heldout-public-prefixes.json').read_text())
        cls.model=StructuralModel(weights=cls.training['weights'])

    def test_source_hashes_and_strict_seed_disjointness(self):
        self.assertEqual(self.result['protocol_sha256'],hashlib.sha256((OUT/'protocol.json').read_bytes()).hexdigest())
        for source,expected in self.protocol['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),expected)
        pools=list(self.protocol['private_deployment_candidate_pools'].values());allstates=[s for pool in pools for s in pool]
        self.assertEqual(len(allstates),len(set(allstates)))
        moves=[s for phase in self.protocol['independent_move_RNG'].values()for role in phase.values()for s in role]
        self.assertEqual(len(moves),192);self.assertEqual(len(set(moves)),192)
        self.assertTrue(all(0<s<65536 for s in moves));self.assertFalse(set(moves)&set(allstates))
        self.assertEqual(self.result['errors'],[])

    def test_exact_generator_branches_and_training_only_fit(self):
        selectedsets=[]
        for phase,evidence in self.generation.items():
            self.assertEqual(len(evidence['selected']),self.protocol['procedural_targets'][phase])
            selectedsets.append({row['audit']['pre_rng_state']for row in evidence['selected']})
            for row in evidence['selected']:
                _,first=rng_next(row['audit']['pre_rng_state']);self.assertEqual(first%5,0)
                self.assertEqual(row['audit']['branch'],'original-procedural')
                self.assertEqual(row['audit']['assets_sha256'],self.protocol['assets_sha256'])
        self.assertFalse(selectedsets[0]&selectedsets[1]|selectedsets[0]&selectedsets[2]|selectedsets[1]&selectedsets[2])
        weights,fit=fit_row_odds([[GLYPHS.index(g)for g in r['setup']]for r in self.generation['training']['selected']])
        self.assertEqual(weights,self.training['weights']);self.assertEqual(fit,self.training['fit'])

    def test_calibration_selection_frozen_before_heldout_queries(self):
        self.assertEqual(self.selection['calibration_prefixes_sha256'],hashlib.sha256((OUT/'calibration-public-prefixes.json').read_bytes()).hexdigest())
        self.assertTrue(self.selection['frozen_before_heldout_move_queries'])
        minimum=min(r['primary_delta']for r in self.selection['grid'])
        expected=max(r['epsilon']for r in self.selection['grid']if r['primary_delta']<=minimum+1e-12)
        self.assertEqual(self.selection['epsilon'],expected)
        self.assertEqual([r['epsilon']for r in self.selection['grid']],list(EPSILONS))
        self.assertGreaterEqual(self.selection['epsilon'],.01)

    def test_uniform_tail_identity_inventory_and_secret_metadata_invariance(self):
        for row in self.heldout[::17]:
            baseline=predict(row,self.model,1.,with_bombs=True)
            for a,b in zip(baseline['flag'],row['hard_Flag']):self.assertAlmostEqual(a,b)
            candidate=predict(row,self.model,self.selection['epsilon'],with_bombs=True)
            self.assertAlmostEqual(sum(candidate['flag']),1.)
            self.assertAlmostEqual(sum(candidate['bomb']),6.)
            self.assertTrue(all(p>0 for p,b in zip(candidate['flag'],row['background_Flag'])if b>0))
            mutated=dict(row,truth_Flag=999,truth_Bombs=[],phase='changed',formation='changed',case='changed',secret_seed=1)
            self.assertEqual(candidate,predict(mutated,self.model,self.selection['epsilon'],with_bombs=True))

    def test_posterior_only_uses_retained_public_rank_mobility_facts(self):
        from campaign_template_beliefs import TemplateMixtureBeliefs
        for row in self.heldout:
            model=TemplateMixtureBeliefs();model.observe(['new','red'])
            model.observe(['setup',self.protocol['own_formations'][row['formation']]])
            for event in row['transcript']:model.observe(event)
            self.assertEqual(row['known_enemy_origins'],{str(o):r for(owner,o),r in model.known.items()if owner==1})
            self.assertEqual(row['moved_enemy_origins'],sorted(o for owner,o in model.moved if owner==1))
        self.assertEqual(len(self.calibration),640);self.assertEqual(len(self.heldout),640)
        self.assertAlmostEqual(primary(self.result['scored_rows']),self.result['primary_delta_logloss']['mean'])


if __name__=='__main__':unittest.main()
