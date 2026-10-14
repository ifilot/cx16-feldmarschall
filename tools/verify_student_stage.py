"""Audit a frozen student's independent game matrix and retained model source."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import zipfile

from benchmark_ai import statistics
from feldmarschall import STRESS_SETUPS, valid_setup


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(policy_path, run):
    policy = json.loads(policy_path.read_text())
    for name, digest in policy['files'].items():
        if sha(Path(name)) != digest: raise ValueError(f'frozen file changed: {name}')
    provenance = json.loads((run / 'provenance.json').read_text())
    report = json.loads((run / 'summary.json').read_text())
    assert report['provenance'] == provenance
    assert provenance['phase'] == 'validation' and provenance['difficulty'] == policy['difficulty']
    assert provenance['rounds_per_group'] == policy['validation_rounds_per_family']
    assert {n - 20261101 for n in provenance['groups'].values()} == set(range(policy['validation_seed_offset'], policy['validation_seed_offset']+7))
    for name, digest in provenance['engine_sha256'].items(): assert sha(run/'engines'/name) == digest
    assert sha(run/'sources.zip') == provenance['source_archive_sha256']
    engine = run/'engines/current'
    expected_engine = next(d for n,d in policy['files'].items() if n.endswith('/engines/current'))
    assert sha(engine) == expected_engine
    header = next(n for n in policy['files'] if n.endswith('/ai_student_model_v2.h'))
    model_path = next(n for n in policy['files'] if n.endswith('/model.json'))
    with zipfile.ZipFile(run/'sources.zip') as sources:
        assert hashlib.sha256(sources.read(header)).hexdigest() == policy['files'][header]
    model = json.loads(Path(model_path).read_text())
    table = b''.join(struct.pack('<BBBBh', *(node[k] for k in ('feature','threshold','left','right','value'))) for node in model['nodes'])
    assert table in engine.read_bytes()
    games = [json.loads(line) for line in (run/'games.jsonl').read_text().splitlines()]
    assert len(games) == 14 * policy['validation_rounds_per_family']
    assert {g['group'] for g in games} == {*STRESS_SETUPS, 'presets', 'broad-mixed'}
    pairs = defaultdict(list)
    for game in games:
        assert len(game['moves']) == game['plies'] and not game['reason'].startswith('illegal')
        assert all(valid_setup(setup) for setup in game['deployments'])
        pairs[(game['group'],game['round'],game['comparison'])].append(game)
    for pair in pairs.values():
        assert len(pair) == 2 and pair[0]['red'] == pair[1]['blue'] and pair[0]['blue'] == pair[1]['red']
        assert pair[0]['seed'] == pair[1]['seed'] and pair[0]['deployments'] == pair[1]['deployments']
    score = statistics(games)
    assert next(iter(report['comparisons'].values()))['overall'] == score
    return {'scope': 'Classic Normal independent strength only; tactical, fairness and X16 gates remain separate',
            'policy_sha256': sha(policy_path), 'program_sha256': sha(engine),
            'model_bytes': len(table), 'score': score,
            'strength_gate_passed': score['paired_bootstrap_95'][0] > .5}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.policy, args.run)
    with args.out.open('x') as output: output.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
