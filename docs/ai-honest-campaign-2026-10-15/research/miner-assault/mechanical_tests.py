"""Independent Classic mechanics behind escort-plan feasibility; no AI edits."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'tools'))
from feldmarschall import Position,battle


def clone(p):
    q=Position();q.cells=[list(c) if c else None for c in p.cells];q.shuttle=dict(p.shuttle);return q


def fixture():
    p=Position()
    for sq,c in {60:[0,7,True,False],61:[0,1,True,False],85:[0,2,True,False],88:[0,8,True,False],
                 90:[0,11,False,False],50:[1,10,False,True],51:[1,6,True,True],40:[1,11,False,False],0:[1,9,True,True]}.items():p.cells[sq]=c
    return p


def run():
    p=fixture();quiet=[m for m in p.moves(0) if m[0]!=60 and p.cells[m[1]] is None]
    checked=0
    for src,dst in quiet:
        q=clone(p);q.move(src,dst)
        unrelated=next(m for m in q.moves(1) if m[0]==0 and q.cells[m[1]] is None)
        q.move(*unrelated)
        assert (60,50) in q.moves(0);q.fight(60,50,7,10)
        # Merely placing a stronger escort nearby creates no zone of control.
        assert (51,50) in q.moves(1)
        assert battle(q.cells[51][1],q.cells[50][1])=='attacker'
        checked+=1
    q=fixture();assert (61,51) in q.moves(0);q.fight(61,51,1,6)
    q.move(0,1);q.fight(60,50,7,10);q.move(1,2)
    assert (50,40) in q.moves(0);q.fight(50,40,7,11)
    assert not any(c and c[0]==1 and c[1]==11 for c in q.cells)
    return dict(passed=True,quiet_preparations_tested=checked,
                quiet_support_fails_to_remove_adjacent_recapture_in_every_test=True,
                explicit_guard_capture_then_miner_breach_then_flag_capture=True,
                explanation='Capture-the-guard-first is already the rejected AI_MISSION_ESCORT mechanism; quiet recapture threats cannot prevent legal captures.',
                test_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

if __name__=='__main__':print(json.dumps(run(),indent=2))
