"""Compare teachers on permitted histories with warm native planning and fresh samples."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys

from feldmarschall import ROOT
from teacher_bot import TeacherBot


def evaluate(case, teacher, depth, strategic, blend, observer, samples):
    bot = TeacherBot(observer, teacher, samples=samples, depth=depth, strategic=strategic, blend=blend)
    try:
        army = case['input']['army']
        seed = case['source']['seed'] * 2 + army + 1
        bot.rng.seed(int(hashlib.sha256(case['id'].encode()).hexdigest()[:8], 16))
        bot.observer.send('seed ' + str(seed))
        bot.observer.send('difficulty ' + case['difficulty'])
        bot.observer.send('new ' + ('red', 'blue')[army])
        bot.observer.send('setup ' + case['own_initial_setup'])
        for ply, event in enumerate(case['public_history']):
            if ply % 2 == army:
                bot.observer.ask('go', 'move')
                bot.observer.ask('played ' + ' '.join(event.split()[1:3]), 'playedok')
            bot.observer.send(event)
        raw = bot.observer.ask('public', 'public').split()
        assert int(raw[0]) == army and raw[1] == case['input']['board_hex'] and raw[2] == case['input']['enemy_lost_hex']
        expected = bytes(case['input']['shuttle'][str(a)][i] if case['input']['shuttle'][str(a)][i] is not None else 255
                         for i in range(3) for a in (0, 1)).hex()
        assert raw[3] == expected
        chosen = bot.choose()
        assert list(chosen) in case['legal_moves']
        return bot.last_report
    finally: bot.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=ROOT / 'docs/ai-mission-cases/cases.jsonl')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=32)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    observer = args.out / 'observer'; shutil.copy2(ROOT / 'build/feldmarschall-teacher-observer', observer)
    programs = {}
    for name in ('teacher', 'teacher-rollout'):
        programs[name] = args.out / name; shutil.copy2(ROOT / ('build/feldmarschall-' + name), programs[name])
    configurations = [('material', 'teacher', 3, False, 'raw'),
                      ('rollout', 'teacher-rollout', 4, True, 'raw'),
                      ('correction', 'teacher-rollout', 4, True, 'correction')]
    cases = [json.loads(line) for line in args.cases.read_text().splitlines()]
    rows = []
    for case in cases:
        row = {'id': case['id'], 'category': case['category'], 'difficulty': case['difficulty'],
               'samples': args.samples, 'policies': {}}
        for name, program, depth, strategic, blend in configurations:
            row['policies'][name] = evaluate(case, programs[program].resolve(), depth, strategic, blend,
                                             observer.resolve(), args.samples)
        rows.append(row)
        print(f'{len(rows)}/{len(cases)} cases', flush=True)
    report = {'cases_sha256': hashlib.sha256(args.cases.read_bytes()).hexdigest(),
              'program_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for name, path in {'observer': observer, **programs}.items()},
              'scope': 'Shared public histories and native executed-action planning caches. Fresh paired world draws at each root; rollout futures begin with cold policy caches. Diagnostic choices, not strength claims.',
              'positions': rows}
    (args.out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__': main()
