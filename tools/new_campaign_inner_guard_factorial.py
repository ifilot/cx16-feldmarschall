"""Independent read-only 2x2 matched inner-guard interaction analysis.

No trajectory decompression, policy execution, placement selection or tuning.
Four distinct frozen tournament executions are required. Errors remain unscored;
finite-cohort bounds assign their unknown scores arbitrary values in [0,1].
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import sqlite3

from feldmarschall import valid_setup

LABELS=('book_base','book_guard','native_base','native_guard')
COEFFICIENTS={'book_base':-1,'book_guard':1,'native_base':1,'native_guard':-1}


def digest(data):return hashlib.sha256(data).hexdigest()
def reflected(layout):return ''.join(layout[i:i+10][::-1]for i in range(0,40,10))

def load(path,policy,protocol):
    path=Path(path).resolve();before=path.read_bytes();connection=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);connection.row_factory=sqlite3.Row
    try:
        metadata={row['key']:json.loads(row['value'])for row in connection.execute('SELECT key,value FROM metadata')}
        rows=[dict(row)for row in connection.execute('SELECT id,pair_id,family,red,blue,seed,red_setup,blue_setup,result FROM games ORDER BY id')]
    finally:connection.close()
    if path.read_bytes()!=before:raise ValueError('Input tournament changed during SQL read')
    rounds=protocol['rounds']
    required=dict(rules='classic',status='complete',seed=protocol['seed'],rounds=rounds,
                  planned_games=2*rounds,setup_mode='policy-owned-rotated-v1',setup_owner=policy,families=['original-dos'])
    for key,value in required.items():
        if metadata.get(key)!=value:raise ValueError('Unmatched tournament metadata '+key)
    if len(rows)!=2*rounds:raise ValueError('Every planned record, including errors, is required')
    participants=metadata.get('participants',[]);selected=[r for r in participants if r.get('policy',{}).get('id')==policy]
    if len(selected)!=1 or not selected[0]['policy'].get('source_sha256'):raise ValueError('Frozen policy source receipt required')
    pairs=defaultdict(dict);opponents=set()
    for row in rows:
        if(row['red']==policy)==(row['blue']==policy):raise ValueError('Candidate identity must appear exactly once')
        side='red'if row['red']==policy else'blue';opponent=row['blue'if side=='red'else'red'];opponents.add(opponent)
        if side in pairs[row['pair_id']]:raise ValueError('Duplicate paired side')
        if row['family']!='original-dos':raise ValueError('Unexpected setup family')
        if not valid_setup(row['red_setup'])or not valid_setup(row['blue_setup']):raise ValueError('Invalid recorded army')
        if row['result'] not in('red','blue','draw','error'):raise ValueError('Unknown result')
        row['score']=None if row['result']=='error'else .5 if row['result']=='draw'else float(row[row['result']]==policy)
        row['own_setup']=row[side+'_setup'];row['opponent_setup']=row[('blue'if side=='red'else'red')+'_setup']
        pairs[row['pair_id']][side]=row
    if set(pairs)!=set(range(1,rounds+1))or len(opponents)!=1:raise ValueError('Missing planned pair or inconsistent opponent')
    for pair in pairs.values():
        if set(pair)!={'red','blue'}:raise ValueError('Incomplete side-swapped pair')
        red,blue=pair['red'],pair['blue']
        if red['family']!=blue['family']or red['seed']!=blue['seed']:raise ValueError('Within-pair family/seed mismatch')
        if red['own_setup']!=reflected(blue['own_setup'])or red['opponent_setup']!=reflected(blue['opponent_setup']):raise ValueError('Within-pair rotated armies mismatch')
    receipt=selected[0]
    opponent=next(iter(opponents));opponent_receipts=[r for r in participants if r.get('policy',{}).get('id')==opponent]
    if len(opponent_receipts)!=1 or not opponent_receipts[0]['policy'].get('source_sha256'):raise ValueError('Frozen opponent source receipt required')
    opponent_receipt=opponent_receipts[0]
    return dict(path=str(path),sha256=digest(before),policy=policy,source_sha256=receipt['policy']['source_sha256'],
                executable_sha256=receipt.get('executable_sha256'),runtime_sha256=receipt.get('runtime_sha256'),
                metadata=metadata,pairs=dict(pairs),opponent=opponent,opponent_source_sha256=opponent_receipt['policy']['source_sha256'],
                opponent_executable_sha256=opponent_receipt.get('executable_sha256'))


def validate(arms,rounds):
    if set(arms)!=set(LABELS):raise ValueError('Exactly four distinct factorial cells required')
    if len({arm['policy']for arm in arms.values()})!=4:raise ValueError('Four distinct policy executions required; reused controls forbidden')
    if len({arm['path']for arm in arms.values()})!=4 or len({arm['sha256']for arm in arms.values()})!=4:raise ValueError('Four distinct execution files required; reused controls forbidden')
    if len({(arm['opponent'],arm['opponent_source_sha256'],arm['opponent_executable_sha256'])for arm in arms.values()})!=1:raise ValueError('All four arms must face the same frozen opponent')
    if len({arm['metadata'].get('max_plies')for arm in arms.values()})!=1:raise ValueError('Unmatched game move limits')
    keys=set(range(1,rounds+1))
    if any(set(arm['pairs'])!=keys for arm in arms.values()):raise ValueError('All planned four-arm pairs required')
    for pair_id in sorted(keys):
        for side in('red','blue'):
            records={label:arm['pairs'][pair_id][side]for label,arm in arms.items()}
            first=records['book_base']
            for row in records.values():
                if any(row[key]!=first[key]for key in('id','pair_id','family','seed','opponent_setup')):raise ValueError('Unmatched four-arm record/seed/opponent army')
            for placement in('base','guard'):
                if records['book_'+placement]['own_setup']!=records['native_'+placement]['own_setup']:raise ValueError('Own armies differ within placement level')
            if records['book_base']['own_setup']==records['book_guard']['own_setup']:raise ValueError('Placement levels must actually differ')


def bootstrap(values,replicates=20000,seed=3110114):
    if not values:return None
    rng=random.Random(seed);n=len(values);samples=sorted(sum(values[rng.randrange(n)]for _ in range(n))/n for _ in range(replicates))
    return dict(mean=sum(values)/n,interval_95=[samples[math.floor(.025*(replicates-1))],samples[math.ceil(.975*(replicates-1))]],
                replicates=replicates,seed=seed,method='Percentile paired bootstrap of common four-arm complete pair interactions; nearest outward order statistics')


def analyze_arms(arms,rounds,replicates=20000):
    validate(arms,rounds);records=[];complete=[];bounds=[]
    for pair_id in range(1,rounds+1):
        scores={label:[arm['pairs'][pair_id][side]['score']for side in('red','blue')]for label,arm in arms.items()}
        errors={label:sum(v is None for v in row)for label,row in scores.items()};is_complete=not any(errors.values())
        means={label:sum(row)/2 for label,row in scores.items()}if is_complete else None
        interaction=sum(COEFFICIENTS[label]*mean for label,mean in means.items())if means is not None else None
        lo=hi=0.
        for label,row in scores.items():
            sign=COEFFICIENTS[label]
            lo+=sign*sum((0 if sign>0 else 1)if v is None else v for v in row)/2
            hi+=sign*sum((1 if sign>0 else 0)if v is None else v for v in row)/2
        bounds.append((lo,hi))
        if is_complete:complete.append(interaction)
        records.append(dict(pair_id=pair_id,complete_in_all_four=is_complete,error_games=errors,arm_pair_scores=means,
                            interaction=interaction,arbitrary_error_interaction_bounds=[lo,hi]))
    return dict(schema='inner-guard-four-arm-interaction-analysis-v1',planned_pairs=rounds,attempted_games=8*rounds,
        four_actual_distinct_execution_files=True,within_placement_own_armies_identical=True,all_four_opponent_armies_seeds_game_ids_matched=True,
        common_four_arm_complete_pairs=len(complete),pairs_with_any_error=rounds-len(complete),
        error_games_by_arm={label:sum(row['error_games'][label]for row in records)for label in LABELS},
        interaction_definition='(book_guard-book_base)-(native_guard-native_base); each arm score is mean of its Red/Blue games in the same paired scenario',
        common_complete_case_interaction=bootstrap(complete,replicates),
        all_planned_pairs_arbitrary_error_bounds=[sum(lo for lo,hi in bounds)/rounds,sum(hi for lo,hi in bounds)/rounds],
        error_bound_interpretation='Finite-cohort identification bounds assigning each error score independently any value in [0,1]; not a confidence interval or missing-at-random assumption.',
        limits='Exploratory interaction, not confirmation or promotion. Primary within-study contrasts remain separately defined. No difference of mismatched-cohort means is used. Pair observations and outcomes are correlated across all four arms.',records=records)


def analyze(inputs,protocol_path,replicates=20000):
    raw=Path(protocol_path).read_bytes();protocol=json.loads(raw)
    if protocol.get('schema')!='inner-guard-factorial-v1':raise ValueError('Frozen factorial protocol required')
    if set(inputs)!=set(LABELS):raise ValueError('All four cell inputs required')
    paths=[Path(inputs[label][0]).resolve()for label in LABELS]
    if len({(p.stat().st_dev,p.stat().st_ino)for p in paths})!=4:raise ValueError('Four actual distinct execution files required')
    arms={label:load(*inputs[label],protocol)for label in LABELS};result=analyze_arms(arms,protocol['rounds'],replicates)
    result['protocol']=dict(path=str(Path(protocol_path).resolve()),sha256=digest(raw),document=protocol)
    result['sources']={label:{key:arm[key]for key in('path','sha256','policy','source_sha256','executable_sha256','runtime_sha256','opponent','opponent_source_sha256','opponent_executable_sha256')}for label,arm in arms.items()}
    result['helper_sha256']=digest(Path(__file__).read_bytes())
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    for label in LABELS:parser.add_argument('--'+label.replace('_','-'),nargs=2,metavar=('FMTOUR','POLICY'),required=True)
    args=parser.parse_args();inputs={label:getattr(args,label)for label in LABELS};result=analyze(inputs,args.protocol)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('records','sources','protocol')},indent=2))

if __name__=='__main__':main()
