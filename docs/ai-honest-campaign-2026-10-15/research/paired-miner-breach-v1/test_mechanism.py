"""Forcing double-entry breach is real, but incidence must justify a policy."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_flag_guard import clone
from feldmarschall import Position
from preflight import inspect


def fixture(guard=1):
    p=Position()
    for square,army,rank in[(0,1,11),(1,1,10),(10,1,10),(11,1,guard),
                              (88,1,8),(2,0,7),(20,0,7),(99,0,11),(89,0,10),(98,0,10)]:
        p.cells[square]=[army,rank,False,True]
    return p


def play(p,move):
    source,target=move
    if p.cells[target]:p.fight(source,target,p.cells[source][1],p.cells[target][1])
    else:p.move(source,target)


class PairMechanism(unittest.TestCase):
    def test_two_entry_forcing_sequence_against_all_legal_known_replies(self):
        for guard in(1,7):
            p=fixture(guard);play(p,(2,1))
            replies=p.moves(1);self.assertTrue(replies)
            for reply in replies:
                q=clone(p);play(q,reply)
                if q.cells[1]and q.cells[1][0]==0:
                    self.assertIn((1,0),q.moves(0))
                    continue
                self.assertEqual(reply,(11,1));play(q,(20,10))
                for second in q.moves(1):
                    r=clone(q);play(r,second)
                    self.assertIn((10,0),r.moves(0))

    def test_rank_disclosure_and_private_nibbles_do_not_invent_known_bombs(self):
        p=fixture();reference=inspect(p,0)
        self.assertEqual(reference[0]['best_pair'][0],1)
        p.cells[0][3]=False
        for rank in range(12):
            p.cells[0][1]=rank
            rows=inspect(p,0)
            self.assertEqual(rows[0]['best_pair'][0],1)
            self.assertFalse(rows[0]['target_disclosed_Flag'])
        p.cells[1][3]=False
        self.assertEqual(inspect(p,0),[])

    def test_public_shuttle_can_remove_immediate_readiness(self):
        p=fixture();p.shuttle[0]=(1,2,5)
        rows=inspect(p,0)
        self.assertGreater(rows[0]['best_pair'][0],1)


if __name__=='__main__':unittest.main()
