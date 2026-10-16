"""Mechanical tests for bounded missed-opportunity evidence, both armies."""
import unittest

from campaign_template_beliefs import TemplateMixtureBeliefs
from feldmarschall import square_name
from new_campaign_information import MissedCaptureBeliefs,attacks


class MissedTests(unittest.TestCase):
    def fixture(self,army=0):
        m=MissedCaptureBeliefs();m.observe(['new',('red','blue')[army]])
        m.tokens={65:(army,0),55:(1-army,0),11:(1-army,1)}
        m.known={(army,0):3};m.disclosed={(army,0)};m.plies=1-army
        return m

    def event(self,m,source=11,target=12):
        m.observe(['moved',square_name(source),square_name(target)])

    def test_both_colors_and_no_compounding(self):
        for army in (0,1):
            m=self.fixture(army);self.event(m)
            self.assertEqual(m.miss['origin'],0)
            first=m.posterior()[0]
            m.plies=1-army;self.event(m,12,11)
            self.assertEqual(first,m.posterior()[0]);self.assertEqual(m.miss_events,1)

    def test_own_hidden_rank_is_not_used(self):
        m=self.fixture();m.disclosed.clear();self.event(m)
        self.assertIsNone(m.miss)

    def test_adjacent_or_scout_protection_rejects(self):
        for square,rank in ((66,5),(85,8)):
            m=self.fixture();m.tokens[square]=(0,1);m.known[0,1]=rank
            self.event(m);self.assertIsNone(m.miss)

    def test_moving_contact_is_not_missed_capture(self):
        m=self.fixture();self.event(m,55,54);self.assertIsNone(m.miss)

    def test_shuttle_ban(self):
        m=self.fixture();m.enemy_shuttle=(65,55,5);self.event(m)
        self.assertIsNone(m.miss)

    def test_invalid_event_has_no_evidence_side_effect(self):
        m=self.fixture()
        with self.assertRaises(ValueError):self.event(m,11,22)
        self.assertIsNone(m.miss);self.assertEqual(m.miss_events,0)

    def test_posterior_bounded_and_background_support(self):
        m=MissedCaptureBeliefs();m.observe(['new','red'])
        before=m.posterior()[0];m.miss=dict(origin=0,victim_rank=5)
        after,report=m.posterior()
        self.assertAlmostEqual(sum(after),1.)
        ratios=[after[i]/after[-1]/(before[i]/before[-1]) for i in range(8)]
        self.assertTrue(all(abs(r-.5)<1e-12 or abs(r-1)<1e-12 for r in ratios))
        self.assertTrue(any(abs(r-.5)<1e-12 for r in ratios))
        self.assertGreaterEqual(after[-1],before[-1])

    def test_disclosure_retires_evidence(self):
        m=self.fixture();self.event(m)
        # Next own move attacks the contact; public disclosure removes soft clue.
        m.observe(['battle',square_name(65),square_name(55),'4','5'])
        self.assertIsNone(m.miss)

    def test_background_and_templates_keep_exact_inventory(self):
        m=MissedCaptureBeliefs();m.observe(['new','red'])
        m.miss=dict(origin=0,victim_rank=3)
        weights,_=m.posterior()
        from feldmarschall import COUNTS
        for rank,n in enumerate(COUNTS):
            mass=sum(weights[i]*t.count(rank) for i,t in enumerate(m.templates))+weights[-1]*n
            self.assertAlmostEqual(mass,n)


if __name__=='__main__':unittest.main()
