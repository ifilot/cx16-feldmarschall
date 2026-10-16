import unittest
from collections import Counter
from secrecy_preflight import gate

class GateTests(unittest.TestCase):
 def fixture(self):
  cells=[255]*100;cells[54]=0;cells[45]=1|32;cells[44]=16|32|5;cells[99]=11
  return cells,{(54,44):100,(45,44):100},{0:(None,None,0),1:(None,None,0)}
 def test_exact_safe_same_victim_tie(self):
  cells,scores,shuttle=self.fixture();counts=Counter()
  self.assertTrue(gate(cells,0,[0]*12,shuttle,scores,(54,44),counts));self.assertEqual(counts['all_gate_conditions'],1)
  scores[45,44]-=1
  self.assertFalse(gate(cells,0,[0]*12,shuttle,scores,(54,44),Counter()))
 def test_hidden_recapture_support_and_nibble_invariance(self):
  cells,scores,shuttle=self.fixture();remaining=[1]+[0]*11
  for nibble in range(12):
   cells[34]=16|nibble
   self.assertFalse(gate(cells,0,remaining,shuttle,scores,(54,44),Counter()))
 def test_immediate_own_flag_danger_veto(self):
  cells,scores,shuttle=self.fixture();cells[98]=16|32|8
  self.assertFalse(gate(cells,0,[0]*12,shuttle,scores,(54,44),Counter()))
if __name__=='__main__':unittest.main()
