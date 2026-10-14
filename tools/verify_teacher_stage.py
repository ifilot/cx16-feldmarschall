"""Audit teacher trial matrices, frozen dependencies and independent strength gates."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shlex

from benchmark_ai import statistics
from feldmarschall import valid_setup, STRESS_SETUPS


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_run(run):
    report = json.loads((run / 'summary.json').read_text())
    provenance = json.loads((run / 'provenance.json').read_text())
    assert report['provenance'] == provenance
    games = [json.loads(line) for line in (run / 'games.jsonl').read_text().splitlines()]
    assert len(games) == 14 * provenance['rounds_per_group']
    assert {g['group'] for g in games} == {*STRESS_SETUPS, 'presets', 'broad-mixed'}
    assert len(report['comparisons']) == 1
    pairs = defaultdict(list)
    for game in games:
        assert not game['reason'].startswith('illegal') and len(game['moves']) == game['plies']
        assert all(valid_setup(s) for s in game['deployments'])
        pairs[(game['group'], game['round'], game['comparison'])].append(game)
    for pair in pairs.values():
        assert len(pair) == 2 and pair[0]['red'] == pair[1]['blue'] and pair[0]['blue'] == pair[1]['red']
        assert pair[0]['deployments'] == pair[1]['deployments'] and pair[0]['seed'] == pair[1]['seed']
    for name, digest in provenance['engine_sha256'].items(): assert sha(run / 'engines' / name) == digest
    for name, digest in provenance['support_sha256'].items(): assert sha(run / name) == digest
    assert sha(run / 'sources.zip') == provenance['source_archive_sha256']
    actual = statistics(games)
    summary = next(iter(report['comparisons'].values()))['overall']
    assert summary == actual
    command = shlex.split(provenance['run_engine_commands']['current'])
    programs = {name: Path(command[command.index('--' + name) + 1]) for name in ('teacher', 'observer')}
    for path in programs.values(): assert path.is_relative_to(run.resolve()) and path.is_file()
    return report, programs


def gate(policy_path, mission, material):
    policy = json.loads(policy_path.read_text())
    first, programs = verify_run(mission); second, other_programs = verify_run(material)
    for report in (first, second):
        p = report['provenance']
        assert p['phase'] == 'validation' and p['difficulty'] == 'normal'
        assert p['rounds_per_group'] == policy['rounds_per_family']
        args = shlex.split(p['run_engine_commands']['current'])
        for key in ('samples', 'depth', 'blend'): assert args[args.index('--' + key) + 1] == str(policy[key])
        assert ('--strategic' in args) == policy['strategic']
        assert p['engine_sha256']['current'] == policy['development_program_sha256']
        # Names can change while immutable program/script contents must match.
        candidate_support = {Path(name).name: digest for name, digest in p['support_sha256'].items()
                             if name.startswith('engines/support/current/')}
        expected_support = {Path(name).name: digest for name, digest in policy['development_support_sha256'].items()}
        assert candidate_support == expected_support
    for report, offset in zip((first, second), policy['planned_validation_seed_offsets']):
        assert {v - 20261101 for v in report['provenance']['groups'].values()} == set(range(offset, offset+7))
    assert sha(programs['teacher']) == sha(other_programs['teacher'])
    reference = shlex.split(second['provenance']['run_engine_commands']['material-teacher'])
    for key, value in [('samples', policy['samples']), ('depth', 3), ('blend', 'correction')]:
        assert reference[reference.index('--' + key) + 1] == str(value)
    assert '--strategic' not in reference
    assert sha(Path(reference[reference.index('--observer')+1])) == sha(programs['observer'])
    scores = {name: next(iter(report['comparisons'].values()))['overall']
              for name, report in [('mission', first), ('material', second)]}
    passed = all(s['paired_bootstrap_95'][0] > .5 for s in scores.values())
    return {'schema': 1, 'both_gates_passed': passed, 'scope': 'Classic Normal, seven broad layout families',
            'policy_sha256': sha(policy_path), 'samples': policy['samples'], 'depth': policy['depth'],
            'policy_path': str(policy_path.resolve()),
            'teacher_program': str(programs['teacher']), 'teacher_sha256': sha(programs['teacher']),
            'observer_program': str(programs['observer']), 'observer_sha256': sha(programs['observer']),
            'validation_runs': [str(mission.resolve()), str(material.resolve())],
            'validation_summary_sha256': [sha(path / 'summary.json') for path in (mission, material)],
            'scores': scores}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--mission', type=Path, required=True)
    parser.add_argument('--material', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = gate(args.policy, args.mission, args.material)
    with args.out.open('x') as output: output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
