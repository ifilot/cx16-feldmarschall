import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from net import candidates,certificate,capture,own_outcomes
from feldmarschall import COUNTS,LAKES
from campaign_mobile_capture import _fork_enemy_lost,_fork_own_moves,_fork_public_key
from campaign_belief_values import worths

def fixture():
 cells=[254 if s in LAKES else 255 for s in range(100)]
 for s,owner,rank in((22,0,1),(0,0,0),(99,0,11),(89,0,10),(98,0,10),(11,1,6),(21,1,10),(9,1,11),(88,1,8)):
  cells[s]=16*owner|32|rank
 remaining=[0]*12;lost=_fork_enemy_lost(cells,0,remaining);state={0:(None,None,0),1:(None,None,0)}
 return cells,lost,remaining,state

class NetTests(unittest.TestCase):
 def test_two_distinct_actor_contributions_and_suicide_success(self):
  c,l,r,s=fixture();moves=_fork_own_moves(c,0,s);rows=candidates(c,0,l,r,moves,(22,23),s)
  net=next(row for row in rows if row['move']==[22,12]and row['victim']==11 and row['ally']==0)
  self.assertEqual(net['continuations'],{'11':[12],'1':[0],'10':[0]})
  budget=[0,20000];native=certificate(c,0,l,r,s,(22,23),budget)
  self.assertFalse(native['certified']);proof=certificate(c,0,l,r,s,(22,12),budget,net)
  self.assertTrue(proof['certified']);self.assertEqual(proof['minimum_net_material'],15)
  self.assertTrue(any(not p['victim_alive']for p in proof['responses']))
  self.assertEqual(len({p['public_key']for p in proof['responses']}),proof['first_public_outcomes'])
 def test_shuttle_capture_and_victim_escape_are_respected(self):
  c,l,r,s=fixture();self.assertTrue(capture(c,0,22,11,s[0])is False)
  c[1]=c[0];c[0]=255
  self.assertTrue(capture(c,0,1,11,s[0]));self.assertFalse(capture(c,0,1,11,(11,1,5)))
  c,l,r,s=fixture();s[1]=(1,11,5)
  rows=candidates(c,0,l,r,_fork_own_moves(c,0,s),(22,23),s)
  row=next(row for row in rows if row['move']==[22,12]and row['ally']==0)
  self.assertNotIn('1',row['continuations']);self.assertIn('10',row['continuations'])
 def test_unknown_capture_requires_one_action_across_all_ranks(self):
  c,l,r,s=fixture();c[12]=16|12;r[8]=r[10]=1;c[13]=16|12;c[88]=255;l=_fork_enemy_lost(c,0,r)
  outcomes=list(own_outcomes(c,0,r,s,(22,12),worths(l)))
  self.assertEqual(len(outcomes),2);self.assertEqual({o['cells'][12]&15 for o in outcomes},{1,10})
  self.assertEqual(sorted(o['balance']for o in outcomes),[-200,10])
  for o in outcomes:self.assertEqual(sum(o['remaining']),1)
 def test_invalid_public_counts_and_cap_fallback(self):
  c,l,r,s=fixture();bad=r[:];bad[11]=1
  self.assertFalse(certificate(c,0,l,bad,s,(22,12),[0,20000])['certified'])
  rows=candidates(c,0,l,r,_fork_own_moves(c,0,s),(22,23),s);row=next(v for v in rows if v['move']==[22,12])
  proof=certificate(c,0,l,r,s,(22,12),[0,0],row)
  self.assertTrue(proof['inconclusive']);self.assertEqual(proof['enemy_nodes'],1)
 def test_counterescape_and_private_nibble_invariance(self):
  c,l,r,s=fixture();c[21]=255;l=_fork_enemy_lost(c,0,r)
  rows=candidates(c,0,l,r,_fork_own_moves(c,0,s),(22,23),s)
  self.assertFalse(any(row['move']==[22,12]and row['victim']==11 for row in rows))
  c,l,r,s=fixture();c[88]=16|64|12;r[8]=1;l=_fork_enemy_lost(c,0,r)
  expected=candidates(c,0,l,r,_fork_own_moves(c,0,s),(22,23),s)
  for nibble in range(12):
   c[88]=(c[88]&240)|nibble
   self.assertEqual(candidates(c,0,l,r,_fork_own_moves(c,0,s),(22,23),s),expected)

if __name__=='__main__':unittest.main()
