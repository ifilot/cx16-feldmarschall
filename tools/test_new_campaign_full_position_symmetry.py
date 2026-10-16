import copy,unittest
from new_campaign_full_position_symmetry import mirror,action,reflect,public_position,mirrored_position,referee_tests
from feldmarschall import Position,LAKES
class Reflection(unittest.TestCase):
 def test_involution_and_lakes(self):
  self.assertEqual([mirror(mirror(s))for s in range(100)],list(range(100)))
  self.assertEqual({mirror(s)for s in LAKES},LAKES)
  self.assertEqual(reflect(reflect(list(range(100)))),list(range(100)))
  self.assertEqual(mirror(255),255)
 def test_public_concealment_and_shuttle(self):
  cells=[255]*100;cells[12]=0x40|12;cells[27]=0x10|0;cells[38]=0x20|7
  p=public_position(cells,[27,12,28,13,5,2]);q=mirrored_position(p)
  self.assertEqual(q.cells[mirror(12)],[0,12,True,False]);self.assertEqual(q.shuttle[0],(22,21,5))
  self.assertEqual(mirrored_position(q).cells,p.cells)
 def test_scout_shuttle_legal_and_quiet(self):
  for army in (0,1):
   p=Position();p.cells[40]=[army,8,True,True];p.cells[49]=[1-army,12,False,False];p.shuttle[army]=(30,40,5);q=mirrored_position(p)
   self.assertNotIn((40,30),p.moves(army));self.assertEqual({action(a)for a in p.moves(army)},set(q.moves(army)))
   for a in p.moves(army):
    if p.cells[a[1]]is None:
     x=copy.deepcopy(p);y=copy.deepcopy(q);x.move(*a);y.move(*action(a));self.assertEqual(mirrored_position(x).cells,y.cells)
 def test_all_public_combats(self):self.assertEqual(referee_tests(),240)
if __name__=='__main__':unittest.main()
