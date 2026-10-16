"""Independent outcome arithmetic from frozen SQLite rows, without runner stats.

Checks complete fixed cohorts, participant/root matching, official standing
denominators, complete swapped-pair mean and arbitrary-error finite bounds.
Does not replace Python/native state replay or frozen source qualification.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3


def load(path,policy,opponent,expected):
    db=sqlite3.connect('file:'+str(path.resolve())+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        metadata={row['key']:json.loads(row['value']) for row in db.execute('SELECT * FROM metadata')}
        rows=[dict(row) for row in db.execute('SELECT id,pair_id,family,red,blue,seed,red_setup,blue_setup,result FROM games ORDER BY id')]
    finally:db.close()
    assert metadata['status']=='complete' and metadata['rules']=='classic'
    assert metadata['planned_games']==expected==len(rows)
    counts=Counter();pairs=defaultdict(list)
    for row in rows:
        side='red' if row['red']==policy else 'blue'
        assert row[side]==policy and row['blue' if side=='red' else 'red']==opponent
        result=row['result']
        if result=='error':value=None;counts['errors']+=1
        elif result=='draw':value=.5;counts['draws']+=1
        elif result==side:value=1.;counts['wins']+=1
        else:assert result in ('red','blue');value=0.;counts['losses']+=1
        row.update(score=value,side=side);pairs[row['pair_id']].append(row)
    for pair in pairs.values():assert len(pair)==2 and {r['side'] for r in pair}=={'red','blue'}
    n=counts['wins']+counts['draws']+counts['losses']
    summary={key:counts[key] for key in ('wins','draws','losses','errors')}
    summary['score']=(counts['wins']+.5*counts['draws'])/n
    return metadata,rows,pairs,summary


def review(directory,allow_own_setup_difference=False):
    plan=json.loads((directory/'plan.json').read_text());result=json.loads((directory/'result.json').read_text())
    expected=2*len(plan['families'])*plan['rounds'];loaded={};standings={}
    for policy in plan['policies']:
        loaded[policy]=load(directory/(policy+'.fmtour'),policy,plan['opponent'],expected)
        actual=loaded[policy][3];claimed=result['standings'][policy]
        for key,value in actual.items():assert abs(value-claimed[key])<1e-12,(policy,key,value,claimed[key])
        standings[policy]=actual
    comparisons={}
    for candidate,baseline in plan['contrasts']:
        cm,cr,cp,cs=loaded[candidate];bm,br,bp,bs=loaded[baseline]
        assert set(cp)==set(bp)
        assert cm.get('setup_mode','referee')==bm.get('setup_mode','referee')
        if allow_own_setup_difference:assert cm.get('setup_mode') in ('policy-owned','policy-owned-rotated-v1')
        low=high=0.;effects=[];directions=Counter()
        different_own_setups=0
        for pair_id in sorted(cp):
            a=sorted(cp[pair_id],key=lambda r:r['side']);b=sorted(bp[pair_id],key=lambda r:r['side'])
            for x,y in zip(a,b):
                for key in ('id','pair_id','family','seed','side'):assert x[key]==y[key],(pair_id,key)
                own_key=x['side']+'_setup';enemy_key=('blue' if x['side']=='red' else 'red')+'_setup'
                assert x[enemy_key]==y[enemy_key],(pair_id,enemy_key)
                if x[own_key]!=y[own_key]:
                    different_own_setups+=1
                    assert allow_own_setup_difference,'Unequal own setups require explicit deployment-treatment review'
                low+=(0 if x['score'] is None else x['score'])-(1 if y['score'] is None else y['score'])
                high+=(1 if x['score'] is None else x['score'])-(0 if y['score'] is None else y['score'])
            if any(r['score'] is None for r in a+b):directions['error_pairs']+=1;continue
            effect=sum(x['score']-y['score'] for x,y in zip(a,b))/2
            effects.append(effect);directions['positive' if effect>0 else 'negative' if effect<0 else 'tied']+=1
        mean=sum(effects)/len(effects);bounds=[low/expected,high/expected]
        name=candidate+' minus '+baseline
        assert abs(result['comparisons'][name]['metrics']['score']['mean']-mean)<1e-12
        saved=result['error_sensitivity'][name]['paired_cohort_effect_bounds']
        assert all(abs(a-b)<1e-12 for a,b in zip(saved,bounds))
        comparisons[name]=dict(complete_pairs=len(effects),planned_pairs=len(cp),paired_mean=mean,
            finite_error_bounds=bounds,directions=dict(directions),
            all_roots_seeds_sides_exactly_matched=different_own_setups==0,
            all_opponent_armies_seeds_sides_exactly_matched=True,
            own_setup_difference_explicitly_allowed=allow_own_setup_difference,
            games_with_different_own_setups=different_own_setups)
    return dict(passed=True,method='Independent direct-SQL outcome arithmetic; no runner analysis helpers',
        standings=standings,comparisons=comparisons,
        hashes={str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [directory/'plan.json',directory/'result.json']+[directory/(s+'.fmtour') for s in plan['policies']]},
        limitation='Checks outcome statistics and pairing, not policy correctness or state replay; those have separate qualification artifacts.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--allow-own-setup-difference',action='store_true')
    args=parser.parse_args();doc=review(args.directory,args.allow_own_setup_difference)
    (args.directory/'independent-review.json').write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps(doc))


if __name__=='__main__':main()
