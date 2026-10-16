"""Public deadline mechanics and tactical exceptions, without match tuning."""
import copy
import unittest

from campaign_flag_guard import clone
from campaign_home_reserve import evaluate, guard_arrival, miner_distance, readiness
from feldmarschall import LAKES, Position


def fixture(rank=7):
    position = Position()
    for square, army, piece in [(0,0,11),(1,0,10),(10,0,10),(22,0,rank),
                                (55,0,6),(3,1,7),(98,1,8),(99,1,11)]:
        position.cells[square] = [army,piece,False,army==1]
    return position


def encode(position):
    cells = [254 if square in LAKES else 255 if cell is None else
             cell[0]*16 | cell[1] | (64 if cell[2] else 0) | (32 if cell[3] else 0)
             for square,cell in enumerate(position.cells)]
    shuttle = bytes(position.shuttle[army][index] if position.shuttle[army][index] is not None else 255
                    for index in range(3) for army in (0,1))
    return cells,shuttle


def run(position, scores=None, army=0):
    if scores is None:
        scores = {move: 100 if move==(22,23) else 0 for move in position.moves(army)}
    cells,shuttle = encode(position)
    return evaluate(cells,army,[0]*12,{},scores,shuttle)


def play(position,move):
    source,target = move
    if position.cells[target]:
        position.fight(source,target,position.cells[source][1],position.cells[target][1])
    else:
        position.move(source,target)


