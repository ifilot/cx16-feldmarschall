"""Structural response fixtures, tactical exceptions and hidden-rank invariance."""
import unittest
from preflight import Position,clone,inspect,reserve,battle
from qualify import safe_reserve


def fixture(rank=6):
    p=Position()
    for sq,army,r in[(0,0,11),(1,0,10),(10,0,10),(11,0,rank),(20,0,6),(4,1,7)]:
        p.cells[sq]=[army,r,False,army==1]
    return p


def play(p,move):
    src,dst=move;a,d=p.cells[src],p.cells[dst]
    if d:p.fight(src,dst,a[1],d[1])
    else:p.move(src,dst)


class ReservePreflight(unittest.TestCase):
    def test_far_known_miner_post_departure_is_distinct_from_C10(self):
        p=fixture();row=inspect(p,0,(11,12))
        self.assertEqual(row['min_distance'],4)
        self.assertTrue(row['reserve_before']['6']['covered'])
        self.assertFalse(row['reserve_after']['6']['covered'])
        self.assertFalse(row['C10_selected_demoted'])
        self.assertTrue(any(c['known_tactically_safe']for c in row['quiet_full_cover_moves']['6']))

    def test_deploy_one_step_to_response_post(self):
        p=fixture();p.cells[12],p.cells[11]=p.cells[11],None
        row=inspect(p,0,(20,30))
        self.assertFalse(row['reserve_before']['6']['covered'])
        self.assertIn([12,11],[c['move']for c in row['quiet_full_cover_moves']['6']])

    def test_equal_rank_trade_is_reported_separately(self):
        p=fixture(7);p.cells[20]=None
        self.assertFalse(reserve(p,0,[1,10],6)['covered'])
        self.assertTrue(reserve(p,0,[1,10],7)['covered'])
        play(p,(4,3));play(p,(3,2));play(p,(2,1))
        self.assertIn((11,1),p.moves(0));play(p,(11,1))
        self.assertIsNone(p.cells[1])

    def test_two_miner_breaches_overload_single_corner_diagonal_guard(self):
        p=fixture();p.cells[4]=None;p.cells[20]=[1,7,False,True];p.cells[2]=[1,7,False,True]
        self.assertTrue(reserve(p,0,[1,10],6)['covered'])
        play(p,(2,1));play(p,(11,1));play(p,(20,10))
        # Guard1 is diagonal from second breach10 and cannot capture in time.
        self.assertFalse(any(dst==10 for _,dst in p.moves(0)))
        for move in p.moves(0):
            q=clone(p);play(q,move)
            self.assertIn((10,0),q.moves(1))

    def test_existing_disclosed_killer_invalidates_holding_post(self):
        p=fixture();p.cells[12]=[1,3,True,True]
        self.assertTrue(reserve(p,0,[1,10],6)['covered'])
        self.assertFalse(safe_reserve(p,0,[1,10],6)['covered'])
        q=clone(p);play(q,(20,30))
        self.assertFalse(safe_reserve(q,0,[1,10],6)['covered'])

    def test_private_nibbles_never_change_inspection(self):
        p=fixture();p.cells[49]=[1,8,True,False];reference=inspect(p,0,(11,12))
        for rank in range(12):
            p.cells[49][1]=rank
            self.assertEqual(inspect(p,0,(11,12)),reference)




class ArrivalDeadlines(unittest.TestCase):
    def setup_position(self,rank=7):
        p=Position()
        for sq,army,r in[(0,0,11),(1,0,10),(10,0,10),(22,0,rank),(55,0,6),(3,1,7),(98,1,8),(99,1,11)]:
            p.cells[sq]=[army,r,False,army==1]
        return p

    def test_two_move_deployment_precedes_old_two_turn_gate(self):
        from deadlines import readiness
        p=self.setup_position();before=readiness(p,0,0,11)
        self.assertEqual(before['enemy_time'],3);self.assertEqual(before['guard']['distance'],2)
        bad=clone(p);play(bad,(22,23));self.assertFalse(readiness(bad,0,0,11)['feasible_after_own_quiet'])
        good=clone(p);play(good,(22,12));self.assertTrue(readiness(good,0,0,11)['feasible_after_own_quiet'])
        self.assertFalse(inspect(p,0,(22,23))['C10_selected_demoted'])

    def test_bad_departure_admits_flag_loss_despite_all_friendly_rescue_replies(self):
        p=self.setup_position();play(p,(22,23));play(p,(3,2));branches=0
        for first in p.moves(0):
            q=clone(p);play(q,first)
            self.assertIn((2,1),q.moves(1));play(q,(2,1))
            for second in q.moves(0):
                r=clone(q);play(r,second)
                self.assertIn((1,0),r.moves(1));branches+=1
        self.assertGreater(branches,1)

    def test_deadline_preserving_move_stops_known_miner_by_win_or_trade(self):
        for rank in(6,7):
            p=self.setup_position(rank);play(p,(22,12));play(p,(3,2));play(p,(12,2))
            self.assertFalse(any(c and c[:2]==[1,7]for c in p.cells))
            self.assertEqual(p.cells[0][:2],[0,11])
            self.assertEqual(p.cells[1][:2],[0,10])
            self.assertEqual(p.cells[2]is None,rank==7)

    def test_absent_miner_route_is_not_a_deadline_failure(self):
        from deadlines import readiness
        p=self.setup_position()
        for sq in(2,4,13):p.cells[sq]=[0,6,False,False]
        state=readiness(p,0,0,11)
        self.assertIsNone(state['enemy_time'])
        self.assertTrue(state['feasible_after_own_quiet'])


if __name__=='__main__':unittest.main()
