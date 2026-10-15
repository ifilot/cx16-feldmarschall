"""Reference endpoint routes in hypothetical complete armies, never root truth.

These functions evaluate armies sampled from permitted beliefs. They do not
choose simulated moves or alter a simulated player's information. A capable
route ignores friendly mobile coordination but cannot pass an enemy defender
that the same attacking rank fails to defeat and survive.
"""
from collections import deque

from feldmarschall import BOMB, FLAG, MINER, battle


def neighbors(square):
    return [target for target in (square-10, square+10,
            square-1 if square%10 else -1, square+1 if square%10<9 else -1)
            if 0 <= target < 100]


def _validate(cells, army):
    if army not in (0, 1) or len(cells) != 100:
        raise ValueError('complete 100-square hypothetical army required')
    if any(cell not in (254,255) and (cell & 15) >= 12 for cell in cells):
        raise ValueError('route evaluation requires complete sampled ranks')
    flags=[square for square,cell in enumerate(cells)
           if cell<254 and bool(cell&16)!=bool(army) and (cell&15)==FLAG]
    if len(flags)>1:
        raise ValueError('at most one opposing Flag permitted')
    return flags[0] if flags else None


def _flood(cells, flag, blocked):
    distance={flag:0}
    queue=deque([flag])
    while queue:
        square=queue.popleft()
        for target in neighbors(square):
            if target in distance or blocked(target):
                continue
            distance[target]=distance[square]+1
            queue.append(target)
    return distance


def geometric_pursuit(cells, army):
    """Exact reference for the current two-pass native pursuit evaluator."""
    flag=_validate(cells,army)
    if flag is None:return 400
    best=100
    for mining in (False,True):
        def blocked(square):
            cell=cells[square]
            return cell==254 or (cell<254 and (cell&15)>=BOMB and square!=flag and
                    (bool(cell&16)==bool(army) or not mining or (cell&15)!=BOMB))
        distance=_flood(cells,flag,blocked)
        for square,cell in enumerate(cells):
            if cell<254 and bool(cell&16)==bool(army) and (cell&15)<BOMB and (
                    not mining or (cell&15)==MINER):
                best=min(best,distance.get(square,100))
    return -4*best


def capable_pursuit(cells, army):
    flag=_validate(cells,army)
    if flag is None:return 400
    actors={rank:[square for square,cell in enumerate(cells)
                  if cell<254 and bool(cell&16)==bool(army) and (cell&15)==rank]
            for rank in range(BOMB)}
    best=100
    for rank,squares in actors.items():
        if not squares:continue
        def blocked(square):
            cell=cells[square]
            if cell==254:return True
            if cell>=254:return False
            if bool(cell&16)==bool(army):return (cell&15)>=BOMB
            return battle(rank,cell&15)!='attacker'
        distance=_flood(cells,flag,blocked)
        for square in squares:
            best=min(best,distance.get(square,100))
    return -4*best
