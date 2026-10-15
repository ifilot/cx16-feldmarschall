"""Verify both frozen information cohorts and compute paired comparisons.

Run from the repository root after all six tournaments finish.
"""
from collections import defaultdict
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from tournament_store import Tournament, replay, verify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def points(game, policy):
    if game['result'] == 'error': return None
    if game['result'] == 'draw': return .5
    return float(game['result'] == ('red' if game['red'] == policy else 'blue'))


def interval(blocks):
    if not blocks: return None
    families = defaultdict(list)
    for family, value in blocks: families[family].append(value)
    rng = random.Random(1940002)
    means = sorted(sum(rng.choice(values) for values in families.values() for _ in values)
                   / len(blocks) for _ in range(10000))
    return dict(mean=sum(v for _, v in blocks)/len(blocks),
                paired_95_percent_interval=[means[249], means[9749]], complete_pairs=len(blocks),
                pairs_by_family={k: len(v) for k, v in families.items()})


def analyze_cohort(name, seed, plan):
    report = dict(seed=seed, policies={}, matched_comparisons={})
    paired, signatures = {}, None
    for policy in plan['policies']:
        path = HERE/name/(policy+'.fmtour')
        summary = verify(path)
        assert summary['status'] == 'complete' and summary['games'] == 140
        with Tournament(path) as tournament:
            metadata = tournament.metadata()
            assert metadata['seed'] == seed and metadata['max_plies'] == plan['max_plies']
            games = [tournament.game(g['id']) for g in tournament.games()]
            current = [(g['id'], g['pair_id'], g['family'], g['seed'], g['red_setup'], g['blue_setup']) for g in games]
            if signatures is None: signatures = current
            assert current == signatures, 'Armies or seeds differ across interventions'
            pairs = defaultdict(list)
            for game in games: pairs[game['pair_id']].append(game)
            paired[policy] = {key: (rows[0]['family'], sum(points(g, policy) for g in rows)/2)
                              for key, rows in pairs.items()
                              if len(rows) == 2 and all(g['result'] != 'error' for g in rows)}
            with tempfile.TemporaryDirectory(prefix='information-review-') as temp:
                request = Path(temp)/'game.json'
                for game in games:
                    request.write_text(json.dumps(game))
                    result = subprocess.run([str(ROOT/'build/desktop/feldmarschall-tournament-worker'), '--replay', str(request)],
                                            capture_output=True, text=True, check=True, timeout=30)
                    assert json.loads(result.stdout)['states'] == replay(game)[0]
            chosen = next((g for g in games if points(g, policy) == 1), games[0])
            result = subprocess.run([str(ROOT/'build/desktop/feldmarschall-desk'), '--capture-review', str(path),
                                     '--match', str(chosen['id']), '--ply', str(chosen['plies']),
                                     '--screenshot', str(path.with_suffix('.png'))],
                                    env=dict(os.environ, QT_QPA_PLATFORM='offscreen'), capture_output=True,
                                    text=True, timeout=30)
            path.with_suffix('.review.log').write_text(result.stdout+result.stderr)
            result.check_returncode()
            report['policies'][policy] = dict(summary=summary,
                complete_pair_score=interval(list(paired[policy].values())),
                tournament_sha256=sha(path), participants=metadata['participants'],
                execution_seconds=metadata['execution_seconds'],
                verification=dict(artifact_hashes=True, python_replay_games=len(games),
                                  native_replay_all_states_games=len(games), qt6_review_match=chosen['id']))
        print('Verified', name, policy, summary['standings'][policy], 'errors', summary['errors'], flush=True)
    for control, intervention in itertools.combinations(plan['policies'], 2):
        common = sorted(paired[control].keys() & paired[intervention].keys())
        blocks = [(paired[control][k][0], paired[intervention][k][1]-paired[control][k][1]) for k in common]
        comparison = interval(blocks)
        comparison['control'] = control
        comparison['intervention'] = intervention
        comparison['interpretation'] = (
            'Improvement supported on this cohort.' if comparison['paired_95_percent_interval'][0] > 0 else
            'Decrease supported on this cohort.' if comparison['paired_95_percent_interval'][1] < 0 else
            'Interval includes zero; this cohort does not establish a difference.')
        report['matched_comparisons'][intervention+'_minus_'+control] = comparison
    report['analysis_source_sha256'] = sha(Path(__file__))
    (HERE/name/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    plan = json.loads((HERE/'plan.json').read_text())
    report = dict(plan=plan, cohorts={},
                  uncertainty='10000 percentile bootstrap resamples of complete paired blocks within layout families; seed 1940002. Matched differences exclude any pair with an error in either arm. Error-related exclusions may be selective. Pilot is descriptive; conclusions use fresh validation. Intervals are individual comparisons, without multiplicity correction.')
    for name, seed in plan['cohorts'].items():
        cached = HERE/name/'report.json'
        cohort = json.loads(cached.read_text()) if cached.exists() else None
        if cohort:
            assert cohort['analysis_source_sha256'] == sha(Path(__file__))
            for policy in plan['policies']:
                assert cohort['policies'][policy]['tournament_sha256'] == sha(HERE/name/(policy+'.fmtour'))
        report['cohorts'][name] = cohort or analyze_cohort(name, seed, plan)
    # Preserve the host changes separately from immutable AI snapshots, which
    # are already packaged into each tournament together with the runtime.
    files = ['tools/ai_registry.py', 'tools/tournament.py', 'tools/teacher_bot.py',
             'tools/test_teacher_truth.py', 'src/native/engine.c', 'desktop/desk.cpp', 'docs/protocol.md']
    files += [str(p.relative_to(ROOT)) for p in (HERE/'plan.json', HERE/'all-policy.json', HERE/'flag-spy-policy.json', Path(__file__))]
    source = HERE/'framework-source.zip'
    with zipfile.ZipFile(source, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files: archive.write(ROOT/name, name)
    report['framework_source_sha256'] = sha(source)
    report['analysis_source_sha256'] = sha(Path(__file__))
    report['checks'] = {p.name: dict(sha256=sha(p), output=p.read_text()) for p in HERE.glob('tests-*.log')}
    (HERE/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    for name, cohort in report['cohorts'].items():
        print(name, json.dumps(cohort['matched_comparisons'], indent=2))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        plan = json.loads((HERE/'plan.json').read_text())
        name = sys.argv[1]
        analyze_cohort(name, plan['cohorts'][name], plan)
    else:
        main()
