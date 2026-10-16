"""Independent honesty, retirement, inventory and geometry review.

Does not modify the registered runtime. One test records the discovered gate
limitation explicitly so a future corrected immutable version has a fixture.
"""
import unittest

from campaign_native_template import NativeTemplateBot
from campaign_template_beliefs import TemplateMixtureBeliefs,TEMPLATES
from campaign_native_beliefs import quantize
from new_campaign_information import attacks
from new_campaign_information_background import MissedCaptureRankBeliefs
from feldmarschall import COUNTS,setup_squares


def public_inputs(model):
    cells=[255]*100;histories={}
    for sq,token in model.tokens.items():
        rank=model.known.get(token);moved=token in model.moved
        cells[sq]=token[0]*16+(12 if rank is None else rank)+64*moved+32*(rank is not None and token[0]!=model.army)
        if token[0]!=model.army and rank is None:
            histories[sq]=[0,0,setup_squares(token[0])[token[1]],0,0,int(moved),1023 if moved else 4095]
    return cells,model.lost,histories


class Review(unittest.TestCase):
    def model(self,army=0):
        model=MissedCaptureRankBeliefs();model.observe(['new',('red','blue')[army]])
        model.observe(['setup',TEMPLATES[0]])
        return model

    def check_inventory(self,model):
        cells,lost,histories=public_inputs(model)
        marginals,remaining=model.rank_marginals(cells,model.army,lost,histories)
        for rank,n in enumerate(remaining):self.assertAlmostEqual(sum(p[rank] for p in marginals.values()),n)
        quantize(marginals,remaining)
        return marginals,remaining

    def test_no_event_exact_default_parity(self):
        for army in (0,1):
            model=self.model(army);baseline=TemplateMixtureBeliefs();baseline.__dict__.update(model.__dict__)
            cells,lost,histories=public_inputs(model)
            self.assertIsNone(model.miss)
            self.assertEqual(model.rank_marginals(cells,army,lost,histories),baseline.rank_marginals(cells,army,lost,histories))

    def test_captured_disclosed_counts_are_not_subtracted_twice(self):
        for army in (0,1):
            model=self.model(army);enemy=1-army
            # Removed enemy origins remain publicly known after capture. They
            # contribute to lost[] and must be removed once from hidden counts.
            for origin,rank in ((5,0),(7,3),(9,7)):
                sq=setup_squares(enemy)[origin];model.tokens.pop(sq)
                model.known[enemy,origin]=rank;model.lost[rank]+=1
            # A live disclosed enemy is removed from hidden counts but not lost.
            sq=setup_squares(enemy)[8];model.known[enemy,8]=4
            model.miss=dict(origin=0,victim_rank=5)
            _,remaining=self.check_inventory(model)
            self.assertEqual(remaining[0],COUNTS[0]-1)
            self.assertEqual(remaining[3],COUNTS[3]-1)
            self.assertEqual(remaining[4],COUNTS[4]-1)
            self.assertEqual(remaining[7],COUNTS[7]-1)

    def test_concealed_nibble_invariance(self):
        model=self.model();model.miss=dict(origin=0,victim_rank=5)
        cells,lost,histories=public_inputs(model)
        reference=model.rank_marginals(cells,0,lost,histories)
        for rank in range(12):
            changed=[(c&240)|rank if sq in histories else c for sq,c in enumerate(cells)]
            self.assertEqual(model.rank_marginals(changed,0,lost,histories),reference)

    def test_private_input_rejected_and_seed_ignored(self):
        model=self.model();before=model.posterior()
        model.observe(['seed','1']);model.observe(['seed','999'])
        self.assertEqual(model.posterior(),before)
        with self.assertRaises(ValueError):model.observe(['opponent-setup',TEMPLATES[0]])

    def test_documented_scout_source_vacancy_limitation(self):
        # Own Scout45 would recapture target65 once enemy55 leaves55 to capture.
        # Current gate tests original occupancy and misses that protection.
        tokens={45:(0,1),55:(1,0),65:(0,0)}
        self.assertFalse(attacks(45,65,8,tokens))
        after=tokens.copy();after.pop(55)
        self.assertTrue(attacks(45,65,8,after))


if __name__=='__main__':unittest.main()
