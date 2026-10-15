"""Proof correctness fixtures, including hidden-world strategy fusion refusal."""
import unittest
from feldmarschall import COUNTS,TWO_SQUARES,Position
from campaign_endgame_proof import solve,terminal,worlds_from_public

class EndgameProof(unittest.TestCase):
    def fixture(self,unknown=(74,),bombs=0):
        cells=[None]*100;cells[90]=[0,11,False,False];cells[75]=[0,1,True,False]
        cells[0]=[1,8,True,True]
        for sq in unknown:cells[sq]=[1,12,False,False]
        lost=list(COUNTS);lost[8]-=1;lost[11]-=1;lost[10]-=bombs
        return cells,lost,{s:(None,None,0) for s in (0,1)}
    def test_deduced_flag_exact_one_move(self):
        c,l,h=self.fixture();r=solve(c,0,l,h,max_depth=1)
        self.assertEqual((r['status'],r['move']),('proved-win',[75,74]))
    def test_two_worlds_cannot_select_different_root_actions(self):
        c,l,h=self.fixture((74,76),1)
        self.assertEqual(len(worlds_from_public(c,0,l,h)),2)
        self.assertEqual(solve(c,0,l,h,max_depth=1)['status'],'unknown')
    def test_hidden_nibbles_ignored(self):
        c,l,h=self.fixture((74,76),1);ref=solve(c,0,l,h,max_depth=2)
        for rank in range(12):
            c[74][1]=c[76][1]=rank
            self.assertEqual(solve(c,0,l,h,max_depth=2),ref)
    def test_shuttle_bans_otherwise_winning_capture(self):
        c,l,h=self.fixture();h[0]=(74,75,TWO_SQUARES)
        self.assertEqual(solve(c,0,l,h,max_depth=1)['status'],'unknown')
    def test_node_and_remaining_ply_limits_are_unknown(self):
        c,l,h=self.fixture()
        self.assertEqual(solve(c,0,l,h,node_cap=0)['status'],'budget-exhausted')
        self.assertEqual(solve(c,0,l,h,remaining_plies=0)['status'],'unknown')
    def test_unrevealed_mobile_refuses_eligibility(self):
        c,l,h=self.fixture();c[0][3]=False
        self.assertEqual(solve(c,0,l,h)['status'],'ineligible')
    def test_no_moves_and_both_no_moves(self):
        p=Position();p.cells[90]=[0,11,False,False];p.cells[0]=[1,11,False,False]
        self.assertIs(terminal(p,1,0),False) # Neither can move is a draw.
        p.cells[75]=[0,1,True,False]
        self.assertIs(terminal(p,1,0),True)
        self.assertIsNone(terminal(p,0,0))

if __name__=='__main__':unittest.main()
