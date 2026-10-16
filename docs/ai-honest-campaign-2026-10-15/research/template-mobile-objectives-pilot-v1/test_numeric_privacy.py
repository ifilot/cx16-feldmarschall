"""Independent rational expectation oracle and public-nibble controls."""
from fractions import Fraction
import unittest
from component import expected,route
from campaign_belief_values import gain,worths
from campaign_mobile_capture import cdiv
class NumericPrivacyTests(unittest.TestCase):
 def test_full_expectation_matches_rational_world_mixture(self):
  cells=[255]*100;cells[50]=16|12;remaining=[0]*12
  for r in(0,2,8,9):remaining[r]=1
  worth=worths([0]*12)
  for actor in range(10):
   for ranks in((0,2),(2,8),(8,9)):
    for f,b in((0,0),(512,256),(1,3)):
     flag=[0]*100;bomb=[0]*100;flag[50]=f;bomb[50]=b
     p=[Fraction(0)]*12;p[ranks[0]]=Fraction(1,3);p[ranks[1]]=Fraction(2,3)
     mean=sum(p[r]*gain(actor,r,worth)for r in range(10))
     exact=(f*2000+b*gain(actor,10,worth)+(4096-f-b)*mean)/4096
     target=exact.numerator//exact.denominator if exact>=0 else-((-exact.numerator)//exact.denominator)
     self.assertEqual(expected(actor,50,cells,remaining,worth,{50:list(map(float,p))},flag,bomb,True),target)
 def test_hidden_nibbles_and_disclosed_values(self):
  cells=[255]*100;cells[0]=1;cells[50]=16|12;remaining=[0]*12;remaining[2]=remaining[8]=1;p=[0.]*12;p[2]=.25;p[8]=.75;f=[0]*100;b=[0]*100;w=worths([0]*12)
  before=route(cells,0,50,0);value=expected(1,50,cells,remaining,w,{50:p},f,b,True)
  for nibble in range(12):
   cells[50]=16|nibble;self.assertEqual(route(cells,0,50,0),before);self.assertEqual(expected(1,50,cells,remaining,w,{50:p},f,b,True),value)
  cells[50]=16|32|2;self.assertEqual(expected(1,50,cells,remaining,w,{50:p},f,b,True),gain(1,2,w))
if __name__=='__main__':unittest.main()
