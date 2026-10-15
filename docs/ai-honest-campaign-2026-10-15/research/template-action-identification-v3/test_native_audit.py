"""Public input, frozen native-prefix replay and calibration controls."""
import hashlib
import json
import shlex
import unittest
from audit_native_prefixes import (ROOT,OUT,POLICY,TEMPLATES,TemplateMixtureBeliefs,Engine,
                                  public_prediction,lookup,score)
from campaign_dos_deployment import rng_next


class NativeAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((OUT/'config.json').read_text())
        cls.result=json.loads((OUT/'result.json').read_text())

    def test_frozen_protocol_sources_and_both_rng_splits(self):
        self.assertEqual(self.result['config_sha256'],hashlib.sha256((OUT/'config.json').read_bytes()).hexdigest())
        for source,expected in self.config['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),expected)
        dos=self.config['DOS_private_research_rng'];own=self.config['native_own_private_research_rng']
        self.assertFalse(set(dos)&set(own));self.assertEqual(len(set(dos)),40);self.assertEqual(len(set(own)),40)
        self.assertFalse(set(own[:4])&set(own[4:8]));self.assertFalse(set(dos[:4])&set(dos[4:8]))
        effective=[(v&65535)or 1 for v in own]
        self.assertEqual(len(set(effective)),40)
        self.assertFalse(set(effective[:4])&set(effective[4:8]))
        self.assertFalse(set(effective)&set(dos))
        self.assertEqual(self.result['errors'],[])

    def test_all_hard_predictions_replay_using_only_public_events(self):
        for row in self.result['raw_rows']:
            model=TemplateMixtureBeliefs();model.observe(['new','red'])
            model.observe(['setup',self.config['own_formations'][row['formation']]])
            for words in row['transcript']:model.observe(words)
            for name,value in public_prediction(model).items():self.assertEqual(value,row[name])
            self.assertAlmostEqual(sum(row['hard_Flag']),1.)

    def test_lookup_has_exact_unseen_fallback_and_preserves_background(self):
        training=[r for r in self.result['raw_rows']if r['split']=='training']
        for row in self.result['raw_rows'][::31]:
            pred,support,components=lookup([],row)
            self.assertEqual(support,0)
            for a,b in zip(pred,row['hard_Flag']):self.assertAlmostEqual(a,b)
            owntrain=[r for r in training if r['formation']==row['formation']and r['step']==row['step']]
            pred,support,components=lookup(owntrain,row)
            self.assertEqual(components[-1],row['component_weights'][-1])
            mutated=dict(row,truth_Flag=999,branch='different',template=999,case='changed',RNG_seed=123)
            self.assertEqual(lookup(owntrain,mutated),(pred,support,components))

    def test_original_procedural_receipts_not_template_nonmembership(self):
        evidence=json.loads((OUT/'generation-evidence.json').read_text())
        self.assertEqual(len(evidence['selected']),32)
        for selected in evidence['selected']:
            audit=selected['audit'];_,first=rng_next(audit['pre_rng_state'])
            self.assertEqual(first%5,0)
            self.assertEqual(audit['branch'],'original-procedural')
            self.assertEqual(audit['assets_sha256'],self.config['assets_sha256'])
            self.assertIsNone(audit['template_index'])

    def test_proper_score_and_confident_error_controls(self):
        good=[0.]*40;good[3]=1.
        self.assertEqual(score(good,3)['logloss_nats'],0.)
        self.assertEqual(score(good,3)['brier'],0.)
        self.assertEqual(score(good,4)['confident_wrong'],1.)
        uniform=[.025]*40
        self.assertEqual(score(uniform,3)['confident_wrong'],0.)
        self.assertAlmostEqual(score(uniform,3)['top_tie_accuracy'],.025)

    def test_frozen_native_moves_reproduce_from_heldout_public_prefixes(self):
        # One template plus one procedural heldout trajectory per formation.
        program=ROOT/'build/ai-catalog'/POLICY/'engine'
        self.assertEqual(hashlib.sha256(program.read_bytes()).hexdigest(),self.config['native_runtime_sha256'])
        for name,own in self.config['own_formations'].items():
            candidates=[r for r in self.result['raw_rows']if r['formation']==name and r['split']=='heldout'and r['step']==4]
            for branch in('template','procedural'):
                row=next(r for r in candidates if r['branch']==branch)
                index=int(row['case'].split('-R')[1])if branch=='template'else 8+int(row['case'][1:])
                seed=self.config['native_own_private_research_rng'][index]
                bot=Engine(shlex.quote(str(program))+' --difficulty normal')
                try:
                    for line in('new red','rules 0','seed '+str(seed),'setup '+own):bot.send(line)
                    bot.ask('isready','readyok')
                    for ply,event in enumerate(row['transcript']):
                        if ply%2==0:self.assertEqual(bot.ask('go','move'),' '.join(event[1:3]))
                        bot.send(' '.join(event))
                finally:bot.close()


if __name__=='__main__':unittest.main()
