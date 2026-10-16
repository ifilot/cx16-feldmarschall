import unittest
from scout_pursuit_preflight import certificate,own_can_capture,quiet_scout

class ScoutPursuitFixtures(unittest.TestCase):
 def fixture(self):
  from feldmarschall import LAKES
  cells=[254 if s in LAKES else 255 for s in range(100)];cells[74]=1;cells[44]=16|32|8;cells[99]=11
  return cells,{0:(None,None,0),1:(None,None,0)}
 def test_open_escape_is_bounded_certificate(self):
  cells,shuttle=self.fixture();proof=certificate(cells,0,74,44,shuttle)
  self.assertTrue(proof['certified']);self.assertEqual(proof['original_distance'],3)
  self.assertEqual(set(proof['witness']),{'64'})
 def test_all_escape_endpoints_have_friendly_interceptors(self):
  cells,shuttle=self.fixture()
  for sq in(0,10,20):cells[sq]=8
  self.assertFalse(certificate(cells,0,74,44,shuttle)['certified'])
 def test_scout_blockers_and_public_shuttle(self):
  cells,shuttle=self.fixture();cells[24]=10
  self.assertNotIn(14,list(quiet_scout(cells,44,shuttle,0)))
  shuttle[1]=(24,44,5)
  self.assertNotIn(24,list(quiet_scout(cells,44,shuttle,0)))
  shuttle[0]=(64,74,5)
  self.assertEqual(certificate(cells,0,74,44,shuttle)['reason'],'no-progress-move')
 def test_hidden_enemy_nibbles_have_no_authority(self):
  cells,shuttle=self.fixture();expected=None
  for nibble in range(12):
   cells[89]=16|nibble;proof=certificate(cells,0,74,44,shuttle)
   if expected is None:expected=proof
   else:self.assertEqual(proof,expected)
 def test_rotation_both_sides(self):
  cells,shuttle=self.fixture();rotated=[(c^16)if c<254 else c for c in cells[::-1]]
  first=certificate(cells,0,74,44,shuttle);second=certificate(rotated,1,25,55,shuttle)
  self.assertEqual(first['certified'],second['certified']);self.assertEqual(first['progress_steps'],second['progress_steps'])
if __name__=='__main__':unittest.main()
