"""Check frozen desktop ranking inference, guarded integration and masking."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shlex
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT, build_policy, get_policy
from diagnose_transfer_teacher import restore
from feldmarschall import Engine, square_name, parse_square
from train_ai_student import predict, sample_world
from train_teacher_student import shuttle_hex

BASE = ROOT / 'docs/ai-transfer-2026-10-15'
IDENTITY = 'ranking-student-v1-normal'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def feature_rows(engine, info):
    engine.send(f"features {info['army']} {info['enemy_lost_hex']} {info['board_hex']} 0")
    rows = {}
    while True:
        words = engine.read().split()
        if words[0] == 'features_done':
            return rows
        assert words[0] == 'feature', words
        values = list(map(int, words[1:])); rows[tuple(values[:2])] = values[2:]


def ranked(engine):
    engine.send('ranked'); rows = {}
    while True:
        words = engine.read().split()
        if words[0] == 'move':
            return rows, tuple(map(parse_square, words[1:3]))
        if words[0] == 'candidate':
            rows[tuple(map(int, words[1:3]))] = int(words[3])
        assert words[0] != 'error', words


def command_move(move):
    return ' '.join(map(square_name, move))


def delta(model, features):
    total = sum(predict(tree, features) for tree in model['trees'])
    # C integer division truncates toward zero, including negative sums.
    return max(-192, min(192, int(total / model['scale'])))


def compile_engine(source, policy, output, include=None, ensemble=True):
    defines = [d for d in policy['defines'] if d != 'AI_STUDENT_ENSEMBLE']
    if ensemble:
        defines.append('AI_STUDENT_ENSEMBLE')
    command = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Wno-format-overflow', '-Isrc/core']
    if include is not None:
        command.append('-I' + str(include))
    command += ['-I' + p for p in policy.get('include_dirs', [])]
    command += ['-D' + d for d in defines]
    command += ['-o', str(output), *policy['sources']]
    subprocess.run(command, cwd=source, check=True)
    return command


def cold(engine, record, cells=None):
    info = record['input']
    engine.send('seed 19361')
    engine.ask(f"position {info['army']} {info['enemy_lost_hex']} "
               f"{bytes(cells).hex() if cells is not None else info['board_hex']} {shuttle_hex(info)}", 'positionok')


def check(identity=IDENTITY, model_dir=None, output_prefix=None):
    model_dir = BASE / 'model' if model_dir is None else Path(model_dir)
    report_path = BASE / 'checks/ranking-runtime.json' if output_prefix is None else Path(str(output_prefix) + '.json')
    probe_path = BASE / 'checks/ensemble-runtime-probes.zip' if output_prefix is None else Path(str(output_prefix) + '-probes.zip')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    policy = get_policy(identity)
    executable, receipt = build_policy(identity)
    source_bytes = (ROOT / policy['archive']).read_bytes()
    assert digest(source_bytes) == policy['source_sha256']
    with zipfile.ZipFile(model_dir / 'ranking-inputs.zip') as archive:
        roots = [json.loads(line) for line in archive.read('roots.jsonl').splitlines()]
    with zipfile.ZipFile(ROOT / 'docs/ai-cycle-2026-10-15/student-model/training-evidence.zip') as archive:
        records = {r['id']: r for r in map(json.loads, archive.read('public-inputs.jsonl').splitlines())}
    model = json.loads((model_dir / 'model.json').read_text())
    held = [r for r in roots if r['validation']]
    counts = dict(held_out_positions=len(held), full_history_actions=0, cold_actions=0,
                  guarded_actions=0, winning_actions=0, masking_positions=0,
                  native_selection_checks=0)
    native_entries = []
    assert held
    with tempfile.TemporaryDirectory(prefix='ranking-runtime-', dir='/tmp') as directory:
        folder = Path(directory); source = folder / 'source'; source.mkdir()
        with zipfile.ZipFile(ROOT / policy['archive']) as archive:
            archive.extractall(source)
        header = policy['include_dirs'][0] + '/ai_student_ensemble.h'
        assert (source / header).read_bytes() == (model_dir / 'ai_student_ensemble.h').read_bytes()
        baseline = folder / 'baseline'
        commands = [compile_engine(source, policy, baseline, ensemble=False)]
        baseline_nodes = []
        import re
        for line in (source / 'src/core/ai_student_model_production.h').read_text().splitlines():
            values = re.findall(r'-?\d+', line)
            if line.strip().startswith('{') and len(values) == 5:
                baseline_nodes.append(dict(zip(('feature','threshold','left','right','value'), map(int,values))))
        assert len(baseline_nodes) == 31
        engines = [Engine(shlex.quote(str(path))) for path in (baseline, executable)]
        try:
            for root in held:
                record = records[root['id']]; info = record['input']
                for engine in engines:
                    restore(engine, record)
                features = [feature_rows(e, info) for e in engines]
                assert features[0] == features[1]
                rankings = [ranked(e) for e in engines]
                assert rankings[0][0].keys() == rankings[1][0].keys() == features[0].keys()
                retained = {tuple(row['move']): row for row in root['rows']}
                assert features[0] == {move: row['features'] for move,row in retained.items()}
                assert rankings[0][0] == {move: row['native'] for move,row in retained.items()}
                for move, vector in features[1].items():
                    text = command_move(move)
                    raw = int(engines[1].ask('student ' + text, 'learned'))
                    expected = predict(baseline_nodes, vector) + delta(model, vector)
                    assert raw == expected, (root['id'], move, raw, expected)
                    guard = int(engines[1].ask('guarded ' + text, 'guarded'))
                    assert guard == int(engines[0].ask('guarded ' + text, 'guarded'))
                    assert guard == retained[move]['guarded']
                    winning = rankings[0][0][move] >= 30000
                    expected_difference = 0 if guard or winning else delta(model, vector)
                    difference = rankings[1][0][move] - rankings[0][0][move]
                    assert difference == expected_difference, (root['id'], move, difference, expected_difference)
                    counts['full_history_actions'] += 1
                    counts['guarded_actions'] += guard
                    counts['winning_actions'] += winning
                # Native selection retains the first encountered maximal score.
                assert rankings[1][1] == max(rankings[1][0], key=rankings[1][0].get)
                counts['native_selection_checks'] += 1
                best = max(row['teacher_value'] for row in retained.values())
                native_entries.append(dict(id=root['id'], production=list(rankings[0][1]),
                    student=list(rankings[1][1]), production_regret=best-retained[rankings[0][1]]['teacher_value'],
                    student_regret=best-retained[rankings[1][1]]['teacher_value']))
                for engine in engines:
                    cold(engine, record)
                cold_features = feature_rows(engines[1], info)
                cold_rankings = [ranked(e) for e in engines]
                for move, vector in cold_features.items():
                    guard = int(engines[1].ask('guarded ' + command_move(move), 'guarded'))
                    winning = cold_rankings[0][0][move] >= 30000
                    expected_difference = 0 if guard or winning else delta(model, vector)
                    assert cold_rankings[1][0][move] - cold_rankings[0][0][move] == expected_difference
                    counts['cold_actions'] += 1
                # Feed two legal sampled concealed armies through the masking
                # boundary. Neither assignment is supplied to the learner.
                cold(engines[1], record)
                cells = list(bytes.fromhex(info['board_hex']))
                histories = {sq: list(map(int, engines[1].ask('memory ' + square_name(sq), 'history').split()))
                             for sq, cell in enumerate(cells)
                             if cell < 254 and bool(cell & 16) != bool(info['army']) and not cell & 32}
                worlds = [sample_world(cells, list(bytes.fromhex(info['enemy_lost_hex'])), histories,
                                       random.Random(1821001 + batch), info['army'])[0] for batch in (0,1)]
                observations = []
                for world in worlds:
                    cold(engines[1], record, world)
                    public = engines[1].ask('public', 'public')
                    observations.append((public, ranked(engines[1])))
                assert observations[0] == observations[1]
                counts['masking_positions'] += 1
        finally:
            for engine in engines:
                engine.close()
        assert counts['guarded_actions'] > 0, 'Corpus must exercise cooperation protection'
        # Frozen-core probes independently exercise scale, zero-delta parity,
        # and positive/negative clipping, without changing the learned model.
        probe_results = {}
        record = records[held[0]['id']]
        with zipfile.ZipFile(probe_path, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for name, value in [('zero',0), ('positive',30000), ('negative',-30000)]:
                include = folder / name; include.mkdir()
                generated = ('#define ENSEMBLE_TREES 8\n#define ENSEMBLE_SCALE 1000\n'
                             'static const unsigned int ensemble_offsets[]={0,0,0,0,0,0,0,0};\n'
                             'static const ensemble_node_t ensemble_nodes[]={{255,0,0,0,'+str(value)+'}};\n')
                (include / 'ai_student_ensemble.h').write_text(generated)
                binary = folder / (name + '-engine')
                commands.append(compile_engine(source, policy, binary, include))
                pair = [Engine(shlex.quote(str(p))) for p in (baseline, binary)]
                try:
                    for engine in pair:
                        cold(engine, record)
                    move = command_move(tuple(held[0]['rows'][0]['move']))
                    raw = [int(e.ask('student ' + move,'learned')) for e in pair]
                    expected = {'zero':0,'positive':192,'negative':-192}[name]
                    assert raw[1] - raw[0] == expected
                    if name == 'zero':
                        assert ranked(pair[0]) == ranked(pair[1])
                    probe_results[name] = dict(raw_difference=raw[1]-raw[0], binary_sha256=digest(binary.read_bytes()))
                    bundle.writestr(name + '/ai_student_ensemble.h', generated)
                    bundle.write(binary, name + '/engine')
                finally:
                    for engine in pair:
                        engine.close()
            report = dict(policy=policy, runtime=receipt, counts=counts, probes=probe_results,
                          native_offline_entries=native_entries,
                          native_mean_regret_improvement=sum(e['production_regret']-e['student_regret'] for e in native_entries)/len(native_entries),
                          commands=commands, test_source_sha256=digest(Path(__file__).read_bytes()),
                          scope='Frozen native inference and integration checks; no strength claim.')
            bundle.writestr('report.json', json.dumps(report,indent=2)+'\n')
            bundle.writestr('test_ranking_student.py', Path(__file__).read_bytes())
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(counts,indent=2))
    print('Frozen ranking model: exact inference, guarded score integration, selection and masking passed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', default=IDENTITY)
    parser.add_argument('--model-dir', type=Path)
    parser.add_argument('--output-prefix', type=Path)
    args = parser.parse_args()
    check(args.identity, args.model_dir, args.output_prefix)
