import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import COUNTS,LAKES,Position
from campaign_belief_values import worths
from certificate import certify,successors,own_moves,support
from audit import candidates

def fixture():
 cells=[254 if sq in LAKES else 255 for sq in range(100)]
 for sq,owner,rank in((31,0,1),(99,0,11),(89,0,10),(98,0,10),(0,1,11),(20,1,2),(22,1,3),(88,1,8)):cells[sq]=owner*16|32|rank
 lost=COUNTS[:]
 for rank in(11,2,3,8):lost[rank]-=1
 return cells,lost,[0]*12,{0:(None,None,0),1:(None,None,0)}
class CertificateTests(unittest.TestCase):
 def test_fully_public_forced_capture_both_orientations(self):
  cells,lost,remaining,shuttle=fixture()
  for army in(0,1):
   board=cells if army==0 else[c if c>=254 else c^16 for c in reversed(cells)]
   move=(31,21)if army==0 else(68,78);victims=[20,22]if army==0 else[79,77]
   proof=certify(board,army,lost,remaining,shuttle,move,victims)
   self.assertTrue(proof['certified'],proof);self.assertEqual(proof['minimum_net_material'],75)
   self.assertGreater(proof['first_public_outcomes'],1)
 def test_all_known_enemy_action_union_matches_exact_rules(self):
  cells,lost,remaining,shuttle=fixture();p=Position();p.shuttle=shuttle.copy()
  p.cells=[None if c>=254 else[int(bool(c&16)),c&15,bool(c&64),bool(c&32)]for c in cells]
  outcomes=list(successors(cells,0,remaining,shuttle,worths(lost),[0,20000]))
  self.assertEqual({tuple(o['observation']['move'])for o in outcomes},set(p.moves(1)))
 def test_equal_recapture_cannot_claim_positive_material_with_terminal_loss(self):
  cells,lost,remaining,shuttle=fixture();cells[10]=16|32|0;cells[12]=16|32|1;lost[0]-=1;lost[1]-=1
  geometry,eligible=candidates(cells,0,lost,own_moves(cells,0,shuttle),shuttle[1])
  self.assertTrue(any(row['move']==[31,21]for row in eligible))
  proof=certify(cells,0,lost,remaining,shuttle,(31,21),[20,22])
  self.assertFalse(proof['certified']);self.assertEqual(proof['reason'],'no-positive-bounded-conversion')
  self.assertTrue(any(row['terminal_refutation']for row in proof['responses']))
 def test_own_flag_counterwin_refutes_geometric_fork(self):
  cells,lost,remaining,shuttle=fixture();cells[88]=255;cells[89]=16|32|8
  proof=certify(cells,0,lost,remaining,shuttle,(31,21),[20,22])
  self.assertFalse(proof['certified'])
  after=cells[:];after[21]=after[31];after[31]=255
  replies=list(successors(after,0,remaining,shuttle,worths(lost),[0,20000]))
  self.assertTrue(any(o['flag_loss']and o['observation']['move']==[89,99]for o in replies))
 def test_unknown_scout_rays_and_public_quiet_grouping(self):
  cells=[254 if sq in LAKES else 255 for sq in range(100)];cells[50]=9;cells[80]=16|64|12;cells[99]=11;cells[0]=16|32|11
  remaining=[0]*12;remaining[8]=1;shuttle={0:(None,None,0),1:(None,None,0)};expected=None
  for hidden in range(12):
   cells[80]=(cells[80]&240)|hidden
   outcomes=list(successors(cells,0,remaining,shuttle,worths([0]*12),[0,20000]))
   signature=[(o['observation'],o['cells'],o['remaining'])for o in outcomes]
   # Unknown nibbles may persist in grouped cells; normalize before comparison.
   signature=[(obs,[(c&240)|12 if c<254 and c&16 and not c&32 else c for c in board],rem)for obs,board,rem in signature]
   if expected is None:expected=signature
   self.assertEqual(signature,expected)
   short=next(o for o in outcomes if o['observation']['move']==[80,70]);self.assertIsNone(short['observation']['rank']);self.assertFalse(short['cells'][70]&32)
   long=next(o for o in outcomes if o['observation']['move']==[80,60]);self.assertEqual(long['observation']['rank'],8);self.assertEqual(long['remaining'][8],0)
   attack=next(o for o in outcomes if o['observation']['move']==[80,50]);self.assertEqual(attack['balance'],-100)
 def test_prespecified_node_cap_is_inconclusive(self):
  cells,lost,remaining,shuttle=fixture()
  proof=certify(cells,0,lost,remaining,shuttle,(31,21),[20,22],nodecap=1)
  self.assertFalse(proof['certified']);self.assertTrue(proof['inconclusive'])
 def test_hidden_slot_feasibility_prevents_forced_immobile_from_moving(self):
  cells=[254 if s in LAKES else 255 for s in range(100)];cells[80]=16|64|12;cells[0]=16|12
  remaining=[0]*12;remaining[0]=1;remaining[11]=1
  self.assertEqual(support(cells,1,remaining,80),[0]);self.assertEqual(support(cells,1,remaining,0),[])
 def test_enemy_shuttle_matches_exact_rule_in_action_union(self):
  cells,lost,remaining,shuttle=fixture();shuttle[1]=(89,88,5)
  outcomes=list(successors(cells,0,remaining,shuttle,worths(lost),[0,20000]))
  moves={tuple(o['observation']['move'])for o in outcomes}
  self.assertNotIn((88,89),moves);self.assertIn((88,78),moves)
 def test_actual_public_certificate_is_hidden_nibble_invariant(self):
  import json
  data=json.loads((Path(__file__).with_name('certificate-result.json')).read_text())
  row=next(r for r in data['results']if r['game']==35);fixture=row['public_fixture']
  shuttle={int(owner):tuple(value)for owner,value in fixture['shuttle'].items()};expected=None
  for nibble in range(12):
   cells=[(c&240)|nibble if c<254 and bool(c&16)!=bool(row['army'])and not c&32 else c for c in fixture['cells']]
   result=certify(cells,row['army'],fixture['lost'],fixture['remaining'],shuttle,tuple(row['move']),[v['square']for v in row['victims']])
   if expected is None:expected=result
   self.assertEqual(result,expected)
   self.assertTrue(result['certified'])
 def test_common_control_recognizes_unrelated_guaranteed_capture(self):
  from certificate_common import certify_common
  cells,lost,remaining,shuttle=fixture();cells[80]=16|32|10;lost[10]-=1;cells[90]=7;cells[70]=4
  proof=certify_common(cells,0,lost,remaining,shuttle,(70,60))
  self.assertTrue(proof['certified'],proof);self.assertGreaterEqual(proof['minimum_net_material'],20)
 def test_common_control_rejects_same_terminal_counterexample(self):
  from certificate_common import certify_common
  cells,lost,remaining,shuttle=fixture();cells[10]=16|32|0;cells[12]=16|32|1;lost[0]-=1;lost[1]-=1
  proof=certify_common(cells,0,lost,remaining,shuttle,(31,21))
  self.assertFalse(proof['certified'])
if __name__=='__main__':unittest.main()
