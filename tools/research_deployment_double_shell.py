"""Geometry proposal only: exact Bomb-distance certificates and old public losses."""
from collections import Counter,deque
import hashlib
import heapq
import json
from pathlib import Path
import re

from ai_registry import ROOT
from feldmarschall import GLYPHS,valid_setup
from tournament_store import Tournament,replay

OUT=ROOT/'docs/ai-honest-campaign-2026-10-15/research/deployment-double-shell'

def geometry(setup):
    assert valid_setup(setup)
    flag=setup.index('F');dist=[100]*40;dist[flag]=0;queue=[(0,flag)]
    while queue:
        cost,sq=heapq.heappop(queue)
        if cost!=dist[sq]:continue
        r,c=divmod(sq,10)
        for nxt in (sq-10 if r else -1,sq+10 if r<3 else -1,sq-1 if c else -1,sq+1 if c<9 else -1):
            if nxt<0:continue
            # Reverse path costs charge the square one is LEAVING, matching
            # forward entry cost into Bomb squares; Flag itself costs0.
            new=cost+int(setup[sq]=='B')
            if new<dist[nxt]:dist[nxt]=new;heapq.heappush(queue,(new,nxt))
    exits=[];trapped=[];exit_distances={}
    for start,glyph in enumerate(setup):
        if glyph in 'BF':continue
        todo=deque([(start,0)]);seen={start};found=None
        while todo:
            sq,d=todo.popleft();r,c=divmod(sq,10)
            if not r:found=d;break
            for nxt in (sq-10 if r else -1,sq+10 if r<3 else -1,sq-1 if c else -1,sq+1 if c<9 else -1):
                if nxt>=0 and nxt not in seen and setup[nxt] not in 'BF':seen.add(nxt);todo.append((nxt,d+1))
        if found is None:trapped.append(start)
        else:exits.append(start);exit_distances[str(start)]=found
    entry=[dist[sq]+int(setup[sq]=='B') for sq in range(10)]
    return dict(min_bomb_captures_from_front=min(entry),bomb_captures_by_front_file=entry,
        mobile_pieces_with_permanent_front_access=len(exits),trapped_mobile_squares=trapped,
        mobile_exit_distance_sum=sum(exit_distances.values()),mobile_exit_distances=exit_distances,
        front_bombs=setup[:10].count('B'),front_miners=setup[:10].count('8'),spy_front_distance=exit_distances.get(str(setup.index('S'))))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    text=(ROOT/'src/core/ai_deploy.c').read_text();arrays=re.findall(r'\{([\d,]+)\}',text)
    layouts=[''.join(GLYPHS[int(v)] for v in a.split(',')) for a in arrays if len(a.split(','))==40]
    assert len(layouts)==3
    base=layouts[0];candidate=list(base);swaps=[(10,28),(21,33),(32,37)]
    for a,b in swaps:candidate[a],candidate[b]=candidate[b],candidate[a]
    candidate=''.join(candidate);assert valid_setup(candidate)
    assert [i for i,(a,b) in enumerate(zip(base,candidate)) if a!=b]==sorted(sum(([a,b] for a,b in swaps),[]))
    own_layouts={name:dict(setup=setup,geometry=geometry(setup)) for name,setup in zip(('Fortress','Evolved2','Evolved3'),layouts)}
    own_layouts['DoubleShellFortress']=dict(setup=candidate,geometry=geometry(candidate),swaps=swaps)
    released=list(base);released[28],released[38]=released[38],released[28]
    released=''.join(released)
    own_layouts['MobilityOnlyFortress']=dict(setup=released,geometry=geometry(released),swaps=[(28,38)])
    assert geometry(base)['min_bomb_captures_from_front']==1
    assert geometry(candidate)['min_bomb_captures_from_front']==2
    assert not geometry(candidate)['trapped_mobile_squares']
    records=[];sources=[]
    for path in (ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour',ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour'):
        sources.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        with Tournament(path) as tournament:
            for row in tournament.games():
                if row['result']=='error':continue
                game=tournament.game(row['id']);army=int(game['blue']=='teacher-context-v1-normal');own=game[('red_setup','blue_setup')[army]]
                states,_=replay(game);flag_fell=False;capturer=None;removed_bombs=0;near_bombs=0;spy_disclosure=None
                flag=own.index('F');fr,fc=divmod(flag,10)
                # Own physical square mapping; no concealed enemy rank is used.
                origin_squares={((6+local//10)*10+local%10 if army==0 else (3-local//10)*10+local%10):local for local in range(40)}
                for ply,(src,dst) in enumerate(game['moves']):
                    source,target=states[ply][src],states[ply][dst]
                    battle=target is not None
                    for square,piece in ((src,source),(dst,target)):
                        if battle and piece is not None and piece[0]==army and piece[1]==9 and spy_disclosure is None:spy_disclosure=ply
                    if battle and target[0]==army and target[1]==11:
                        flag_fell=True;capturer=source[1] # rank disclosed by this actual Flag battle
                    next_state=states[ply+1]
                    if battle:
                        for square,piece in ((src,source),(dst,target)):
                            if piece is not None and piece[0]==army and piece[1]==10:
                                # Bombs never move; if no own Bomb survives there it was publicly removed.
                                survivor=next_state[square]
                                if survivor is None or survivor[0]!=army or survivor[1]!=10:
                                    removed_bombs+=1;local=origin_squares[square];r,c=divmod(local,10)
                                    near_bombs+=int(abs(r-fr)+abs(c-fc)<=2)
                records.append(dict(source=str(path.relative_to(ROOT)),game=game['id'],family=game['family'],army=army,
                    flag_fell=flag_fell,flag_capturer_rank=capturer,own_bombs_removed=removed_bombs,
                    own_bombs_removed_within_two_of_flag=near_bombs,own_spy_first_public_battle_ply=spy_disclosure,
                    initial_min_bomb_captures=geometry(own)['min_bomb_captures_from_front']))
    losses=[r for r in records if r['flag_fell']]
    screened=[r for r in records if r['initial_min_bomb_captures']>=1]
    screened_losses=[r for r in screened if r['flag_fell']]
    summary=dict(screened_games=len(screened),screened_flag_losses=len(screened_losses),
        screened_flag_losses_captured_by_public_miner=sum(r['flag_capturer_rank']==7 for r in screened_losses),
        screened_flag_losses_with_only_one_nearby_bomb_removed=sum(r['own_bombs_removed_within_two_of_flag']==1 for r in screened_losses),
        games=len(records),flag_losses=len(losses),flag_capturer_ranks=dict(Counter(str(r['flag_capturer_rank']) for r in losses)),
        flag_losses_by_bombs_removed=dict(Counter(str(r['own_bombs_removed']) for r in losses)),
        flag_losses_by_initial_min_bomb_layer=dict(Counter(str(r['initial_min_bomb_captures']) for r in losses)),
        flag_losses_by_near_flag_bombs_removed=dict(Counter(str(r['own_bombs_removed_within_two_of_flag']) for r in losses)),
        spy_disclosed_in_first20plies=sum(r['own_spy_first_public_battle_ply'] is not None and r['own_spy_first_public_battle_ply']<20 for r in records))
    document=dict(scope='Research proposal and historical development description only. No saved candidate games, campaign cohorts or new outcomes.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        deployment_source_sha256=hashlib.sha256((ROOT/'src/core/ai_deploy.c').read_bytes()).hexdigest(),sources=sources,
        existing_and_candidate_layouts=own_layouts,summary=summary,records=records,
        caveat='Shortest Bomb count treats mobile defenders as cleared; it is a structural certificate, not a win or actual tempo model. Historical family associations are not causal deployment evidence.')
    (OUT/'geometry-and-history.json').write_text(json.dumps(document,indent=2)+'\n')
    print(json.dumps(dict(layouts={k:v['geometry'] for k,v in own_layouts.items()},summary=summary),indent=2))

if __name__=='__main__':main()
