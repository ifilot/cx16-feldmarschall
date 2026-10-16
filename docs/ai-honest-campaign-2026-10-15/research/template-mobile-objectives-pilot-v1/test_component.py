import unittest
from component import route,expected
from campaign_belief_values import worths
from feldmarschall import LAKES
class ComponentTests(unittest.TestCase):
 def test_route_blocks_friends_and_enemy_transit(self):
  c=[254 if s in LAKES else 255 for s in range(100)];c[0]=1;c[1]=16|12;c[10]=10
  d=route(c,0,0,0);self.assertEqual(d[1],1);self.assertEqual(d[2],255)
 def test_exchangeable_mobile_reduces_exactly_to_baseline(self):
  c=[255]*100;c[10]=16|12;r=[0]*12;r[0]=1;r[8]=2;w=worths([0]*12);f=[0]*100;b=[0]*100
  for actor in range(10):self.assertEqual(expected(actor,10,c,r,w,{10:[1/3]+[0]*7+[2/3]+[0]*3},f,b,True),expected(actor,10,c,r,w,{},f,b))
if __name__=='__main__':unittest.main()
