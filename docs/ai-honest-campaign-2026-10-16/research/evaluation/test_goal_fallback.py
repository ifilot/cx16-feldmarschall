"""Independent arithmetic check of moved/unmoved exchangeable fallback."""
from fractions import Fraction
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'tools'))
from campaign_belief_values import gain,worths,native_expected
from feldmarschall import COUNTS
from new_campaign_objectives import goal_values


class UniformFallback(unittest.TestCase):
    def test_both_colors_moved_unmoved_and_empty_mobile_mass(self):
        rng=random.Random(20261016104)
        for trial in range(240):
            remaining=[rng.randrange(n+1) for n in COUNTS]
            if not sum(remaining[:10]):remaining[8]=1
            lost=[n-r for n,r in zip(COUNTS,remaining)]
            worth=worths(lost);h=sum(remaining[:10])
            for army in (0,1):
                for moved in (False,True):
                    f=rng.randrange(4097);b=rng.randrange(4097-f)
                    cells=[255]*100;cells[35]=(16 if army==0 else 0)|12|(64 if moved else 0)
                    exchange=[n/h for n in remaining[:10]]+[0.,0.]
                    for row in (exchange,[0.]*12):
                        table=goal_values(cells,army,lost,remaining,{35:row},[f]*100,[b]*100)
                        for actor in range(10):
                            numerator=((0 if moved else f)*2000+(0 if moved else b)*gain(actor,10,worth))*h
                            numerator+=(4096-(0 if moved else f+b))*sum(n*gain(actor,r,worth) for r,n in enumerate(remaining[:10]))
                            expected=native_expected(actor,True,remaining,worth) if moved else int(Fraction(numerator,4096*h))
                            self.assertEqual(table[actor][35],expected,(trial,army,moved,actor))


if __name__=='__main__':unittest.main()
