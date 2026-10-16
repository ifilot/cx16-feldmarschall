"""Public single-corner-post arrival deadline feasibility, not global safety."""
from collections import Counter,deque
import hashlib
import json
from pathlib import Path
from preflight import clone,neighbors,battle,miner_distance,known_safe_quiet
from qualify import decode
OUT=Path(__file__).resolve().parent


def guard_arrival(p,army,post,max_rank=7):
    cell=p.cells[post]
    if cell and(cell[0]!=army or cell[1]>max_rank):return None
    enemy_moves=[(src,dst)for src,dst in p.moves(1-army)if p.cells[src][3]and p.cells[src][1]<10 and p.cells[src][1]!=7]
    candidates=[];last_from,last_to,count=p.shuttle[army]
    for rank in range(max_rank+1):
        threats={dst for src,dst in enemy_moves if battle(p.cells[src][1],rank)!='defender'}
        if post in threats:continue
        if cell:
            if cell[1]==rank:candidates.append(dict(guard=post,rank=rank,distance=0,path=[post]))
            continue
        distances={post:0};toward={};todo=deque([post])
        while todo:
            sq=todo.popleft()
            for n in neighbors(sq):
                if n in distances or n in threats or p.cells[n]is not None:continue
                distances[n]=distances[sq]+1;toward[n]=sq;todo.append(n)
        for src,c in enumerate(p.cells):
            if not c or c[:2]!=[army,rank]:continue
            first=[n for n in neighbors(src)if n in distances and not(count>=5 and src==last_to and n==last_from)]
            if not first:continue
            dst=min(first,key=lambda n:(distances[n],n));path=[src,dst]
            while path[-1]!=post:path.append(toward[path[-1]])
            candidates.append(dict(guard=src,rank=rank,distance=len(path)-1,path=path))
    return min(candidates,key=lambda r:(r['distance'],r['guard']))if candidates else None


def readiness(p,army,flag,post):
    known=[s for s,c in enumerate(p.cells)if c and c[0]!=army and c[3]and c[1]==7]
    distances={s:miner_distance(p,army,s,flag)for s in known};finite=[d for d in distances.values()if d is not None]
    guard=guard_arrival(p,army,post)
    return dict(known_Miners=known,enemy_time=min(finite)if finite else None,guard=guard,
                feasible_after_own_quiet=bool(finite and guard and guard['distance']+2<=min(finite)))


def main():
    raw=OUT/'result.json';data=json.loads(raw.read_text());rows=[];counters=Counter()
    for root in data['screened_known_Miner_roots']:
        if root['flag']not in(0,9,90,99)or not root['selected_quiet']:continue
        p=decode(root);army=root['army'];flag=root['flag'];post=flag+(10 if flag<10 else-10)+(1 if flag%10==0 else-1)
        current=readiness(p,army,flag,post)
        if current['enemy_time']is None or current['enemy_time']<=2:continue
        counters['corner_known_Miner_3plus_roots']+=1
        q=clone(p);q.move(*root['selected']);actual=readiness(q,army,flag,post)
        if actual['feasible_after_own_quiet']:continue
        # A one-step guard-progress alternative can reduce its route by atmost1.
        # If no such current guard route exists, this specific mechanism defers;
        # it doesnotinvent blocker relocation or multiple-guard scheduling.
        if current['guard']is None or current['guard']['distance']+1>current['enemy_time']:continue
        candidates=[]
        for move in p.moves(army):
            if p.cells[move[1]]is not None or not known_safe_quiet(p,army,move):continue
            r=clone(p);r.move(*move);state=readiness(r,army,flag,post)
            if state['feasible_after_own_quiet']:candidates.append(dict(move=list(move),state=state))
        if candidates:
            rows.append(dict(game=root['game'],ply=root['ply'],army=army,flag=flag,post=post,
                selected=root['selected'],current=current,after_selected=actual,deadline_preserving_quiet=candidates,
                C10_selected_demoted=root['C10_selected_demoted'],C10_reason=root['C10_reason'],
                eventual_own_Flag_loss=root['eventual_own_Flag_loss'],eventual_captor_known_here=root['eventual_captor_known_here']))
    summary=dict(counters,opportunity_roots=len(rows),games=len({r['game']for r in rows}),
        nonC10_roots=sum(not r['C10_selected_demoted']for r in rows),nonC10_games=len({r['game']for r in rows if not r['C10_selected_demoted']}),
        nonC10_loss_games=len({r['game']for r in rows if not r['C10_selected_demoted']and r['eventual_own_Flag_loss']}),
        single_known_Miner_nonC10_loss_games=len({r['game']for r in rows if not r['C10_selected_demoted']and r['eventual_own_Flag_loss']and len(r['current']['known_Miners'])==1}),
        distances=dict(Counter(r['current']['enemy_time']for r in rows)))
    report=dict(kind='corner-home-interceptor-arrival-deadline-preflight',summary=summary,opportunities=rows,
        formula='After our quiet candidate, if enemy fastest current stationary-piece Miner route needs tau actions to captureFlag, guard needs d quiet moves tocornerpost plus1capture. Enemy moves next, leaving tau-1 own actions; feasibility is d+2<=tau.',
        scope='Snapshot geometric scheduling feasibility, not a proved winning or safe policy. Revealed nonMiner threats are avoided along guardquietroutes; enemyMiners may be met/exchanged as the interception goal. Otherpieces frozen; unknownenemy threats and twoMiner overload remain outsideproof.',
        comparison='C10onlyresponds to2turnFlagroute; this askswhether 2+quietguardmovesmustbeginearlier to retain a response schedule.',
        source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'deadlines.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
