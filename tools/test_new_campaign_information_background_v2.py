"""Recapture geometry correction and unchanged eligibility gates, both armies."""
import unittest

from new_campaign_information_background import MissedCaptureRankBeliefs
from new_campaign_information_background_v2 import SourceVacancyMissedCaptureBeliefs
from test_new_campaign_information_background import BackgroundTests


class VacancyTests(unittest.TestCase):
    def fixture(self,army=0,cls=SourceVacancyMissedCaptureBeliefs):
        m=cls();m.observe(['new',('red','blue')[army]])
        m.tokens={65:(army,0),55:(1-army,0),11:(1-army,1)}
        m.known={(army,0):3};m.disclosed={(army,0)};m.plies=1-army
        return m

    def test_new_scout_ray_after_source_vacates_both_colors(self):
        for army in (0,1):
            original=self.fixture(army,MissedCaptureRankBeliefs)
            fixed=self.fixture(army)
            for m in (original,fixed):
                m.tokens[45]=(army,1);m.known[army,1]=8;m.disclosed.add((army,1))
            self.assertEqual(len(original.opportunities((1-army,1))),1)
            self.assertEqual(fixed.opportunities((1-army,1)),[])

    def test_other_blocker_keeps_ray_blocked(self):
        for army in (0,1):
            m=self.fixture(army)
            m.tokens[35]=(army,1);m.known[army,1]=8
            m.tokens[45]=(1-army,2)
            self.assertEqual(len(m.opportunities((1-army,1))),1)

    def test_actor_shuttle_and_hidden_victim_gates_unchanged(self):
        for army in (0,1):
            for cls in (MissedCaptureRankBeliefs,SourceVacancyMissedCaptureBeliefs):
                m=self.fixture(army,cls)
                self.assertEqual(m.opportunities((1-army,0)),[])
                m.enemy_shuttle=(65,55,5)
                self.assertEqual(m.opportunities((1-army,1)),[])
                m.enemy_shuttle=None;m.disclosed.clear()
                self.assertEqual(m.opportunities((1-army,1)),[])

    def test_unchanged_unprotected_candidates_and_order(self):
        for army in (0,1):
            old=self.fixture(army,MissedCaptureRankBeliefs);new=self.fixture(army)
            self.assertEqual(old.opportunities((1-army,1)),new.opportunities((1-army,1)))

    def test_posterior_same_for_same_stored_observation(self):
        for army in (0,1):
            old=self.fixture(army,MissedCaptureRankBeliefs);new=self.fixture(army)
            old.miss=new.miss=dict(origin=0,victim_rank=5)
            self.assertEqual(old.posterior(),new.posterior())


if __name__=='__main__':unittest.main()
