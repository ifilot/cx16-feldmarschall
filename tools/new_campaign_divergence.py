"""Read-only matched frozen-game trajectory diagnostic, without new games.

Usage: new_campaign_divergence.py BASELINE.fmtour BASELINE_ID
       CANDIDATE.fmtour CANDIDATE_ID [--output FILE]
This is descriptive post-hoc evidence, not an independent test or replay audit.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path

from tournament_store import Tournament


def score(game,policy):
    if game['result']=='error':return None
    if game['result']=='draw':return .5
    return float(game[game['result']]==policy)


def load(path,policy):
    with Tournament(path) as tournament:
        metadata=tournament.metadata()
        if metadata.get('rules')!='classic' or metadata.get('status')!='complete':
            raise ValueError('A complete Classic tournament is required')
        games=[tournament.game(row['id']) for row in tournament.games()]
    if len(games)!=metadata['planned_games']:
        raise ValueError('All planned attempts, including errors, are required')
    for game in games:
        if (game['red']==policy)==(game['blue']==policy):
            raise ValueError('Candidate identity must appear exactly once per game')
    return metadata,games


def record(a,policy_a,b,policy_b,allow_own_difference=False):
    for key in ('id','pair_id','family','seed'):
        if a[key]!=b[key]:raise ValueError('Unmatched '+key)
    side_a='red' if a['red']==policy_a else 'blue'
    side_b='red' if b['red']==policy_b else 'blue'
    if side_a!=side_b:raise ValueError('Unmatched candidate side')
    enemy='blue' if side_a=='red' else 'red'
    if a[enemy]!=b[enemy] or a[enemy+'_setup']!=b[enemy+'_setup']:
        raise ValueError('Unmatched opponent or opponent army')
    same_own=a[side_a+'_setup']==b[side_b+'_setup']
    if not same_own and not allow_own_difference:
        raise ValueError('Own armies differ; trajectory mechanism comparison requires identical roots')
    common=0
    for x,y in zip(a['moves'],b['moves']):
        if x!=y:break
        common+=1
    same_moves=a['moves']==b['moves']
    first_move=(common+1 if common<min(len(a['moves']),len(b['moves'])) else None)
    actor=('candidate' if ('red' if common%2==0 else 'blue')==side_a else 'opponent') if first_move else None
    errors=(a['result']=='error',b['result']=='error')
    if not any(errors):error_kind=None
    elif same_moves:error_kind='identical move prefixes'
    elif first_move is None:error_kind='one saved trace extends the other error prefix'
    else:error_kind='moves diverge before either saved prefix ends'
    return dict(game_id=a['id'],pair_id=a['pair_id'],family=a['family'],candidate_side=side_a,
        same_initial_state=same_own,trajectory_comparable=same_own,
        complete_in_both=not any(errors),errors={'baseline':errors[0],'candidate':errors[1]},
        same_moves=same_moves,common_prefix_plies=common,
        first_different_move_ply=first_move,first_different_move_actor=actor,
        first_trajectory_difference_ply=None if same_moves else common+1,
        termination_only_difference=(not same_moves and first_move is None),
        outcome_same=score(a,policy_a)==score(b,policy_b),
        ending_same=(a['result'],a['reason'])==(b['result'],b['reason']),
        baseline_plies=len(a['moves']),candidate_plies=len(b['moves']),error_prefix_kind=error_kind,
        baseline_score=score(a,policy_a),candidate_score=score(b,policy_b))


def summarize(records):
    comparable=[r for r in records if r['trajectory_comparable']]
    complete=[r for r in comparable if r['complete_in_both']]
    prefixes=[r for r in comparable if not r['complete_in_both']]
    pairs=defaultdict(list)
    for row in records:pairs[row['pair_id']].append(row)
    directions=Counter();effects=[]
    for rows in pairs.values():
        if len(rows)!=2 or {r['candidate_side'] for r in rows}!={'red','blue'}:
            raise ValueError('Each planned pair must contain both candidate sides')
        if any(not r['complete_in_both'] for r in rows):directions['unscored_error_pair']+=1;continue
        effect=sum(r['candidate_score']-r['baseline_score'] for r in rows)/2
        effects.append(effect)
        directions['positive' if effect>0 else 'negative' if effect<0 else 'tied']+=1
    return dict(attempted_matched_games=len(records),trajectory_comparable_games=len(comparable),
        excluded_different_own_armies=len(records)-len(comparable),
        complete_game_trajectories=dict(games=len(complete),
            identical_moves=sum(r['same_moves'] for r in complete),
            different_moves=sum(not r['same_moves'] for r in complete),
            same_outcome_despite_different_moves=sum(not r['same_moves'] and r['outcome_same'] for r in complete)),
        error_prefixes=dict(games=len(prefixes),kinds=dict(Counter(r['error_prefix_kind'] for r in prefixes)),
            error_in_both=sum(r['errors']['baseline'] and r['errors']['candidate'] for r in prefixes),
            error_only_baseline=sum(r['errors']['baseline'] and not r['errors']['candidate'] for r in prefixes),
            error_only_candidate=sum(r['errors']['candidate'] and not r['errors']['baseline'] for r in prefixes)),
        first_different_move_actors=dict(Counter(r['first_different_move_actor'] for r in comparable if r['first_different_move_ply'])),
        planned_pairs=len(pairs),paired_score_directions={k:directions[k] for k in ('positive','negative','tied','unscored_error_pair')},
        complete_case_paired_effect=sum(effects)/len(effects) if effects else None)


def compare(path_a,policy_a,path_b,policy_b,allow_own_difference=False):
    ma,a=load(path_a,policy_a);mb,b=load(path_b,policy_b)
    for key in ('seed','rounds','families','max_plies','setup_mode'):
        if ma.get(key)!=mb.get(key):raise ValueError('Unmatched metadata '+key)
    if [g['id'] for g in a]!=[g['id'] for g in b]:raise ValueError('Unmatched complete game IDs')
    rows=[record(x,policy_a,y,policy_b,allow_own_difference) for x,y in zip(a,b)]
    return dict(schema='matched-frozen-trajectory-divergence-v1',
        interpretation='Post-hoc descriptive diagnostic. Only the first different move in a game has the same preceding public state. Later differences are dependent consequences, not independent mechanism activations. Identical trajectories or scores do not establish equivalence. Error prefixes are retained and never scored.',
        sources={label:dict(path=str(path),policy=policy,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
                 for label,path,policy in (('baseline',path_a,policy_a),('candidate',path_b,policy_b))},
        summary=summarize(rows),families={f:summarize([r for r in rows if r['family']==f]) for f in ma['families']},games=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path);parser.add_argument('baseline_id')
    parser.add_argument('candidate',type=Path);parser.add_argument('candidate_id')
    parser.add_argument('--allow-own-setup-difference',action='store_true',
                        help='exclude unequal initial armies from trajectory comparisons, retaining score directions')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=compare(args.baseline,args.baseline_id,args.candidate,args.candidate_id,args.allow_own_setup_difference)
    data=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(data)
    else:print(data,end='')


if __name__=='__main__':main()
