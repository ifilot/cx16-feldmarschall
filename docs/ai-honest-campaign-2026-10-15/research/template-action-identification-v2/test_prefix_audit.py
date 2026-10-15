"""Public sequential-conditioning and inference controls; no original-engine calls."""
import hashlib
import json
import unittest
from audit_prefixes import (OUT,ROOT,TEMPLATES,TemplateMixtureBeliefs,Position,
                           own_public_moves,hard_state,classify)


class PrefixAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((OUT/'config.json').read_text())
        cls.result=json.loads((OUT/'result.json').read_text())

    def test_replay_every_prefix_reproduces_all_hard_facts(self):
        # Reconstruct ONLY from own army and recorded public protocol events.
        for row in self.result['raw_rows']:
            model=TemplateMixtureBeliefs();model.observe(['new','red'])
            model.observe(['setup',self.config['own_formations'][row['formation']]])
            for words in row['transcript']:model.observe(words)
            state=hard_state(model)
            for key,value in state.items():self.assertEqual(value,row[key])
            self.assertIn(row['template'],state['compatible'])

    def test_captured_disclosure_is_retained(self):
        model=TemplateMixtureBeliefs();model.observe(['new','red'])
        model.observe(['setup',self.config['own_formations']['Fortress']])
        model.observe(['battle','a4','a7','9','9'])
        self.assertNotIn(30,model.tokens)
        self.assertEqual(model.known[1,0],8)
        self.assertEqual(model.lost[8],1)
        self.assertEqual(hard_state(model)['compatible'],[1,3])

    def test_own_legal_policy_has_no_private_rank_dependence(self):
        p=Position();p.place(0,self.config['own_formations']['Fortress']);p.place(1,TEMPLATES[0])
        reference=own_public_moves(p)
        for rank in range(12):
            for c in p.cells:
                if c and c[0]==1:c[1]=rank
            self.assertEqual(own_public_moves(p),reference)

    def test_exact_prefix_conditioning_and_unseen_prefix_fallback(self):
        row={'transcript':[['moved','a7','a6']],'compatible':[0,2]}
        training=[dict(row,template=0)]*4
        self.assertEqual(classify(training,row)[0],[5/6,0,1/6,0,0,0,0,0])
        # Identical last action after a DIFFERENT public past is not pooled.
        other=dict(row,transcript=[['moved','f4','f5'],['moved','a7','a6']])
        self.assertEqual(classify(training,other),([.5,0,.5,0,0,0,0,0],0))

    def test_balanced_repeated_path_does_not_invent_information(self):
        row={'transcript':[['moved','a7','a6'],['moved','a6','a7']],'compatible':[0,2]}
        training=[dict(row,template=t)for t in(0,2)for k in range(4)]
        self.assertEqual(classify(training,row)[0],[.5,0,.5,0,0,0,0,0])

    def test_frozen_source_config_split_and_complete_counts(self):
        for source,expected in self.config['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),expected)
        self.assertEqual(len(self.result['raw_rows']),1024)
        self.assertEqual(self.result['config_sha256'],hashlib.sha256((OUT/'config.json').read_bytes()).hexdigest())
        for row in self.result['raw_rows']:
            self.assertEqual(row['split'],'training'if row['rng_index']<4 else'heldout')
            self.assertEqual(len(row['transcript']),2*row['step'])
        self.assertFalse(set(self.config['dos_private_research_rng'])&set(self.config['own_private_research_rng_by_formation'].values()))


if __name__=='__main__':unittest.main()
