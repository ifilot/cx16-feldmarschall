"""Verify the frozen DOS comparison and report paired uncertainty.

Run from the repository root: python3 docs/ai-vs-msdos-2026-10-15/analyze.py
"""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from tournament_store import Tournament, replay, verify


def points(game, policy):
    if game['result'] == 'error':
        return None
    return .5 if game['result'] == 'draw' else float(
        game['result'] == ('red' if game['red'] == policy else 'blue'))


def interval(blocks):
    """Stratify by layout family; retain both army assignments per block."""
    groups = defaultdict(list)
    for family, value in blocks:
        groups[family].append(value)
    if not blocks:
        return None
    rng = random.Random(1930002)
    samples = sorted(sum(rng.choice(values) for values in groups.values()
                         for _ in values) / len(blocks) for _ in range(10000))
    return dict(mean=sum(v for _, v in blocks) / len(blocks),
                paired_95_percent_interval=[samples[249], samples[9749]],
                complete_pairs=len(blocks), pairs_by_family={k: len(v) for k, v in groups.items()})


def main():
    plan = json.loads((HERE / 'plan.json').read_text())
    report = dict(plan=plan, policies={}, matched_comparisons={},
                  uncertainty='Percentile bootstrap, 10000 resamples, paired blocks within layout families. Score intervals use only complete scored pairs; matched differences additionally require both policies to have scored both games. Errors may make these subsets selective.')
    paired = {}
    signatures = None
    worker = ROOT / 'build/desktop/feldmarschall-tournament-worker'
    desk = ROOT / 'build/desktop/feldmarschall-desk'
    for policy in plan['policies']:
        path = HERE / (policy + '.fmtour')
        summary = verify(path)
        assert summary['status'] == 'complete'
        assert summary['games'] == 140
        with Tournament(path) as tournament:
            meta = tournament.metadata()
            assert meta['seed'] == plan['seed']
            assert meta['rules'] == 'classic'
            games = [tournament.game(g['id']) for g in tournament.games()]
            current = [(g['id'], g['pair_id'], g['family'], g['seed'],
                        g['red_setup'], g['blue_setup']) for g in games]
            if signatures is None:
                signatures = current
            assert current == signatures, 'Starting armies or seeds differ between matchups'
            pairs = defaultdict(list)
            for game in games:
                pairs[game['pair_id']].append(game)
            paired[policy] = {key: (rows[0]['family'], sum(points(g, policy) for g in rows) / 2)
                              for key, rows in pairs.items()
                              if len(rows) == 2 and all(g['result'] != 'error' for g in rows)}
            # Independent native replay must match every Python board state.
            with tempfile.TemporaryDirectory(prefix='dos-review-') as temporary:
                request = Path(temporary) / 'game.json'
                for game in games:
                    request.write_text(json.dumps(game))
                    native = subprocess.run([str(worker), '--replay', str(request)],
                                            capture_output=True, text=True, check=True, timeout=30)
                    assert json.loads(native.stdout)['states'] == replay(game)[0]
            chosen = next((g for g in games if points(g, policy) == 1), games[0])
            capture_args = [str(desk), '--capture-review', str(path), '--match', str(chosen['id']),
                            '--ply', str(chosen['plies']), '--screenshot', str(HERE / (policy + '.png'))]
            capture = subprocess.run(capture_args, env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                                     capture_output=True, text=True, timeout=30)
            (HERE / (policy + '-review.log')).write_text(capture.stdout + capture.stderr)
            capture.check_returncode()
            report['policies'][policy] = dict(summary=summary,
                complete_pair_score=interval(list(paired[policy].values())),
                tournament_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                participants=meta['participants'], execution_seconds=meta['execution_seconds'],
                verification=dict(artifact_hashes=True, python_replay_games=len(games),
                                  native_replay_all_states_games=len(games), qt6_review_match=chosen['id']))
        print('Verified', policy, summary['standings'][policy], flush=True)
    baseline = plan['policies'][0]
    for policy in plan['policies'][1:]:
        common = sorted(paired[baseline].keys() & paired[policy].keys())
        differences = [(paired[policy][key][0], paired[policy][key][1] - paired[baseline][key][1])
                       for key in common]
        report['matched_comparisons'][policy + '_minus_' + baseline] = interval(differences)
    report['findings'] = []
    for policy in plan['policies'][1:]:
        comparison = report['matched_comparisons'][policy + '_minus_' + baseline]
        score = report['policies'][policy]['summary']['standings'][policy]['score']
        low, high = comparison['paired_95_percent_interval']
        report['findings'].append(dict(policy=policy, score_against_dos=score,
            matched_gain_over_production=comparison['mean'],
            interpretation=('The paired interval is wholly above zero: evidence of improvement over production against this DOS adapter.'
                            if low > 0 else 'The paired interval is wholly below zero: evidence of worse performance than production against this DOS adapter.'
                            if high < 0 else 'The paired interval includes zero: this cohort does not establish an improvement over production against this DOS adapter.'),
            observed_score_above_half=score > .5))
    report['analysis_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (HERE / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['matched_comparisons'], indent=2))


if __name__ == '__main__':
    main()
