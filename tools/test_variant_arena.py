"""Check variant semantics, masked observations, rescues and Classic equivalence."""
import random
import unittest

from feldmarschall import ROOT, Position, random_setup, GLYPHS, square_name
from variant_rules import VariantPosition, RESCUED
from variant_arena import play_variant


class VariantTests(unittest.TestCase):
    def test_classic_matches_independent_python_rules(self):
        rng=random.Random(9271)
        for _ in range(5):
            classic=Position();native=VariantPosition()
            for army in (0,1):
                setup=random_setup(rng);classic.place(army,setup);native.place(army,setup)
            for ply in range(200):
                army=ply%2
                self.assertEqual(set(classic.moves(army)),set(native.moves(army)))
                moves=classic.moves(army)
                if not moves:break
                src,dst=rng.choice(moves);target=classic.cells[dst]
                _,ending=native.apply(src,dst)
                if target is None:classic.move(src,dst)
                else:classic.fight(src,dst,classic.cells[src][1],target[1])
                expected=bytes(254 if sq in (42,43,46,47,52,53,56,57) else 255 if cell is None else
                               cell[1]|(16 if cell[0] else 0)|(64 if cell[2] else 0)|(32 if cell[3] else 0)
                               for sq,cell in enumerate(classic.cells))
                self.assertEqual(native.cells,expected)
                if ending:break

    def test_special_combat_and_movement(self):
        for rules,attacker,defender,result,disclosed in [(1,8,8,'A',True),(4,3,10,'X',True),
                (8,3,10,'X',True),(2,0,7,'A',False),(2,8,1,'D',True)]:
            p=VariantPosition(rules);cells=bytearray(p.cells);cells[50]=attacker;cells[40]=defender|16;p.cells=bytes(cells)
            event,_=p.apply(50,40)
            self.assertEqual(event.split()[4],GLYPHS[defender] if disclosed else '?')
            self.assertEqual(event.split()[5],result)
        for rank,rule in [(10,8),(11,16)]:
            p=VariantPosition(rule);cells=bytearray(p.cells);cells[50]=rank;cells[40]=16;p.cells=bytes(cells)
            self.assertIn((50,60),p.moves(0));self.assertNotIn((50,40),p.moves(0))
        p=VariantPosition(16);cells=bytearray(p.cells);cells[10]=11;p.cells=bytes(cells)
        self.assertEqual(p.apply(10,0)[1],'flag arrival')

    def test_rescue_privacy_identity_and_limits(self):
        p=VariantPosition(32);cells=bytearray(p.cells);cells[10]=4;p.cells=bytes(cells)
        state=bytearray(p.state);state[1]=1;p.state=bytes(state)
        p.apply(10,0);self.assertEqual(p.auto_rescue(0),(0,60,0,False))
        self.assertEqual(p.state[1],0);self.assertEqual(p.state[49],1)
        p.apply(0,1);self.assertIsNone(p.auto_rescue(1));self.assertEqual(p.state[RESCUED+1],1)
        cells=bytearray(p.cells);cells[10]=5;p.cells=bytes(cells)
        state=bytearray(p.state);state[2]=state[26]=1;p.state=bytes(state)
        p.apply(10,0);self.assertEqual(p.auto_rescue(0),(0,61,1,True))
        self.assertEqual(p.state[49],2)
        p.apply(1,2)
        cells=bytearray(p.cells);cells[11]=3;p.cells=bytes(cells)
        state=bytearray(p.state);state[3]=1;p.state=bytes(state)
        p.apply(11,1);self.assertIsNone(p.auto_rescue(1))

    def test_failed_attack_never_triggers_defender_rescue(self):
        p=VariantPosition(32);cells=bytearray(p.cells)
        cells[99]=0|16;cells[89]=4;p.cells=bytes(cells)
        state=bytearray(p.state);state[14]=1;p.state=bytes(state)
        p._sync();self.assertTrue(p.lib.rules_can_rescue(99))
        event,_=p.apply(89,99)
        self.assertTrue(event.endswith(' D'))
        self.assertIsNone(p.arrival);self.assertIsNone(p.auto_rescue(99))
        self.assertEqual(p.state[50],0)

    def test_masked_python_observers_all_rule_combinations(self):
        rng=random.Random(891)
        for rules in range(64):
            truth=VariantPosition(rules);observers=[VariantPosition(rules),VariantPosition(rules)]
            for army in (0,1):
                setup=random_setup(rng);truth.place(army,setup)
                for side,p in enumerate(observers):p.place(army,setup if side==army else '?'*40,known=side==army)
            for ply in range(80):
                army=ply%2;moves=truth.moves(army)
                if not moves:break
                src,dst=rng.choice(moves);event,ending=truth.apply(src,dst)
                for p in observers:p.observe(event)
                if not ending:
                    rescued=truth.auto_rescue(dst)
                    if rescued:
                        trigger,sq,rank,visible=rescued
                        for side,p in enumerate(observers):
                            p.observe(f'reinforce {square_name(trigger)} {square_name(sq)} {GLYPHS[rank] if side==army or visible else "?"} {int(visible)}')
                for side,p in enumerate(observers):self.assertEqual(p.view(side),truth.view(side),(rules,ply,side,event))
                if ending:break

    def test_real_native_and_greedy_views(self):
        rng=random.Random(173)
        setups=tuple(random_setup(rng) for _ in range(2))
        for rules in (0,1,2,4,8,16,32,63):
            game=play_variant((('current','greedy'),(str(ROOT/'build/feldmarschall-engine'),
                'python3 tools/variant_bot.py greedy'),setups,911,100,True,rules,str(ROOT/'build/librules-variant.so')))
            self.assertFalse(game['reason'].startswith('illegal'))
            self.assertTrue(game['observations_audited'])


if __name__=='__main__':unittest.main()
