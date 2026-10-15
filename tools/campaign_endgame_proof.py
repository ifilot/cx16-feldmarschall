"""Bounded strong-win proof prototype for tiny publicly resolved Classic endgames.

No rollout value: return a common winning action only if every legal enemy reply
and every publicly distinct hidden Flag/Bomb outcome has a terminal win proof.
Depth/node exhaustion returns UNKNOWN. This is an offline feasibility prototype.
"""
from feldmarschall import COUNTS, Position

class BudgetExceeded(Exception):
    pass


def clone(position):
    result=Position();result.cells=[list(c) if c else None for c in position.cells]
    result.shuttle=dict(position.shuttle);return result


def worlds_from_public(cells,army,lost,shuttle,max_mobile=2):
    """cells are public tuples [owner,rank,moved,revealed], None for vacant/lake.

    `lost` is enemy public combat losses. Enemy concealed rank fields are ignored.
    Shuttle is the exact public per-army (lastfrom,lastto,count) dictionary.
    """
    if army not in (0,1) or len(cells)!=100 or len(lost)!=12:raise ValueError('bad public input')
    base=Position();base.cells=[list(c) if c else None for c in cells];base.shuttle=dict(shuttle)
    known=[0]*12;unknown=[];own_mobile=0
    for sq,c in enumerate(base.cells):
        if not c:continue
        if c[0]==army:own_mobile+=c[1]<10
        elif c[3]:known[c[1]]+=1
        else:c[1]=12;unknown.append(sq)
    remaining=[count-dead-seen for count,dead,seen in zip(COUNTS,lost,known)]
    if any(n<0 for n in remaining) or sum(remaining[:10]) or own_mobile>max_mobile or sum(known[:10])>max_mobile or len(unknown)>7:
        return []
    if remaining[11] not in (0,1) or remaining[10]+remaining[11]!=len(unknown):return []
    flags=[sq for sq,c in enumerate(base.cells) if c and c[0]!=army and c[3] and c[1]==11]
    if len(flags)+remaining[11]!=1:return []
    worlds=[]
    for flag in unknown if remaining[11] else [None]:
        world=clone(base)
        for sq in unknown:world.cells[sq][1]=11 if sq==flag else 10
        worlds.append(world)
    return worlds


def state_key(position):
    return (tuple(tuple(c) if c else () for c in position.cells),tuple(position.shuttle[s] for s in (0,1)))


def observation(position,army):
    return (tuple((c[0],c[1] if c[0]==army or c[3] else 12,c[2],c[3]) if c else () for c in position.cells),
            tuple(position.shuttle[s] for s in (0,1)))


def terminal(position,turn,army):
    flags={c[0] for c in position.cells if c and c[1]==11}
    if army not in flags:return False
    if 1-army not in flags:return True
    if not position.moves(turn):return turn!=army and bool(position.moves(army))
    return None


def successors(worlds,move,turn,army):
    groups={}
    for world in worlds:
        # Enemy may condition its action on its private Flag location. Only
        # worlds where the observed action is legal remain in that branch.
        if move not in world.moves(turn):continue
        branch=clone(world);src,dst=move;a,d=branch.cells[src],branch.cells[dst]
        if d is None:branch.move(src,dst)
        else:branch.fight(src,dst,a[1],d[1])
        groups.setdefault(observation(branch,army),{})[state_key(branch)]=branch
    return [list(group.values()) for group in groups.values()]


def solve(cells,army,lost,shuttle,max_depth=8,node_cap=20000,remaining_plies=None):
    worlds=worlds_from_public(cells,army,lost,shuttle)
    report=dict(status='ineligible',move=None,nodes=0,worlds=len(worlds),max_depth=max_depth,node_cap=node_cap)
    if not worlds:return report
    if remaining_plies is not None:max_depth=min(max_depth,max(0,remaining_plies))
    memo={}
    def visit(belief,turn,depth):
        report['nodes']+=1
        if report['nodes']>node_cap:raise BudgetExceeded
        outcomes=[terminal(world,turn,army) for world in belief]
        if all(outcome is True for outcome in outcomes):return True
        # Any compatible adverse terminal outcome refutes a guaranteed win.
        if any(outcome is False for outcome in outcomes):return False
        if depth==0:return False # Not proved within horizon, not a loss claim.
        key=(tuple(sorted(state_key(world) for world in belief)),turn,depth)
        if key in memo:return memo[key]
        available=[set(world.moves(turn)) for world in belief]
        actions=set.intersection(*available) if turn==army else set.union(*available)
        # Deterministic ordering only: immediate Flag attacks first when known.
        actions=sorted(actions,key=lambda m:(not any(w.cells[m[1]] and w.cells[m[1]][1]==11 for w in belief),m))
        if turn==army:
            answer=any(all(visit(group,1-turn,depth-1) for group in successors(belief,m,turn,army)) for m in actions)
        else:
            answer=all(visit(group,1-turn,depth-1) for m in actions for group in successors(belief,m,turn,army))
        memo[key]=answer;return answer
    try:
        if all(terminal(w,army,army) is True for w in worlds):report['status']='already-won';return report
        for move in sorted(set.intersection(*(set(w.moves(army)) for w in worlds))):
            if max_depth and all(visit(group,1-army,max_depth-1) for group in successors(worlds,move,army,army)):
                report.update(status='proved-win',move=list(move));return report
        report['status']='unknown'
    except BudgetExceeded:report['status']='budget-exhausted'
    return report
