"""Fit all-action corrections only after the rollout teacher passes its strength gates."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

from feldmarschall import ROOT, GLYPHS, parse_square, setup_squares, valid_setup
from teacher_bot import TeacherBot
from train_ai_student import fit, predict


def own_initial(info, history):
    """Reverse only legitimate own ranks and Classic public battle disclosures."""
    if info['rules'] != 0: raise ValueError('Classic training only')
    army = info['army']; cells = bytes.fromhex(info['board_hex'])
    pieces = {sq: cell & 15 for sq, cell in enumerate(cells)
              if cell < 254 and bool(cell & 16) == bool(army)}
    for ply in range(len(history) - 1, -1, -1):
        words = history[ply].split(); src, dst = map(parse_square, words[1:3])
        if words[0] == 'moved':
            if ply % 2 == army: pieces[src] = pieces.pop(dst)
        elif words[0] == 'battle':
            if ply % 2 == army:
                pieces.pop(dst, None); pieces[src] = GLYPHS.index(words[3])
            else: pieces[dst] = GLYPHS.index(words[4])
        else: raise ValueError('unsupported public event')
    squares = setup_squares(army)
    if set(pieces) != set(squares): raise ValueError('history does not reconstruct own initial squares')
    result = ''.join(GLYPHS[pieces[sq]] for sq in squares)
    if not valid_setup(result): raise ValueError('history does not reconstruct a legal own army')
    return result


def shuttle_hex(info):
    return bytes(info['shuttle'][str(a)][i] if info['shuttle'][str(a)][i] is not None else 255
                 for i in range(3) for a in (0, 1)).hex()


def canonical_shuttle(text):
    state = list(bytes.fromhex(text))
    for army in (0, 1):
        if state[4 + army] == 0: state[army] = state[2 + army] = 255
    return bytes(state).hex()


def label_record(job):
    record, observer, teacher, samples, *settings = job
    options = settings[0] if settings else {}
    info, history = record['input'], record['public_history']
    army = info['army']; group = record['split_group']
    rows = []; nodes = 0
    for cold in (False, True):
        bot = TeacherBot(Path(observer), Path(teacher), samples=samples, depth=4, blend='correction',
                         strategic=True, context=options.get('context', False))
        try:
            seed = int(hashlib.sha256(record['id'].encode()).hexdigest()[:8], 16)
            bot.rng.seed(seed); bot.observer.send('seed ' + str(seed % 65535 + 1))
            if cold:
                bot.observer.ask(f"position {army} {info['enemy_lost_hex']} {info['board_hex']} {shuttle_hex(info)}", 'positionok')
            else:
                bot.observer.send('new ' + ('red', 'blue')[army])
                bot.observer.send('setup ' + own_initial(info, history))
                for ply, event in enumerate(history):
                    if ply % 2 == army:
                        bot.observer.ask('go', 'move')
                        bot.observer.ask('played ' + ' '.join(event.split()[1:3]), 'playedok')
                    bot.observer.send(event)
            public = bot.observer.ask('public', 'public').split()
            public[3] = canonical_shuttle(public[3])
            if public != [str(army), info['board_hex'], info['enemy_lost_hex'], shuttle_hex(info)]:
                raise ValueError(f"public reconstruction differs: {record['id']} {'cold' if cold else 'full'}; {public} != {[str(army), info['board_hex'], info['enemy_lost_hex'], shuttle_hex(info)]}")
            bot.observer.send(f"features {army} {info['enemy_lost_hex']} {info['board_hex']} 0")
            vectors = {}
            while True:
                words = bot.observer.read().split()
                if words[0] == 'features_done': break
                if words[0] != 'feature': raise ValueError(words)
                values = list(map(int, words[1:])); vectors[tuple(values[:2])] = values[2:]
            bot.choose(); nodes += bot.last_report['nodes']
            for value in bot.last_report['values']:
                move = tuple(value['move']); features = vectors[move]
                correction = round(value['correction'])
                if 'baseline_model' in options:
                    # The context teacher starts from the guarded production
                    # student. Its correction is a delta; a replacement model
                    # must also reproduce the baseline's existing correction.
                    correction += predict(options['baseline_model'], features)
                rows.append({'position': record['id'], 'split_group': group,
                             'validation': int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 5 == 0,
                             'history': 'cold' if cold else 'full', 'move': move, 'features': features,
                             'target': correction})
        finally: bot.close()
    return {'id': record['id'], 'rows': rows, 'nodes': nodes}


def public_record(record):
    # Selection/split metadata stays outside teacher features. Oracle fields,
    # enemy deployments and source replay data never reach producer workers.
    return {'id': record['id'], 'input': record['input'], 'public_history': record['public_history'],
            'split_group': f"{record['source']['group']}:{record['source']['seed']}"}


def require_teacher_gate(path):
    gate = json.loads(path.read_text())
    if not gate.get('both_gates_passed'):
        raise ValueError('teacher strength gates are not satisfied')
    from verify_teacher_stage import gate as audit_gate
    actual = audit_gate(Path(gate['policy_path']), *map(Path, gate['validation_runs']))
    if actual != gate: raise ValueError('teacher gate differs from verified current evidence')
    return gate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--positions', type=int, default=512)
    parser.add_argument('--samples', type=int, default=8)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--corpus', type=Path, default=ROOT / 'docs/ai-diagnostics/positions-20261014.zip')
    parser.add_argument('--observer', type=Path, default=ROOT / 'build/feldmarschall-teacher-observer')
    args = parser.parse_args()
    gate = require_teacher_gate(args.gate)
    if args.samples != gate['samples']: parser.error('label sampling budget must match the validated teacher')
    if min(args.positions, args.samples, args.jobs) < 1: parser.error('positive counts required')
    args.out.mkdir(parents=True, exist_ok=False)
    observer = args.out / 'observer'; teacher = args.out / 'teacher'
    shutil.copy2(args.observer, observer)
    shutil.copy2(gate['teacher_program'], teacher)
    if hashlib.sha256(teacher.read_bytes()).hexdigest() != gate['teacher_sha256']:
        raise ValueError('teacher program differs from accepted gate')
    shutil.copy2(sys.executable, args.out / 'python')
    with zipfile.ZipFile(args.out / 'sources.zip', 'x', compression=zipfile.ZIP_DEFLATED) as snapshot:
        for directory in ('src', 'tests', 'tools'):
            for path in (ROOT / directory).rglob('*'):
                if path.suffix in ('.c', '.h', '.s', '.py', '.cfg', '.md'): snapshot.write(path, str(path.relative_to(ROOT)))
        for name in ('Makefile', 'src/Makefile'): snapshot.write(ROOT/name, name)
    provenance = {'schema': 1, 'teacher_gate': gate, 'samples': args.samples, 'positions': args.positions,
                  'source_archive_sha256': hashlib.sha256((args.out/'sources.zip').read_bytes()).hexdigest(),
                  'program_sha256': {name: hashlib.sha256((args.out/name).read_bytes()).hexdigest()
                                     for name in ('observer', 'teacher', 'python')},
                  'python_version': sys.version, 'command': sys.argv,
                  'corpus_sha256': hashlib.sha256(args.corpus.read_bytes()).hexdigest(),
                  'feature_scope': 'input and public_history only; source family/seed used solely for grouping'}
    (args.out / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    if args.corpus.suffix == '.zip':
        with zipfile.ZipFile(args.corpus) as archive:
            records = [json.loads(line) for line in archive.read('positions.jsonl').splitlines()]
    else:
        records = [json.loads(line) for line in args.corpus.read_text().splitlines()]
    # Deterministic coverage of families/outcomes through a stable hash order.
    records.sort(key=lambda r: hashlib.sha256(r['id'].encode()).hexdigest())
    selected = [public_record(r) for r in records[:args.positions]]
    (args.out / 'public-inputs.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in selected))
    jobs = [(r, str(observer.resolve()), str(teacher.resolve()), args.samples) for r in selected]
    rows = []; nodes = 0
    with (args.out / 'labels.jsonl').open('w') as output, ProcessPoolExecutor(args.jobs) as pool:
        for index, result in enumerate(pool.map(label_record, jobs)):
            rows.extend(result['rows']); nodes += result['nodes']
            for row in result['rows']: output.write(json.dumps(row) + '\n')
            if (index + 1) % 16 == 0: print(f'{index+1}/{len(selected)} positions', flush=True)
    training = [r for r in rows if not r['validation']]; validation = [r for r in rows if r['validation']]
    if not training or not validation: raise ValueError('both grouped splits required')
    model = fit(training)
    report = {'nodes': model, 'node_bytes': len(model) * 6, 'positions': len(selected), 'rows': len(rows),
              'teacher_nodes': nodes, 'training_rows': len(training), 'validation_rows': len(validation),
              'validation_mae': sum(abs(predict(model,r['features'])-r['target']) for r in validation)/len(validation),
              'zero_mae': sum(abs(r['target']) for r in validation)/len(validation),
              'teacher_sha256': gate['teacher_sha256'],
              'scope': 'Grouped development fit only; independent game strength and X16 gates are still required.'}
    (args.out / 'model.json').write_text(json.dumps(report, indent=2) + '\n')
    header = ['/* Generated all-action teacher student. Experimental until independently validated. */',
              'static const student_node_t student_nodes[] = {']
    for node in model:
        header.append('    {' + ','.join(str(node[key]) for key in ('feature','threshold','left','right','value')) + '},')
    header.append('};')
    (args.out / 'ai_student_model_v2.h').write_text('\n'.join(header) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'nodes'}, indent=2))


if __name__ == '__main__': main()
