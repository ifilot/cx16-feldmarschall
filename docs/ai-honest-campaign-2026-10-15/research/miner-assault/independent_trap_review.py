"""Independent public-only last-Miner trap check, old game32 root389."""
from collections import Counter,deque
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import Position,COUNTS,LAKES,battle
from tournament_store import Tournament

PATH=ROOT/'docs/ai-fair-information-2026-10-15/validation/dos--teacher-context-v1-normal.fmtour'

def clone(p):
    q=Position();q.cells=[None if c is None else c[:] for c in p.cells];q.shuttle=dict(p.shuttle);return q

def play_public(p,move):
    src,dst=move;a,d=p.cells[src],p.cells[dst]
    if d:
        assert a[1]<12 and d[1]<12,'Cannot resolve hidden-rank hypothetical battle'
        p.fight(src,dst,a[1],d[1])
    else:p.move(src,dst)

def fixture():
    with Tournament(PATH) as saved:g=saved.game(32)
    p=Position();p.place(0,g['red_setup']);p.place(1,g['blue_setup']);lost=[0]*12
    for src,dst in g['moves'][:389]:
        a,d=p.cells[src],p.cells[dst]
        if d:
            _,fallen=p.fight(src,dst,a[1],d[1])
            for c in fallen:
                if c[0]==0:lost[c[1]]+=1
        else:p.move(src,dst)
    for c in p.cells:
        if c and c[0]==0 and not c[3]:c[1]=12
    return p,lost

def gate(p,lost):
    miners=[sq for sq,c in enumerate(p.cells) if c and c[:2]==[1,7]]
    candidates={sq for sq,c in enumerate(p.cells) if c and c[0]==0 and ((c[3] and c[1]==11) or(not c[3] and not c[2]))}
    bombs={sq for sq,c in enumerate(p.cells) if c and c[0]==0 and c[3] and c[1]==10}
    reached={sq for sq,c in enumerate(p.cells) if c and c[0]==1 and c[1]<10 and c[1]!=7};todo=list(reached)
    while todo:
        sq=todo.pop();r,c=divmod(sq,10)
        for nxt in (sq-10 if r else -1,sq+10 if r<9 else -1,sq-1 if c else -1,sq+1 if c<9 else -1):
            if nxt>=0 and nxt not in LAKES and nxt not in bombs and nxt not in reached:reached.add(nxt);todo.append(nxt)
    remaining=[n-v for n,v in zip(COUNTS,lost)]
    for c in p.cells:
        if c and c[0]==0 and c[3]:remaining[c[1]]-=1
    assert min(remaining)>=0
    assert len(miners)==1 and candidates=={96} and not(candidates&reached)
    assert remaining[11]==1 # all concealed immobiles reduce to single Flag candidate
    return dict(last_miner=miners[0],public_flag_candidates=sorted(candidates),known_bombs=sorted(bombs),
                all_nonminer_optimistic_routes_blocked=True,remaining_hidden_rank_counts=remaining)

def trap(p):
    assert (65,66) in p.moves(1);play_public(p,(65,66))
    assert p.cells[68][:2]==[0,4] and p.cells[68][3]
    assert p.cells[75][:2]==[0,0] and p.cells[75][3]
    assert (68,67) in p.moves(0);play_public(p,(68,67))
    replies=[]
    for move in p.moves(1):
        q=clone(p);play_public(q,move)
        # Check terminal wins before proposing enemy recapture.
        assert q.cells[96] is not None and q.cells[96][0]==0
        assert not any(dst==96 for src,dst in [move])
        miners=[sq for sq,c in enumerate(q.cells) if c and c[:2]==[1,7]]
        if not miners:
            replies.append(dict(own_reply=list(move),result='Miner dies attacking disclosed Captain'));continue
        assert len(miners)==1;target=miners[0]
        killer=67 if target==66 else 75
        assert target in (65,66,76)
        capture=(killer,target);assert capture in q.moves(0),'Shuttle or friendly rescue defeats stated response'
        assert q.cells[killer][3] and battle(q.cells[killer][1],7)=='attacker'
        play_public(q,capture);assert not any(c and c[:2]==[1,7] for c in q.cells)
        replies.append(dict(own_reply=list(move),enemy_capture=list(capture),result='last Miner captured'))
    return replies

def retreat(p,lost):
    # Uniform policy: take65->55 now; take55->45 next, capturing any enemy
    # Scout/Spy that arrived there. No decision depends on a concealed nibble.
    assert (65,55) in p.moves(1);q=clone(p);play_public(q,(65,55))
    assert (55,45) in q.moves(1);assert q.cells[45] is None
    remaining=gate(p,lost)['remaining_hidden_rank_counts']
    threats=[]
    for sq,c in enumerate(p.cells):
        if not c or c[0]!=0:continue
        ranks=[c[1]] if c[3] else [r for r,n in enumerate(remaining) if n and (not c[2] or r<10)]
        lethal=[rank for rank in ranks if rank<10 and battle(rank,7)!='defender']
        if not lethal:continue
        assert 8 not in lethal and 9 not in lethal
        distance55=abs(sq//10-5)+abs(sq%10-5)
        distance45=abs(sq//10-4)+abs(sq%10-5)
        assert distance55>1 and distance45>2
        threats.append(dict(square=sq,public_possible_lethal_ranks=lethal,distance_to55=distance55,distance_to45=distance45))
    # Both own Flag neighbors are own Bombs; an enemy Miner needs >=3 turns
    # from root to capture it. Scouts cannot jump these occupied Bombs.
    assert p.cells[0][:2]==[1,11] and p.cells[1][:2]==[1,10] and p.cells[10][:2]==[1,10]
    for sq,c in enumerate(p.cells):
        if c and c[0]==0:
            assert abs(sq//10)+sq%10>2
    return dict(policy=[[65,55],[55,45]],survival_horizon='two enemy turns only',lethal_enemy_distance_certificates=threats,
        caveats=['No long-term Miner escape, Flag capture or winning strategy is established.',
                 'An enemy Scout or Spy may occupy45 in one turn; our Miner safely captures it on planned retreat.',
                 'Future operational mobility beyond45 is not certified.'])

def main():
    p,lost=fixture();root=clone(p);g=gate(p,lost);replies=trap(clone(p));r=retreat(clone(p),lost)
    for rank in range(12):
        q=clone(root)
        for c in q.cells:
            if c and c[0]==0 and not c[3]:c[1]=rank
        assert gate(q,lost)==g and trap(clone(q))==replies and retreat(clone(q),lost)==r
    document=dict(passed=True,review='Independent public-only resource trap review',game=32,zero_based_ply=389,army=1,
        tournament_sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        public_cells=root.cells,shuttle=root.shuttle,enemy_lost=lost,gate=g,root_move=[65,66],enemy_setup_move=[68,67],
        friendly_replies=len(replies),reply_certificates=replies,retreat=r,concealed_rank_invariance_variants=12,
        terminology='Enemy41 is General(rank1), not Colonel. Only revealed rank4Captain68/rank0Marshal75 are needed for trap proof.',
        scope='Old historical diagnostic fixture only. Honest public gate, no registered policy or new games. Not a strength result.')
    destination=Path(__file__).with_name('independent-trap-review.json');destination.write_text(json.dumps(document,indent=2)+'\n')
    print(json.dumps(dict(passed=True,friendly_replies=len(replies),reply_outcomes=dict(Counter(row['result'] for row in replies)),
        gate=g,retreat=r),indent=2))

if __name__=='__main__':main()
