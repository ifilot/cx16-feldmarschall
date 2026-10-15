"""Public exact-endgame eligibility audit on explicit historical tournaments.

Truth is used only by referee replay. Eligibility uses own ranks, public enemy
loss counts and publicly disclosed enemy survivors; hidden ranks are never read.
"""
import argparse
from collections import Counter
import hashlib
import json
import time
from pathlib import Path
from feldmarschall import COUNTS, Position, GLYPHS
from tournament_store import Tournament


def eligible_view(position, side, losses, max_mobile=2):
    own = sum(c is not None and c[0] == side and c[1] < 10 for c in position.cells)
    enemy_remaining = sum(COUNTS[:10])-sum(losses[1-side][:10])
    known = sum(c is not None and c[0] != side and c[3] and c[1] < 10 for c in position.cells)
    unknown = [sq for sq, c in enumerate(position.cells) if c and c[0] != side and not c[3]]
    public = [None if c is None else [c[0],c[1] if c[0] == side or c[3] else 12,c[2],c[3]] for c in position.cells]
    return dict(own_mobile=own, enemy_mobile=enemy_remaining, enemy_disclosed_mobile=known,
                hidden_squares=unknown, public=public,
                eligible=enemy_remaining == known and own <= max_mobile and enemy_remaining <= max_mobile and len(unknown) <= 7)


def audit(paths):
    counters = Counter(); rows = []; sources = []
    for path in paths:
        if 'ai-honest-campaign' in str(path):
            raise ValueError('Use old historical evidence only, never active campaign validation')
        sources.append(dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        with Tournament(path) as tour:
            for entry in tour.games():
                if entry['result'] == 'error':continue
                game=tour.game(entry['id']);position=Position();position.place(0,game['red_setup']);position.place(1,game['blue_setup'])
                losses=[[0]*12 for _ in (0,1)]; seen_game=False
                for ply,(src,dst) in enumerate(game['moves']):
                    side=ply%2
                    if 'msdos' not in game[('red','blue')[side]] and '1990' not in game[('red','blue')[side]]:
                        counters['honest_decision_roots']+=1
                        view=eligible_view(position,side,losses)
                        if view['enemy_mobile']==view['enemy_disclosed_mobile']:counters['all_enemy_mobile_disclosed_roots']+=1
                        if view['own_mobile']<=2 and view['enemy_mobile']<=2:counters['at_most_two_mobiles_each_roots']+=1
                        if view['eligible']:
                            counters['eligible_roots']+=1
                            if not seen_game:counters['games_with_eligible_root']+=1;seen_game=True
                            # Store first eligible root per game and at most ten more spaced prefixes.
                            if not any(r['source']==str(path) and r['game']==game['id'] for r in rows) or ply%20==side:
                                rows.append(dict(source=str(path),game=game['id'],ply=ply,side=side,result=game['result'],reason=game['reason'],
                                                 shuttle={str(s):position.shuttle[s] for s in (0,1)},losses=[list(v) for v in losses],**view))
                    a,d=position.cells[src],position.cells[dst]
                    if d is None:position.move(src,dst)
                    else:
                        _,fallen=position.fight(src,dst,a[1],d[1])
                        for cell in fallen:losses[cell[0]][cell[1]]+=1
                counters['games']+=1
    return dict(kind='historical-public-exact-endgame-eligibility',sources=sources,counters=dict(counters),rows=rows,
                criteria='All remaining enemy mobile ranks disclosed by public survivor/loss count equality; at most2 mobile pieces per side; at most7 concealed enemy immobile slots.',
                limits=['Eligibility is public; physical hidden ranks are omitted from all stored views.','Roots may already be won/lost or need more proof depth than an economical solver.','This audit does not use active campaign validation.'],
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

def proof_pilot(path):
    from campaign_endgame_proof import solve
    data=json.loads(path.read_text());rows=[];seen=set()
    for root in data['rows']:
        key=(root['source'],root['game'])
        if key in seen:continue
        seen.add(key)
        for depth in (4,6,8):
            start=time.perf_counter()
            result=solve(root['public'],root['side'],root['losses'][1-root['side']],
                         {int(k):tuple(v) for k,v in root['shuttle'].items()},max_depth=depth,
                         node_cap=5000,remaining_plies=1000-root['ply'])
            result['seconds']=time.perf_counter()-start
            rows.append(dict(source=root['source'],game=root['game'],ply=root['ply'],**result))
    return dict(kind='old-public-exact-endgame-bounded-proof-pilot',strength_evidence=False,
                eligibility_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                prototype_source_sha256=hashlib.sha256(Path(__file__).with_name('campaign_endgame_proof.py').read_bytes()).hexdigest(),rows=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('paths',type=Path,nargs='*');parser.add_argument('--pilot-source',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=proof_pilot(args.pilot_source) if args.pilot_source else audit(args.paths)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
