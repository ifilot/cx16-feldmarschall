"""Independent mirror-study SQL, bootstrap and selected-arm trace accounting.

Reads terminal source files only; never changes a cycle or starts matches.
No import or reuse of the study's composition helper or bootstrap code.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import zlib

from direct_sql_review import review as review_sql

BASELINE='student-fortress-template-flag-bomb-v1-normal'
MIRROR='student-fortress-mirror-template-v1-normal'
MIXTURE='student-fortress-mirror-mixture-template-v1-normal'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path,policy):
    connection=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    connection.row_factory=sqlite3.Row
    try:
        rows={r['id']:dict(r) for r in connection.execute('SELECT * FROM games ORDER BY id')}
    finally:connection.close()
    for row in rows.values():
        row['raw_moves']=zlib.decompress(row.pop('moves'))
        assert len(row['raw_moves'])==2*row['plies']
        row['own_side']='red' if row['red']==policy else 'blue'
        assert row[row['own_side']]==policy
        row['points']=(None if row['result']=='error' else .5 if row['result']=='draw' else
                       float(row['result']==row['own_side']))
    return rows


def bootstrap(rows):
    groups=defaultdict(list)
    for family,value in rows:groups[family].append(value)
    rng=random.Random(1970001);estimates=[]
    for _ in range(20000):
        total=0.
        for group in groups.values():
            for _ in group:total+=rng.choice(group)
        estimates.append(total/len(rows))
    estimates.sort()
    return dict(mean=sum(v for _,v in rows)/len(rows),interval_95=[estimates[499],estimates[19499]],
                interval_98_3333=[estimates[166],estimates[19833]],complete_pairs=len(rows),
                pairs_by_family={family:len(values) for family,values in groups.items()})


def review(directory):
    directory=Path(directory);base_review=review_sql(directory)
    plan=json.loads((directory/'plan.json').read_text());result=json.loads((directory/'result.json').read_text())
    assert plan['policies']==[BASELINE,MIRROR,MIXTURE]
    games={p:load(directory/(p+'.fmtour'),p) for p in plan['policies']}
    assert all(set(rows)==set(games[BASELINE]) for rows in games.values())
    comparisons={}
    for candidate in (MIRROR,MIXTURE):
        pairs=defaultdict(list)
        for identity,a in games[candidate].items():
            b=games[BASELINE][identity]
            pairs[a['pair_id']].append((a,b))
        blocks=[]
        for pair_id,rows in sorted(pairs.items()):
            assert len(rows)==2
            if any(a['points'] is None or b['points'] is None for a,b in rows):continue
            blocks.append((rows[0][0]['family'],sum(a['points']-b['points'] for a,b in rows)/2))
        current=bootstrap(blocks) if blocks else None
        stored=result['comparisons'][candidate+' minus '+BASELINE]
        if current is None:assert stored is None
        else:
            for key in ('mean','interval_95','interval_98_3333'):
                assert current[key]==stored['metrics']['score'][key],(candidate,key)
            assert current['complete_pairs']==stored['complete_pairs']
            assert current['pairs_by_family']==stored['pairs_by_family']
        comparisons[candidate]=current
    choices={};counts=Counter();mismatches=[];reason_differences=[]
    for identity,mixed in sorted(games[MIXTURE].items()):
        side=mixed['own_side'];opponent_side='blue' if side=='red' else 'red'
        selected=[p for p in (BASELINE,MIRROR)
                  if games[p][identity][side+'_setup']==mixed[side+'_setup']]
        assert len(selected)==1,(identity,'mixture must match exactly one fixed-arm own formation')
        selected=selected[0];fixed=games[selected][identity]
        assert mixed['own_side']==fixed['own_side']
        assert mixed[opponent_side]==fixed[opponent_side]==plan['opponent']
        for key in ('pair_id','family','seed','red_setup','blue_setup'):assert mixed[key]==fixed[key]
        if mixed['pair_id'] in choices:assert choices[mixed['pair_id']]==selected
        choices[mixed['pair_id']]=selected
        different=[key for key in ('raw_moves','plies','result') if mixed[key]!=fixed[key]]
        if different:mismatches.append(dict(game=identity,pair=mixed['pair_id'],selected=selected,fields=different))
        if mixed['reason']!=fixed['reason']:reason_differences.append(dict(game=identity,selected=selected,mixed_reason=mixed['reason'],fixed_reason=fixed['reason']))
        counts['compared_games']+=1;counts['error_prefixes']+=mixed['result']=='error'
        counts['complete_games']+=mixed['result']!='error'
        counts['exact_full_move_streams']+=mixed['raw_moves']==fixed['raw_moves']
        counts['same_result_and_plies']+=(mixed['result'],mixed['plies'])==(fixed['result'],fixed['plies'])
    receipt=dict(passed=not mismatches,cycle=plan['cycle'],scope='Independent terminal SQL accounting, separately implemented paired bootstrap, and mixture-to-actual-selected-fixed-arm complete move/error-prefix comparison. No composition helper reuse, no new matches, no population equivalence or coordinate-bias isolation claim.',
        independent_sql=base_review,independent_paired_bootstraps=comparisons,
        selected_arm_pairs=dict(Counter(choices.values())),trajectory_counts=dict(counts),
        move_result_mismatches=mismatches,raw_reason_differences=reason_differences,
        source_manifest_sha256=sha(directory/'manifest.json'),auditor_sha256=sha(__file__))
    assert receipt['passed'],'Mixture differs from its actual selected fixed arm'
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=review(args.directory);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('independent_sql','independent_paired_bootstraps')},indent=2))
