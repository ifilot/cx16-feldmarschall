"""C21 screening-only public home-Miner interception reserve preflight.

No policy is implemented. Truth is used only by the actual referee replay and
terminal-label annotation; every opportunity predicate sees a masked board.
"""
from collections import Counter,deque
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import Position,LAKES,setup_squares,battle
from tournament_store import Tournament
from campaign_flag_guard import evaluate as old_guard,public_position
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
POLICY='student-template-flag-bomb-v1-normal'


def neighbors(sq):
    r,c=divmod(sq,10)
    return[n for n in(sq-10 if r else-1,sq+10 if r<9 else-1,sq-1 if c else-1,sq+1 if c<9 else-1)if n>=0 and n not in LAKES]


def clone(p):
    q=Position();q.cells=[None if c is None else c[:]for c in p.cells];q.shuttle=dict(p.shuttle);return q


def screen(p,army):
    flags=[s for s,c in enumerate(p.cells)if c and c[:2]==[army,11]]
    if len(flags)!=1:return None
    flag=flags[0];entries=neighbors(flag)
    if not entries or any(not p.cells[s]or p.cells[s][:2]!=[army,10]for s in entries):return None
    return flag,entries


def reserve(p,army,entries,max_rank=7):
    guards={b:[s for s in neighbors(b)if p.cells[s]and p.cells[s][0]==army and p.cells[s][1]<=max_rank]for b in entries}
    return dict(covered=all(guards.values()),guards={str(b):s for b,s in guards.items()},covered_entries=sum(bool(v)for v in guards.values()))


def miner_distance(p,army,src,flag):
    """Single disclosed Miner route, other pieces frozen; exact initial shuttle."""
    todo=deque([(src,0)]);seen={src};enemy=1-army
    previous_from,previous_to,count=p.shuttle[enemy]
    while todo:
        sq,d=todo.popleft()
        if sq==flag:return d
        for dst in neighbors(sq):
            if dst in seen:continue
            if d==0 and count>=5 and sq==previous_to and dst==previous_from:continue
            c=p.cells[dst]
            if c and dst!=src:
                if c[0]==enemy:continue
                if battle(7,c[1])!='attacker':continue
            seen.add(dst);todo.append((dst,d+1))
    return None


def known_safe_quiet(p,army,move):
    q=clone(p);q.move(*move)
    return not any(dst==move[1]and q.cells[src][3]and q.cells[src][1]<10 and battle(q.cells[src][1],q.cells[dst][1])!='defender'
                   for src,dst in q.moves(1-army))


def public_bytes(p):
    return [254 if s in LAKES else 255 if c is None else c[0]*16|c[1]|(64 if c[2]else 0)|(32 if c[3]else 0)for s,c in enumerate(p.cells)]


def shuttle_bytes(p):
    return bytes(p.shuttle[a][i]if p.shuttle[a][i]is not None else 255 for i in range(3)for a in(0,1))


def inspect(p,army,selected):
    p=public_position(p,army);s=screen(p,army)
    if not s:return None
    flag,entries=s
    known=[sq for sq,c in enumerate(p.cells)if c and c[0]!=army and c[3]and c[1]==7]
    if not known:return None
    distances={sq:miner_distance(p,army,sq,flag)for sq in known}
    finite=[d for d in distances.values()if d is not None]
    before={str(rank):reserve(p,army,entries,rank)for rank in(6,7)}
    record=dict(flag=flag,entries=entries,known_Miners=known,miner_distances=distances,min_distance=min(finite)if finite else None,
                reserve_before=before,selected=list(selected),selected_quiet=p.cells[selected[1]]is None,
                public_board_hex=bytes(public_bytes(p)).hex(),shuttle_hex=shuttle_bytes(p).hex())
    if not record['selected_quiet']:return record
    q=clone(p);q.move(*selected)
    after={str(rank):reserve(q,army,entries,rank)for rank in(6,7)}
    record['reserve_after']=after
    # Only inspect complete coverage departures or one-step restoration. This
    # does not try to tune a horizon; retain distance buckets for review.
    quiet=[move for move in p.moves(army)if p.cells[move[1]]is None]
    repairs={str(rank):[]for rank in(6,7)}
    for move in quiet:
        r=clone(p);r.move(*move)
        for rank in(6,7):
            if reserve(r,army,entries,rank)['covered']:
                repairs[str(rank)].append(dict(move=list(move),known_tactically_safe=known_safe_quiet(p,army,move)))
    record['quiet_full_cover_moves']=repairs
    native_moves={move:0. for move in p.moves(army)}
    adjustment,reason=old_guard(public_bytes(p),army,[0]*12,{},native_moves,shuttle_bytes(p))
    record['C10_selected_demoted']=adjustment.get(tuple(selected),0)<0
    record['C10_reason']=reason['reason']
    return record


