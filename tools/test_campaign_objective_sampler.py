"""Actual native public-prefix adapter checks for isolated objective sampler."""
import copy
import hashlib
import json
import random
import shlex
import unittest

from ai_registry import ROOT,build_policy
from calibrated_beliefs import BeliefModel
from campaign_inverse_objectives import ObjectiveSampler
from feldmarschall import COUNTS,Engine,square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

MODELS=[ROOT/'ai/models'/f'{name}-own-flag-motion-beliefs-v1.json' for name in ['mirrored']]
MODELS.insert(0,ROOT/'ai/models/own-flag-motion-beliefs-v1.json')

class ObjectiveSamplerAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program,_=build_policy('teacher-calibrated-beliefs-v1-normal');cls.observer=program.parent/'observer'
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:cls.game=saved.game(9)
        states,_=replay(cls.game);cls.events=public_events(cls.game,states)

    def root(self,model,army,plies=80):
        observer=Engine(shlex.quote(str(self.observer)));self.addCleanup(observer.close)
        for line in ['new '+('red','blue')[army],'rules 0','setup '+self.game[('red_setup','blue_setup')[army]]]+self.events[:plies]:
            model.observe(line.split());observer.send(line)
        side,board,lost,_=observer.ask('public','public').split();cells=list(bytes.fromhex(board))
        histories={sq:list(map(int,observer.ask('memory '+square_name(sq),'history').split()))
            for sq,c in enumerate(cells) if c<254 and bool(c&16)!=bool(army) and not c&32}
        return cells,list(bytes.fromhex(lost)),histories

    def test_both_assets_actual_public_prefixes_counts_masks_and_private_nibble_invariance(self):
        for path in MODELS:
            for army in (0,1):
                model=ObjectiveSampler.load(path);cells,lost,histories=self.root(model,army)
                first=model.sample_worlds(cells,lost,histories,random.Random(319),army,8)
                mutated=cells[:]
                for sq in histories:mutated[sq]=(mutated[sq]&240)|(sq%12)
                second=model.sample_worlds(mutated,lost,histories,random.Random(319),army,8)
                self.assertEqual(first,second)
                for world,weight in first:
                    counts=lost[:]
                    for sq,c in enumerate(world):
                        if c<254 and bool(c&16)!=bool(army):counts[c&15]+=1
                        if sq in histories:self.assertTrue(histories[sq][-1]&(1<<(c&15)))
                    self.assertEqual(counts,list(COUNTS));self.assertGreater(weight,0)
                self.assertTrue(model.memory.last)

    def test_generated_setup_callback_required_before_public_events_and_sampling(self):
        model=ObjectiveSampler.load(MODELS[0]);model.observe(['new','red']);model.observe(['setup'])
        with self.assertRaisesRegex(ValueError,'own setup'):model.observe(self.events[0].split())
        with self.assertRaisesRegex(ValueError,'own setup'):model.prepare([],[],{},0)
        model.observe(['setup',self.game['red_setup']]);model.observe(self.events[0].split())
        self.assertTrue(model.memory.own_setup_recorded)
        model.observe(['new','blue']);self.assertFalse(model.memory.own_setup_recorded);self.assertFalse(model.memory.last)

    def test_honesty_and_stale_public_state_rejected(self):
        model=ObjectiveSampler.load(MODELS[0]);cells,lost,h=self.root(model,0)
        with self.assertRaisesRegex(ValueError,'rejects opponent setup'):model.observe(['opponent-setup',self.game['blue_setup']])
        sq=next(iter(h));stale=copy.deepcopy(h);stale[sq][2]=(stale[sq][2]+1)%100
        with self.assertRaisesRegex(ValueError,'origin'):model.prepare(cells,lost,stale,0)
        with self.assertRaisesRegex(ValueError,'another side'):model.prepare(cells,lost,h,1)
        bad=cells[:];own=next(s for s,c in enumerate(cells) if c<254 and not c&16);bad[own]=(bad[own]&240)|((bad[own]+1)%12)
        with self.assertRaisesRegex(ValueError,'own rank'):model.prepare(bad,lost,h,0)

    def test_zero_strength_facade_exact_base_rng(self):
        document=json.loads(MODELS[0].read_text());document['factor_strength']=0
        facade=ObjectiveSampler(document);base=BeliefModel(document['base_document'])
        cells,lost,h=self.root(facade,0)
        self.assertEqual(facade.sample_worlds(cells,lost,h,random.Random(122),0,8),
                         base.sample_worlds(cells,lost,h,random.Random(122),0,8))

    def test_assets_exact_matched_control_and_preserved_evidence(self):
        real,control=[json.loads(path.read_text()) for path in MODELS]
        self.assertEqual(real['base_document'],control['base_document']);self.assertEqual(real['factor_strength'],.5)
        self.assertEqual(control['factor_strength'],.5);self.assertEqual(real['selected_features'],[0,1,2])
        self.assertEqual(real['selected_features'],control['selected_features'])
        self.assertFalse(real['mirrored_control']);self.assertTrue(control['mirrored_control'])
        for document in [real,control]:
            for name,digest in document['provenance']['files'].items():
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
            parts=document['provenance']['partitions']
            self.assertFalse(set(parts['train']['pairs'])&set(parts['calibration']['pairs']))
        self.assertEqual(real['base_document'],json.loads((ROOT/'ai/models/public-history-beliefs-v1.json').read_text()))

if __name__=='__main__':unittest.main()
