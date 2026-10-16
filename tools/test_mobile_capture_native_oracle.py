"""Compare reconstructed capture baselines against actual native expected_at."""
import random
import unittest
from campaign_mobile_capture import adjustments
import test_campaign_native_beliefs as native_fixture
import test_compact_backrow as public_fixture
from feldmarschall import setup_squares

class MobileNativeOracle(unittest.TestCase):
    def test_original_gain_and_exchangeable_zero_match_native_both_sides(self):
        native_fixture.NativeBeliefObjectives.setUpClass()
        helper=native_fixture.NativeBeliefObjectives('runTest');fixtures=public_fixture.CompactBackrowTests('runTest');checked=0
        try:
            for army in (0,1):
                for seed in range(6):
                    cells,lost=fixtures.fixture(army,2479000+seed)
                    remaining=fixtures.hidden(cells,army,lost);total=sum(remaining[:10]);self.assertGreater(total,0)
                    squares=[sq for sq,c in enumerate(cells) if c<254 and bool(c&16)!=bool(army) and not c&32]
                    rng=random.Random(seed);flag=[0]*100;bomb=[0]*100
                    for sq in squares:
                        if not cells[sq]&64:
                            flag[sq]=rng.randrange(4097);bomb[sq]=rng.randrange(4097-flag[sq])
                    marginals={sq:[n/total for n in remaining[:10]]+[0,0] for sq in squares}
                    source=setup_squares(army)[0]
                    for rank in range(10):
                        cells[source]=army*16|rank
                        helper.initialize(cells,lost,army=army*16);self.assertEqual(helper.set_priors(flag,bomb,army=army*16),1)
                        scores={(source,sq):0 for sq in squares};credit=dict.fromkeys(scores,0)
                        delta,report=adjustments(cells,army,lost,remaining,marginals,flag,bomb,scores,credit)
                        self.assertFalse(any(delta.values()))
                        for row in report['captures']:
                            sq=row['move'][1]
                            self.assertEqual(row['original_capture_gain'],helper.lib.belief_expected(rank,sq),(army,seed,rank,sq))
                            checked+=1
            self.assertGreater(checked,1000)
        finally:native_fixture.NativeBeliefObjectives.tearDownClass()

if __name__=='__main__':unittest.main()
