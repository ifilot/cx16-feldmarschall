"""Mechanical owner/180degree mapping; not a second-color history sample."""
import unittest
from component import route,expected
from campaign_belief_values import worths
from feldmarschall import LAKES
class RotationTests(unittest.TestCase):
 def test_owner_flip_and_rotation_preserve_route_and_expectation(self):
  c=[254 if s in LAKES else 255 for s in range(100)];c[71]=1;c[61]=4;c[32]=16|12;c[22]=16|32|3
  mirrored=[255]*100
  for s,cell in enumerate(c):mirrored[99-s]=cell^16 if cell<254 else cell
  d=route(c,0,32,71);e=route(mirrored,1,67,28);self.assertEqual(d,list(reversed(e)))
  remaining=[0]*12;remaining[0]=remaining[8]=1;f=[0]*100;b=[0]*100;p=[0.]*12;p[0]=.2;p[8]=.8
  self.assertEqual(expected(1,32,c,remaining,worths([0]*12),{32:p},f,b,True),expected(1,67,mirrored,remaining,worths([0]*12),{67:p},list(reversed(f)),list(reversed(b)),True))
if __name__=='__main__':unittest.main()