def audit():
    counters=Counter();records=[];losses=[];source_games=0
    with Tournament(SOURCE)as saved:
        for meta in saved.games():
            g=saved.game(meta['id']);army=int(g['blue']==POLICY);p=Position();tokens={}
            for owner in(0,1):
                p.place(owner,g[('red_setup','blue_setup')[owner]])
                tokens.update({sq:(owner,o)for o,sq in enumerate(setup_squares(owner))})
            local=[];breaches=[];first_known={};terminal=None
            for ply,move in enumerate(g['moves']):
                src,dst=move;a,d=p.cells[src],p.cells[dst]
                if ply%2==army:
                    counters['own_roots']+=1
                    for sq,c in enumerate(p.cells):
                        if c and c[0]!=army and c[3]and c[1]==7:first_known.setdefault(tokens[sq],ply)
                    row=inspect(p,army,move)
                    if row:
                        counters['screened_known_Miner_roots']+=1
                        row.update(game=g['id'],army=army,ply=ply,result=g['result'],known_Miner_origins=[tokens[sq]for sq in row['known_Miners']])
                        local.append(row)
                actor=tokens[src]
                if d and d[0]==army and d[1]==10 and a[0]!=army and a[1]==7:
                    flag=next(s for s,c in enumerate(p.cells)if c and c[:2]==[army,11])
                    if dst in neighbors(flag):breaches.append(dict(ply=ply,square=dst,actor=actor,already_disclosed=bool(a[3])))
                if d and d[0]==army and d[1]==11:terminal=dict(ply=ply,rank=a[1],actor=actor)
                if d:
                    outcome,_=p.fight(src,dst,a[1],d[1]);tokens.pop(src)
                    if outcome=='attacker':tokens[dst]=actor
                    elif outcome=='both':tokens.pop(dst)
                else:p.move(src,dst);tokens[dst]=tokens.pop(src)
            source_games+=1
            if terminal:
                terminal.update(game=g['id'],army=army,screen_breaches=breaches,
                    captor_first_known_own_root=first_known.get(terminal['actor']),
                    own_turns_since_captor_known=(terminal['ply']-first_known[terminal['actor']])/2 if terminal['actor']in first_known else None)
                losses.append(terminal)
            for row in local:
                row['eventual_own_Flag_loss']=bool(terminal)
                row['eventual_captor_known_here']=bool(terminal and terminal['actor']in row['known_Miner_origins'])
                records.append(row)
    counters['attempted_games']=source_games;counters['own_Flag_losses']=len(losses)
    counters['Flag_losses_to_Miner']=sum(r['rank']==7 for r in losses)
    counters['losses_captor_known_more_than_one_own_turn_before_capture']=sum(r['rank']==7 and r['own_turns_since_captor_known']is not None and r['own_turns_since_captor_known']>1 for r in losses)
    counters['losses_known_captor_before_inner_screen_breach']=sum(any(b['actor']==r['actor']and b['already_disclosed']for b in r['screen_breaches'])for r in losses if r['rank']==7)
    opportunities=[]
    for row in records:
        if not row['selected_quiet']:continue
        for rank in(6,7):
            key=str(rank);before=row['reserve_before'][key]['covered'];after=row['reserve_after'][key]['covered']
            candidates=[r for r in row['quiet_full_cover_moves'][key]if r['known_tactically_safe']]
            if candidates and not after:
                kind='maintain'if before else'restore'
                opportunities.append(dict(game=row['game'],ply=row['ply'],army=row['army'],max_guard_rank=rank,kind=kind,
                    min_Miner_distance=row['min_distance'],selected=row['selected'],known_safe_cover_moves=candidates,
                    C10_selected_demoted=row['C10_selected_demoted'],C10_reason=row['C10_reason'],
                    eventual_own_Flag_loss=row['eventual_own_Flag_loss'],eventual_captor_known_here=row['eventual_captor_known_here']))
    return dict(kind='C21public-home-Miner-reserve-preflight',strength_evidence=False,policy_implemented=False,
        source=str(SOURCE.relative_to(ROOT)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        counters=dict(counters),opportunities=opportunities,Flag_losses=losses,screened_known_Miner_roots=records,
        source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Only completedC21screening. Every opportunity uses own ranks/disclosedenemyMiners/publicoccupancy/shuttle. Terminalcaptorlabels areofflineevent annotations, notstrategyinputs.',
        limitations=['Single breach coverage is not globalFlagsecurity; twoMinerbreaches canoverload a diagonalcornerguard.','Rank7guard trades withMiner; rank0..6survives. Both are separatelyreported.','Other enemy attacks, unknownranks and futureally/enemymoves can invalidate stationarycoverage.','All-entrycoverage maymiss usefulpartialposts; currentknownMinerroute freezes otherpieces and is a geometric diagnostic only.','No scores or policyparameters fitted; equal-scoreC10diagnostic marks existingcategoricalcoverage only.'])


if __name__=='__main__':
    if(OUT/'result.json').exists():raise FileExistsError('Preserve prior preflight')
    result=audit();(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(counters=result['counters'],opportunities=len(result['opportunities'])),indent=2))
