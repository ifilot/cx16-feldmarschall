"""Read-only reproduction of the preregistered99% paired bootstrap supplement."""
import json
from pathlib import Path
import random
import sys
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from information_strategy_cycle import score
from tournament_store import Tournament
p=Path(__file__).resolve().parent
plan=json.loads((p/'plan.json').read_text());expected=json.loads((p/'paired-99-intervals.json').read_text())
pairs={}
for policy in plan['policies']:
    groups=defaultdict(list)
    with Tournament(p/(policy+'.fmtour')) as t:
        for game in t.games():groups[game['pair_id']].append(game)
    pairs[policy]={key:sum(score(g,policy) for g in rows)/2 for key,rows in groups.items()
                   if len(rows)==2 and all(g['result']!='error' for g in rows)}
for a,b in plan['contrasts']:
    common=sorted(pairs[a].keys()&pairs[b].keys());rows=[pairs[a][k]-pairs[b][k] for k in common]
    rng=random.Random(1970001)
    draws=sorted(sum(rng.choice(rows) for _ in rows)/len(rows) for _ in range(20000))
    actual=dict(complete_pairs=len(rows),mean=sum(rows)/len(rows),interval_99=[draws[99],draws[19899]])
    assert actual==expected['comparisons'][a+' minus '+b]
print('All five99% paired intervals reproduced exactly.')
