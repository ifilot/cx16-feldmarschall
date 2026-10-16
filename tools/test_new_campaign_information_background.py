"""Exhaustive uniform-world oracle and full Classic inventory checks."""
import itertools
import unittest

from feldmarschall import COUNTS,GLYPHS,LAKES,setup_squares
from campaign_native_beliefs import quantize
from campaign_template_beliefs import TEMPLATES
from new_campaign_information_background import MissedCaptureRankBeliefs,condition_background
from test_new_campaign_information import MissedTests


class BackgroundTests(unittest.TestCase):
    def test_exhaustive_toy_worlds(self):
        for pool,U in (([0,3,10,11],3),([0,3,3,10],2),([0,3,3,10],3),([0,3,7,8],2)):
            counts=[pool.count(r) for r in range(12)]
            worlds=[w for w in set(itertools.permutations(pool)) if all(r<10 for r in w[U:])]
            for clue in (0,U):
                if clue>=len(pool):continue
                likelihood=lambda rank:.5 if rank<3 else 1.
                focal,others,Z=condition_background(counts,U,clue>=U,likelihood)
                total=sum(likelihood(w[clue]) for w in worlds)
                self.assertAlmostEqual(Z,total/len(worlds))
                for square in range(len(pool)):
                    expected=[sum(likelihood(w[clue]) for w in worlds if w[square]==r)/total for r in range(12)]
                    actual=focal if square==clue else others[square>=U]
                    for a,b in zip(actual,expected):self.assertAlmostEqual(a,b)

    def test_full_both_colors_counts_mobility_and_quantization(self):
        for army in (0,1):
            for moving_clue in (False,True):
                m=MissedCaptureRankBeliefs();m.observe(['new',('red','blue')[army]])
                m.observe(['setup',TEMPLATES[0]])
                cells=[254 if sq in LAKES else 255 for sq in range(100)];histories={}
                for sq,token in m.tokens.items():
                    if token[0]==army:cells[sq]=army*16+m.known[token]
                    else:
                        moved=token[1] in ({0,1,2} if moving_clue else {1,2})
                        cells[sq]=(1-army)*16+12+64*moved
                        histories[sq]=[0,0,sq,0,0,int(moved),1023 if moved else 4095]
                        if moved:m.moved.add(token)
                # Disclosed ranks alter the remaining inventory before conditioning.
                revealed=setup_squares(1-army)[4];token=m.tokens[revealed]
                m.known[token]=2;cells[revealed]=(1-army)*16+32+2
                histories.pop(revealed)
                m.miss=dict(origin=0,victim_rank=5)
                probabilities,remaining=m.rank_marginals(cells,army,m.lost,histories)
                for rank,n in enumerate(remaining):self.assertAlmostEqual(sum(p[rank] for p in probabilities.values()),n)
                for sq,p in probabilities.items():
                    self.assertAlmostEqual(sum(p),1.)
                    self.assertGreaterEqual(min(p),0.)
                    if histories[sq][-1]==1023:self.assertEqual(p[10:], [0.,0.])
                quantize(probabilities,remaining)

    def test_background_only_contact_changes(self):
        m=MissedCaptureRankBeliefs();m.observe(['new','red'])
        m.known[1,0]=0  # No source template has Marshal at origin0.
        before,_=m.posterior();self.assertEqual(before[-1],1.)
        m.miss=dict(origin=1,victim_rank=5)
        from new_campaign_information_background import background_row
        remaining,U,moved=m.context()
        original=background_row(remaining,U,False)
        focal,_,_=condition_background(remaining,U,False,m.likelihood)
        self.assertGreater(focal[10],original[10])
        self.assertLess(focal[1],original[1])

    def test_inherited_lifecycle_both_colors(self):
        for army in (0,1):
            m=MissedCaptureRankBeliefs();m.observe(['new',('red','blue')[army]])
            m.tokens={65:(army,0),55:(1-army,0),11:(1-army,1)}
            m.known={(army,0):3};m.disclosed={(army,0)};m.plies=1-army
            from feldmarschall import square_name
            m.observe(['moved',square_name(11),square_name(12)])
            self.assertIsNotNone(m.miss)
            m.observe(['battle',square_name(65),square_name(55),'4','5'])
            self.assertIsNone(m.miss)
            m.observe(['new',('red','blue')[army]])
            self.assertFalse(m.disclosed);self.assertEqual(m.miss_events,0)


if __name__=='__main__':unittest.main()
