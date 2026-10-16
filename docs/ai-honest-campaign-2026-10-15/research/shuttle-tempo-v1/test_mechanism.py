"""An exact one-tempo breach, contrasted with an inactive shuttle ban."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_flag_guard import clone
from feldmarschall import Position
from preflight import inspect
from audit_last_mobile import refutation,wait_certificate


def fixture(count=5):
 p=Position()
 for square,army,rank in[(0,1,11),(10,1,10),(30,1,1),(88,1,8),
                          (21,0,7),(11,0,10),(99,0,11),(89,0,10),(98,0,10)]:
  p.cells[square]=[army,rank,True,True]
 p.shuttle[1]=(20,30,count)
 return p


def play(p,move):
 source,target=move
 if p.cells[target]:p.fight(source,target,p.cells[source][1],p.cells[target][1])
 else:p.move(source,target)


class ShuttleTempoTests(unittest.TestCase):
 def test_last_mobile_pocket_all_legal_replies_die_but_root_can_already_be_forced(self):
  p=Position()
  for sq,side,rank in[(6,0,0),(90,0,11),(80,0,10),(91,0,10),(4,1,10),
                       (7,1,10),(15,1,10),(26,1,0),(97,1,2),(3,1,11)]:
   p.cells[sq]=[side,rank,True,True]
  p.shuttle[0]=(5,6,4)
  q=clone(p);play(q,(6,5));proof=wait_certificate(q,0)
  self.assertIsNotNone(proof)
  self.assertEqual(set(map(tuple,proof['all_friendly_terminal_losing_replies'])),{(5,4),(5,15)})
  self.assertTrue(all(refutation(p,0,m)for m in p.moves(0)))
  p.cells[7]=None
  self.assertIsNone(refutation(p,0,(6,7)))

 def test_immediate_flag_loss_refutes_an_apparent_mobility_escape(self):
  p=Position()
  for sq,side,rank in[(89,1,0),(6,1,11),(98,0,10),(5,0,7),(90,0,11)]:
   p.cells[sq]=[side,rank,True,True]
  p.shuttle[1]=(99,89,4)
  self.assertEqual(refutation(p,1,(89,79))['reason'],'enemy-terminal-Flag-capture')

 def test_unknown_capture_aborts_terminal_pocket_certificate(self):
  p=Position()
  for sq,side,rank in[(5,0,0),(90,0,11),(4,1,12),(15,1,10),(26,1,0)]:
   p.cells[sq]=[side,rank,True,sq!=4]
  p.shuttle[0]=(6,5,5)
  self.assertIsNone(wait_certificate(p,0))

 def test_banned_capture_forces_three_turn_miner_breakthrough_against_all_replies(self):
  p=fixture();self.assertTrue(inspect(p,0)['entries'][0]['strict_aligned_breach'])
  play(p,(21,20));self.assertNotIn((30,20),p.moves(1));first=p.moves(1);self.assertTrue(first)
  for reply in first:
   q=clone(p);play(q,reply)
   self.assertEqual(q.cells[99][:2],[0,11]);self.assertIn((20,10),q.moves(0));play(q,(20,10))
   second=q.moves(1);self.assertTrue(second)
   for response in second:
    r=clone(q);play(r,response)
    self.assertEqual(r.cells[99][:2],[0,11]);self.assertIn((10,0),r.moves(0))

 def test_count4_has_no_ban_and_rotated_count5_preserves_public_motif(self):
  p=fixture(4);self.assertIsNone(inspect(p,0));play(p,(21,20))
  self.assertIn((30,20),p.moves(1));play(p,(30,20));self.assertFalse(any(c and c[:2]==[0,7]for c in p.cells))
  rotated=Position()
  for sq,c in enumerate(fixture().cells):
   if c:rotated.cells[99-sq]=[1-c[0],*c[1:]]
  rotated.shuttle[0]=(79,69,5)
  self.assertTrue(inspect(rotated,1)['entries'][0]['strict_aligned_breach'])

 def test_possible_flag_and_concealed_rank_nibbles_remain_conditional(self):
  p=fixture();p.cells[0][3]=False;reference=inspect(p,0)
  for rank in range(12):
   p.cells[0][1]=rank;self.assertEqual(inspect(p,0),reference)
  p.cells[10][3]=False
  self.assertFalse(any(r['strict_aligned_breach']for r in inspect(p,0)['entries']))


if __name__=='__main__':unittest.main()
