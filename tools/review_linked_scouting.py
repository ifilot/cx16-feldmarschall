"""Public-only follow-up opportunity review for the linked-scouting experiment."""
import json

from feldmarschall import COUNTS, VALUES, SCOUT, MINER, BOMB, FLAG, battle, square_name
from ai_registry import ROOT

BASE=ROOT/'docs/ai-linked-scouting-2026-10-15'


def opportunities(case):
    cells=bytes.fromhex(case['input']['board_hex']);army=case['input']['army']
    remaining=[max(0,n-lost) for n,lost in zip(COUNTS,bytes.fromhex(case['input']['enemy_lost_hex']))]
    seen=[0]*12
    for cell in cells:
        if cell<254 and bool(cell&16)!=bool(army) and cell&32:seen[cell&15]+=1
    hidden=[max(0,n-s) for n,s in zip(remaining,seen)]
    worth=VALUES[:]
    if remaining[BOMB]:worth[MINER]=40
    if not remaining[0]:worth[9]=15
    legal=set(map(tuple,case['legal_moves']));rows=[]
    for target,cell in enumerate(cells):
        if cell>=254 or bool(cell&16)==bool(army) or cell&32:continue
        ranks=[rank for rank in range(12) if not(cell&64 and rank>=BOMB)]
        total=sum(hidden[rank] for rank in ranks)
        if not total:continue
        for ally,friend in enumerate(cells):
            if friend>=254 or bool(friend&16)!=bool(army) or friend&15>=BOMB or friend&15==SCOUT or (ally,target) not in legal:continue
            informed=blind=0
            for rank in ranks:
                if battle(SCOUT,rank)!='defender':continue
                outcome=battle(friend&15,rank)
                payoff=2000 if rank==FLAG else worth[rank] if outcome=='attacker' else -worth[friend&15] if outcome=='defender' else worth[rank]-worth[friend&15]
                blind+=hidden[rank]*payoff
                informed+=hidden[rank]*max(0,payoff)
            value=(informed-max(0,blind))//total
            if value<worth[SCOUT]:continue
            rows.append(dict(target=target,beneficiary=ally,value=min(80,value),
                immediate_scouts=[src for src,dst in legal if dst==target and cells[src]&15==SCOUT]))
    return rows


def review():
    source=ROOT/'docs/ai-cycle-2026-10-15/public-cases.jsonl'
    cases=[json.loads(line) for line in source.read_text().splitlines()]
    rows=[]
    for case in cases:
        src,dst=case['chosen_move'];cell=bytes.fromhex(case['input']['board_hex'])[dst]
        rows.append(dict(id=case['id'],source=case['source'],army=case['input']['army'],
            category=case['category'],chosen_move=case['chosen_move'],
            chosen_target_already_disclosed=bool(cell<254 and cell&32),opportunities=opportunities(case)))
    return dict(scope='Public forced-history review; opportunity is a currently legal conditional follow-up, not a guaranteed continuation. Source outcomes never enter the mechanism.',
        source=str(source.relative_to(ROOT)),positions=rows)


if __name__=='__main__':
    result=review()
    with (BASE/'review.json').open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
    for row in result['positions']:
        print(row['id'],row['category'],' '.join(map(square_name,row['chosen_move'])),
              'disclosed',row['chosen_target_already_disclosed'],'opportunities',len(row['opportunities']))
