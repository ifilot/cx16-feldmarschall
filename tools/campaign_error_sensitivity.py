"""Read-only finite-cohort score bounds for unscored engine-error games.

Official standings still exclude errors. These bounds assign each unknown error
score any value in [0,1], with no claim about its probability or a confidence
interval. Every planned side-swapped pair remains in the comparison denominator.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from feldmarschall import valid_setup
from tournament_store import Tournament, mirror_setup


def _score(game, policy):
    if game['result'] == 'error':
        return None
    if game['result'] == 'draw':
        return .5
    if game['result'] not in ('red', 'blue'):
        raise ValueError('unknown game result')
    return float(game[game['result']] == policy)


def _load(path, policy):
    with Tournament(path) as tournament:
        metadata = tournament.metadata()
        if metadata.get('rules') != 'classic' or metadata.get('status') != 'complete':
            raise ValueError('complete Classic tournament required')
        # Outcome sensitivity needs no move decompression or replay. Legal
        # prefixes and artifacts remain untouched; the runner verifies them.
        rows = [dict(row) for row in tournament.db.execute(
            'SELECT id,pair_id,family,red,blue,seed,red_setup,blue_setup,result FROM games ORDER BY id')]
    planned = metadata.get('planned_games')
    if type(planned) is not int or planned <= 0 or planned % 2 or len(rows) != planned:
        raise ValueError('every planned game, including error prefixes, is required')
    mode = metadata.get('setup_mode', 'referee')
    if mode not in ('referee', 'policy-owned', 'policy-owned-rotated-v1'):
        raise ValueError('unknown setup mode')
    if mode in ('policy-owned','policy-owned-rotated-v1') and metadata.get('setup_owner') != policy:
        raise ValueError('candidate must own the policy-owned setup treatment')
    pairs = defaultdict(dict)
    opponents = set()
    for game in rows:
        if (game['red'] == policy) == (game['blue'] == policy):
            raise ValueError('candidate must appear exactly once in every game')
        side = 'red' if game['red'] == policy else 'blue'
        opponent = game['blue'] if side == 'red' else game['red']
        opponents.add(opponent)
        if side in pairs[game['pair_id']]:
            raise ValueError('paired round must swap candidate sides exactly once')
        if not valid_setup(game['red_setup']) or not valid_setup(game['blue_setup']):
            raise ValueError('invalid recorded army')
        game['candidate_score'] = _score(game, policy)
        pairs[game['pair_id']][side] = game
    if len(opponents) != 1:
        raise ValueError('one unchanged opponent identity required')
    for pair in pairs.values():
        if set(pair) != {'red', 'blue'}:
            raise ValueError('incomplete planned side-swapped pair')
        a, b = pair['red'], pair['blue']
        if any(a[key] != b[key] for key in ('family', 'seed')):
            raise ValueError('pair family or move seed mismatch')
        if mode == 'referee':
            matching = a['red_setup'] == b['red_setup'] and a['blue_setup'] == b['blue_setup']
        elif mode == 'policy-owned':
            matching = a['red_setup'] == b['blue_setup'] and a['blue_setup'] == b['red_setup']
        else:
            matching = a['red_setup'] == mirror_setup(b['blue_setup']) and a['blue_setup'] == mirror_setup(b['red_setup'])
        if not matching:
            raise ValueError('paired armies violate declared setup mode')
    return dict(path=str(path), sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                policy=policy, opponent=next(iter(opponents)), setup_mode=mode, pairs=dict(pairs))


def _arm_summary(games):
    known = [game['candidate_score'] for game in games if game['candidate_score'] is not None]
    errors = len(games)-len(known)
    return dict(attempted_games=len(games), error_games=errors, scored_games=len(known),
                wins=known.count(1.), draws=known.count(.5), losses=known.count(0.),
                official_scored_score=sum(known)/len(known) if known else None,
                all_attempt_score_bounds=[sum(known)/len(games), (sum(known)+errors)/len(games)])


def _bound(pair_a, pair_b):
    a = [game['candidate_score'] for game in pair_a.values()]
    b = [game['candidate_score'] for game in pair_b.values()]
    lo = sum(0 if value is None else value for value in a)/2 - sum(1 if value is None else value for value in b)/2
    hi = sum(1 if value is None else value for value in a)/2 - sum(0 if value is None else value for value in b)/2
    return lo, hi


def compare(path_a, policy_a, path_b, policy_b):
    """Return matched A-minus-B finite-cohort bounds without modifying files."""
    a, b = _load(path_a, policy_a), _load(path_b, policy_b)
    if a['opponent'] != b['opponent'] or a['setup_mode'] != b['setup_mode']:
        raise ValueError('opponent identity and explicit setup mode must match')
    if set(a['pairs']) != set(b['pairs']):
        raise ValueError('all planned pairs must match across arms; no intersection filtering')
    records = []
    for identity, pair_a in sorted(a['pairs'].items()):
        pair_b = b['pairs'][identity]
        for side in ('red', 'blue'):
            x, y = pair_a[side], pair_b[side]
            if any(x[key] != y[key] for key in ('family', 'seed')):
                raise ValueError('unmatched pair family or move seed across arms')
            opponent_side = 'blue' if side == 'red' else 'red'
            if x[opponent_side+'_setup'] != y[opponent_side+'_setup']:
                raise ValueError('unmatched opponent army across arms')
            if a['setup_mode'] == 'referee' and x[side+'_setup'] != y[side+'_setup']:
                raise ValueError('unmatched candidate army outside policy-owned mode')
        scores_a = [pair_a[side]['candidate_score'] for side in ('red', 'blue')]
        scores_b = [pair_b[side]['candidate_score'] for side in ('red', 'blue')]
        error_a, error_b = scores_a.count(None), scores_b.count(None)
        records.append(dict(pair_id=identity, family=pair_a['red']['family'], move_seed=pair_a['red']['seed'],
                            scores_a=scores_a, scores_b=scores_b, errors_a=error_a, errors_b=error_b,
                            effect_bounds=list(_bound(pair_a, pair_b))))

    def summarize(subset):
        ids = {row['pair_id'] for row in subset}
        complete = [row['effect_bounds'][0] for row in subset if row['errors_a']+row['errors_b'] == 0]
        positive = sum(value > 0 for value in complete)
        negative = sum(value < 0 for value in complete)
        non_ties = positive+negative
        sign_p = min(1., 2*sum(math.comb(non_ties, i) for i in range(min(positive, negative)+1))/(2**non_ties)) if non_ties else 1.
        return dict(complete_case_direction_diagnostic=dict(positive_pairs=positive, negative_pairs=negative,
                    zero_pairs=len(complete)-non_ties, non_tied_pairs=non_ties,
                    exact_two_sided_binomial_sign_p=sign_p,
                    interpretation='Sign symmetry diagnostic on complete-case pair directions; ties ignored. Not a test of the mean effect, not adjusted for campaign multiple comparisons or selection.'),
                    planned_pairs=len(subset), error_games_a=sum(row['errors_a'] for row in subset),
                    error_games_b=sum(row['errors_b'] for row in subset),
                    pairs_with_any_error=sum(row['errors_a']+row['errors_b'] > 0 for row in subset),
                    arms={label: _arm_summary([game for identity in ids for game in arm['pairs'][identity].values()])
                          for label, arm in (('a', a), ('b', b))},
                    paired_cohort_effect_bounds=[sum(row['effect_bounds'][bound] for row in subset)/len(subset)
                                                 for bound in (0, 1)],
                    complete_case_pairs=len(complete),
                    complete_case_paired_effect=sum(complete)/len(complete) if complete else None)

    return dict(schema='planned-cohort-engine-error-sensitivity-v1',
                interpretation='Finite-cohort A-minus-B bounds, not confidence intervals. Error prefixes remain unscored in official standings; their unknown scores range independently over [0,1] only for this sensitivity calculation.',
                comparison=policy_a+' minus '+policy_b, setup_mode=a['setup_mode'],
                sources={label: {key: arm[key] for key in ('path', 'sha256', 'policy', 'opponent')}
                         for label, arm in (('a', a), ('b', b))},
                summary=summarize(records),
                families={family: summarize([row for row in records if row['family'] == family])
                          for family in sorted({row['family'] for row in records})}, pairs=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fmtour_a', type=Path); parser.add_argument('policy_a')
    parser.add_argument('fmtour_b', type=Path); parser.add_argument('policy_b')
    args = parser.parse_args()
    print(json.dumps(compare(args.fmtour_a, args.policy_a, args.fmtour_b, args.policy_b), indent=2))


if __name__ == '__main__':
    main()
