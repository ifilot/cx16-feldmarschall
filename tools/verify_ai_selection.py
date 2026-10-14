"""Verify complete policy experiments against trials, frozen weights and programs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from benchmark_ai_selection import choose_weights, selected_cases
from optimize_ai_deployments import FAMILIES, delta, score


def verify(run):
    provenance = json.loads((run / 'provenance.json').read_text())
    cases = json.loads((run / 'trials.json').read_text())
    policy = json.loads((run / 'policy.json').read_text())
    summary = json.loads((run / 'summary.json').read_text())
    games = [json.loads(line) for line in (run / 'games.jsonl').read_text().splitlines()]
    assert summary['provenance'] == provenance
    assert summary['policy'] == policy
    weights = policy['weights']
    assert set(weights) == set(policy['layouts'])
    assert all(type(value) is int and 0 <= value <= 5 for value in weights.values())
    assert sum(weights.values()) == 10 and sum(value > 0 for value in weights.values()) >= 3
    assert {case['family'] for case in cases} == set(FAMILIES)
    assert len(cases) == 7 * provenance['rounds'] * 5
    assert {case['opponent'] for case in cases} == {'v020', 'planned', 'adaptive', 'easy', 'greedy'}
    validation = provenance['phase'] == 'validation'
    arms = {'mixture', 'fortress', 'random-control'} if validation else {*policy['layouts'], 'random-control'}
    assert len(games) == len(cases) * len(arms) * 2
    assert Counter((g['setup_id'], g['case'], g['candidate_blue']) for g in games) == Counter(
        (arm, case, side) for arm in arms for case in range(len(cases)) for side in (False, True))
    if validation:
        frozen_bytes = (run / 'frozen-policy.json').read_bytes()
        assert hashlib.sha256(frozen_bytes).hexdigest() == provenance['policy_sha256']
        frozen = json.loads(frozen_bytes)
        assert all(policy[key] == value for key, value in frozen.items())
        assert frozen['development_seed'] != provenance['seed']
        actual, selected = selected_cases(cases, frozen, provenance['seed'] + 7919)
        assert policy['validation_selection_counts'] == {
            name: sum(value == name for value in selected.values()) for name in frozen['weights']}
        for control in ('fortress', 'random-control'):
            assert summary['setup_deltas'][control] == delta(games, 'mixture', control)
        assert summary['promotion_passed'] == (
            summary['setup_deltas']['random-control']['paired_bootstrap_95'][0] > 0)
    else:
        names = list(policy['layouts'])
        values = [score([g for g in games if g['setup_id'] == name]) for name in names]
        assert policy['development_scores'] == dict(zip(names, values))
        assert policy['weights'] == dict(zip(names, choose_weights(values)))
    for game in games:
        assert not game['reason'].startswith('illegal')
        arm = game['setup_id']
        expected = (cases[game['case']]['random_control'] if arm == 'random-control' else
                    actual[game['case']] if arm == 'mixture' else policy['layouts'][arm])
        assert game['candidate_setup'] == expected
    for arm in arms:
        selected_games = [game for game in games if game['setup_id'] == arm]
        result = summary['comparisons'][arm + '-vs-league']
        overall = result['overall']
        assert overall['games'] == len(selected_games)
        assert overall['score'] == score(selected_games)
        assert overall['wins'] == sum(g['winner'] == 'current' for g in selected_games)
        assert overall['draws'] == sum(g['winner'] is None for g in selected_games)
        assert result['capped_games'] == sum(g['reason'] == 'ply limit' for g in selected_games)
        for family in FAMILIES:
            group = [g for g in selected_games if g['group'] == family]
            assert result['families'][family] == {
                'games': len(group), 'score': score(group),
                'capped_games': sum(g['reason'] == 'ply limit' for g in group)}
    subprocess.run([sys.executable, str(Path(__file__).with_name('verify_ai_deployments.py')), str(run)], check=True)
    report = {'games': len(games), 'complete_trial_matrix': True,
              'policy_and_actual_selections_verified': True, 'phase': provenance['phase']}
    (run / 'selection-integrity.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    verify(parser.parse_args().run)
