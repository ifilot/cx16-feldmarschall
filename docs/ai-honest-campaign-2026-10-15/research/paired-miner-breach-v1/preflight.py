"""Public formation incidence only, not a policy or forcing-win proof."""
from collections import Counter,deque
import hashlib
from itertools import combinations,permutations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from campaign_flag_guard import public_position
from campaign_home_reserve import neighbors
from feldmarschall import Position,LAKES
from tournament_store import Tournament
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
POLICY='student-template-flag-bomb-v1-normal'


def route(position,army,source,bomb):
    queue=deque([(source,0,True)]);seen={(source,True)}
    last_from,last_to,count=position.shuttle[army]
    while queue:
        square,distance,initial=queue.popleft()
        if square==bomb:return distance
        for target in neighbors(square):
            state=(target,False)
            if state in seen:continue
            if initial and count>=5 and source==last_to and target==last_from:continue
            if position.cells[target] is not None and target not in(source,bomb):continue
            seen.add(state);queue.append((target,distance+1,False))
    return None


def inspect(position,army):
    position=public_position(position,army)
    miners=[s for s,c in enumerate(position.cells)if c and c[:2]==[army,7]]
    targets=[]
    for square,cell in enumerate(position.cells):
        if not cell or cell[0]==army or not(cell[3]and cell[1]==11 or not cell[3]and not cell[2]):continue
        bombs=[s for s in neighbors(square)if position.cells[s]and position.cells[s][0]!=army and position.cells[s][3]and position.cells[s][1]==10]
        if len(bombs)<2:continue
        paired=[]
        distances={(miner,bomb):route(position,army,miner,bomb)for miner in miners for bomb in bombs}
        for first,second in combinations(miners,2):
            for b1,b2 in permutations(bombs,2):
                d1,d2=distances[first,b1],distances[second,b2]
                if d1 is not None and d2 is not None:paired.append((max(d1,d2),d1+d2,first,b1,second,b2))
        best=min(paired)if paired else None
        targets.append(dict(target=square,target_disclosed_Flag=bool(cell[3]),bombs=bombs,own_Miners=len(miners),best_pair=list(best)if best else None))
    return targets


def main():
    counts=Counter();rows=[];games=0
    with Tournament(SOURCE)as saved:
        for meta in saved.games():
            game=saved.game(meta['id']);army=int(game['blue']==POLICY);position=Position()
            for side in(0,1):position.place(side,game[('red_setup','blue_setup')[side]])
            for ply,(source,target)in enumerate(game['moves']):
                if ply%2==army:
                    counts['own_roots']+=1
                    for row in inspect(position,army):
                        counts['public_two_Bomb_target_roots']+=1
                        counts['disclosed_Flag_targets'if row['target_disclosed_Flag']else'undisclosed_possible_Flag_targets']+=1
                        pair=row['best_pair']
                        if pair:
                            counts['distinct_reachable_Miner_pair_roots']+=1
                            for horizon in(1,2,3):
                                if pair[0]<=horizon:counts[f'paired_distance_atmost{horizon}_roots']+=1
                        if pair and pair[0]<=3:
                            flag=next((s for s,c in enumerate(position.cells)if c and c[:2]==[army,11]),None)
                            screened=flag is not None and all(position.cells[s]and position.cells[s][:2]==[army,10]for s in neighbors(flag))
                            row.update(game=game['id'],ply=ply,army=army,selected=[source,target],own_Flag_screened=screened,
                                target_is_actual_Flag_offline_label=position.cells[row['target']][1]==11)
                            row['public_board_hex']=bytes(254 if s in LAKES else 255 if c is None else c[0]*16|c[1]|(64 if c[2]else 0)|(32 if c[3]else 0)for s,c in enumerate(public_position(position,army).cells)).hex()
                            row['shuttle']=position.shuttle
                            rows.append(row)
                actor,defender=position.cells[source],position.cells[target]
                if defender:position.fight(source,target,actor[1],defender[1])
                else:position.move(source,target)
            games+=1
            if games%100==0:print('games',games,flush=True)
    report=dict(kind='paired-Miner-breach-geometric-public-preflight',games=games,counters=counts,
        near_pair_games=len({r['game']for r in rows}),ready_pair_games=len({r['game']for r in rows if r['best_pair'][0]==1}),
        near_actual_Flag_games_offline=len({r['game']for r in rows if r['target_is_actual_Flag_offline_label']}),
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=rows,
        limits='Readiness is geometric only; known/unknown defensive tactics, forcing replies and safe preparation are not proved. Possible Flag is not hidden truth. Counts include correlated repeated roots and multiple targets.')
    (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='rows'},indent=2))


if __name__=='__main__':main()