class HomeReserveTests(unittest.TestCase):
    def test_timely_deployment_changes_quiet_order_without_changing_preferred_scores(self):
        position=fixture();scores={move:100 if move==(22,23) else 0 for move in position.moves(0)}
        delta,report=run(position,scores)
        self.assertTrue(report['active'])
        self.assertLess(scores[(22,23)]+delta[(22,23)],0)
        for move in [(22,12),(22,21)]:
            self.assertIn(move,report['repair_moves']);self.assertEqual(delta[move],0)
        self.assertEqual(report['current_routes'],{3:3})

    def test_full_bad_line_survives_all_friendly_rescue_replies(self):
        position=fixture();play(position,(22,23));play(position,(3,2));pairs=0
        for first in position.moves(0):
            branch=clone(position);play(branch,first)
            self.assertIn((2,1),branch.moves(1));play(branch,(2,1))
            for second in branch.moves(0):
                leaf=clone(branch);play(leaf,second)
                self.assertIn((1,0),leaf.moves(1));pairs+=1
        self.assertEqual(pairs,49)
        for rank in (6,7):
            branch=fixture(rank);play(branch,(22,12));play(branch,(3,2));play(branch,(12,2))
            self.assertFalse(any(cell and cell[:2]==[1,7] for cell in branch.cells))
            self.assertEqual(branch.cells[2] is None,rank==7)

    def test_capture_scores_and_immediate_wins_are_preserved(self):
        position=fixture();position.cells[54]=[1,8,True,True]
        scores={move:100 if move==(22,23) else 0 for move in position.moves(0)}
        delta,_=run(position,scores);self.assertEqual(delta[(55,54)],0)
        scores[(55,54)]=30000;delta,report=run(position,scores)
        self.assertFalse(any(delta.values()));self.assertEqual(report['reason'],'immediate-win')
        position=fixture();position.cells[54]=[1,11,False,True]
        delta,report=run(position)
        self.assertFalse(any(delta.values()));self.assertEqual(report['reason'],'immediate-win')

    def test_confirmed_unknown_mobile_flag_attack_bails_out(self):
        position=fixture();position.cells[1]=[1,0,True,False]
        delta,report=run(position)
        self.assertFalse(any(delta.values()));self.assertEqual(report['reason'],'confirmed-immediate-flag-danger')

    def test_multiple_routed_miners_and_broken_screen_defer(self):
        position=fixture();position.cells[30]=[1,7,True,True]
        delta,report=run(position);self.assertFalse(any(delta.values()))
        self.assertEqual(report['reason'],'multiple-routed-miners')
        position=fixture();position.cells[1]=None
        delta,report=run(position);self.assertFalse(any(delta.values()))
        self.assertEqual(report['reason'],'no-intact-two-bomb-screen')

    def test_candidate_opening_second_miner_route_cannot_certify_schedule(self):
        position=fixture()
        position.cells[70]=[1,7,True,True]
        for square in (60,71,80):position.cells[square]=[0,6,False,False]
        # The second Miner is fully blocked until our piece leaves60.
        state=readiness(position,0,0,11)
        self.assertEqual(set(state['routes']),{3})
        _,report=run(position)
        self.assertEqual(report['candidates']['60:50']['reason'],'multiple-routed-miners')

    def test_absent_route_after_candidate_is_success_not_failure(self):
        position=fixture();position.cells[22]=None;position.cells[12]=[0,6,False,False]
        for square in (4,13):position.cells[square]=[0,6,False,False]
        delta,report=run(position)
        self.assertIn((12,2),report['repair_moves'])
        self.assertEqual(report['candidates']['12:2']['reason'],'no-invasion-route')
        branch=clone(position);play(branch,(12,2))
        self.assertTrue(readiness(branch,0,0,11)['feasible'])

    def test_public_shuttle_applies_to_actor_guard_and_enemy_routes(self):
        position=fixture();position.cells[21]=[0,10,False,False]
        self.assertTrue(run(position)[1]['active'])
        position.shuttle[0]=(12,22,5)
        self.assertNotIn((22,12),position.moves(0))
        delta,report=run(position)
        self.assertFalse(any(delta.values()));self.assertEqual(report['reason'],'no-safe-quiet-schedule')
        position=fixture();self.assertEqual(miner_distance(position,0,3,0),3)
        position.shuttle[1]=(2,3,5)
        self.assertEqual(miner_distance(position,0,3,0),5)
        delta,_=run(position);self.assertEqual(delta[(22,23)],0)

    def test_disclosed_attackers_reject_actor_and_guard_route(self):
        position=fixture();position.cells[13]=[1,3,True,True]
        changes,report=run(position)
        self.assertFalse(report['candidates']['22:12']['actor_safe'])
        self.assertNotIn((22,12),report['repair_moves'])
        position=fixture();position.cells[11]=position.cells[22];position.cells[22]=None
        position.cells[64]=[1,3,True,True]
        changes,report=run(position)
        self.assertFalse(report['candidates']['55:54']['actor_safe'])
        self.assertTrue(report['candidates']['55:54']['feasible'])
        self.assertEqual(changes[(55,54)],0)  # no independent tactical filter
        position=fixture();position.cells[55]=None;position.cells[23]=[1,3,True,True]
        self.assertIsNone(guard_arrival(position,0,11))  # guard source itself threatened
        position=fixture();position.cells[11]=[0,7,False,False];position.cells[22]=None
        position.cells[12]=[1,3,True,True]
        self.assertIsNone(guard_arrival(position,0,11))
        position=fixture();position.cells[20]=[1,8,True,True]
        position.cells[21]=[0,7,False,False];position.cells[22]=None
        # Vacating21 exposes22 to the Scout; it cannot be promised as a safe path.
        guard=guard_arrival(position,0,11)
        if guard and guard['guard']==21:self.assertNotIn(22,guard['path'])

    def test_no_alternative_preserves_baseline(self):
        position=fixture(rank=8)
        position.cells[55]=None
        delta,report=run(position)
        self.assertFalse(any(delta.values()));self.assertEqual(report['reason'],'no-safe-quiet-schedule')

    def test_rotation_private_nibbles_and_input_immutability(self):
        position=fixture();position.cells[49]=[1,8,True,False]
        cells,shuttle=encode(position);scores={move:100 if move==(22,23) else 0 for move in position.moves(0)}
        original=copy.deepcopy((cells,scores,shuttle));reference=evaluate(cells,0,[],{},scores,shuttle)
        for rank in range(12):
            mutated=cells[:];mutated[49]=(mutated[49]&240)|rank
            self.assertEqual(evaluate(mutated,0,[],{},scores,shuttle),reference)
        self.assertEqual((cells,scores,shuttle),original)
        rotated=Position()
        for square,cell in enumerate(position.cells):
            if cell:rotated.cells[99-square]=[1-cell[0],*cell[1:]]
        transformed={(99-a,99-b):score for (a,b),score in scores.items()}
        delta,_=run(rotated,transformed,1)
        self.assertEqual(delta,{(99-a,99-b):change for (a,b),change in reference[0].items()})

    def test_invalid_legal_move_and_nonfinite_score_rejected(self):
        position=fixture()
        with self.assertRaises(ValueError):run(position,{(22,99):0})
        with self.assertRaises(ValueError):run(position,{(22,23):float('nan')})


if __name__=='__main__':unittest.main()
