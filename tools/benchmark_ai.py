"""Reproducible comparisons with the frozen v0.2.0 AI; run make benchmark-ai.

Development uses different seeds. Each validation round consists of two games
with identical deployments and engine sides swapped. Confidence intervals
resample complete pairs, so the two games are not treated as independent.
"""
import argparse
from datetime import datetime, timezone
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import zipfile
import shlex
import shutil

from arena import deployments, play
from feldmarschall import ROOT, new_rng, describe_setup, valid_setup


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def statistics(games, engine="current"):
    points = [1.0 if g['winner'] == engine else 0.5 if g['winner'] is None else 0.0 for g in games]
    pairs = [(points[i] + points[i + 1]) / 2 for i in range(0, len(points), 2)]
    rng = random.Random(8675309)
    samples = sorted(sum(rng.choices(pairs, k=len(pairs))) / len(pairs) for _ in range(10000))
    return {
        'games': len(games), 'wins': points.count(1.0), 'draws': points.count(0.5), 'losses': points.count(0.0),
        'score': sum(points) / len(points), 'paired_bootstrap_95': [samples[249], samples[9749]],
        'reasons': dict(Counter(g['reason'] for g in games)),
        'average_plies': sum(g['plies'] for g in games) / len(games),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=300, help='paired rounds for each deployment group')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--levels', action='store_true', help='compare Easy, Normal and Hard with independent seeds')
    mode.add_argument('--previous', action='store_true', help='compare against the frozen 2026-10-14 milestone')
    mode.add_argument('--progress', action='store_true', help='compare against the validated Normal progress milestone')
    mode.add_argument('--adaptive', action='store_true', help='compare against the adaptive Normal milestone')
    mode.add_argument('--missions', action='store_true', help='compare against the coordinated mission milestone')
    mode.add_argument('--league', action='store_true', help='compare against original, planned, adaptive, Easy and greedy opponents')
    parser.add_argument('--suite', choices=('classic', 'broad'), default='classic',
                        help='historical deployments or diverse legal stress deployments')
    parser.add_argument('--candidate-engine', type=Path, default=ROOT / 'build/feldmarschall-engine')
    parser.add_argument('--candidate-command', help='explicit executable and arguments; all script/binary arguments are frozen')
    parser.add_argument('--reference-command', help='explicit reference executable and arguments, replacing the default opponent')
    parser.add_argument('--reference-name', default='teacher-reference')
    parser.add_argument('--reference-source', type=Path)
    parser.add_argument('--source-extra', type=Path, action='append', default=[], help='additional generated model/source files required to rebuild the candidate')
    parser.add_argument('--candidate-source', type=Path, default=ROOT / 'src/core/ai.c')
    parser.add_argument('--phase', choices=('development', 'validation', 'diagnostic'), default='development')
    parser.add_argument('--strategy', default='current', help='explicit experimental policy identifier')
    parser.add_argument('--difficulty', choices=('easy', 'normal', 'hard'), default='normal')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--record-moves', action='store_true', help='save complete move traces for endgame analysis')
    parser.add_argument('--rules',type=int,choices=range(64),help='audited C variant referee; 0 cross-checks Classic')
    parser.add_argument('--rules-library',type=Path,default=ROOT/'build/librules-variant.so')
    parser.add_argument('--seed-offset', type=int, default=0, help='offset deployment seeds for development or held-out validation')
    parser.add_argument('--out', type=Path, help='new output directory; existing directories are never overwritten')
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('--rounds must be positive')
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    if args.reference_command and (args.levels or args.league or args.previous or args.progress or args.adaptive or args.missions):
        parser.error('--reference-command cannot be combined with another opponent selector')
    if args.reference_command and (not args.reference_source or args.reference_name == 'current'):
        parser.error('a distinct reference name and --reference-source are required')
    started = datetime.now(timezone.utc)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    kind = 'league' if args.league else 'levels' if args.levels else 'progress' if args.previous or args.progress or args.adaptive or args.missions else 'v020'
    if args.out is None:
        args.out = ROOT / 'build/ai-benchmarks' / (started.strftime('%Y%m%dT%H%M%S%fZ') + '-' + revision[:8] + '-' + kind)
    candidate_command = args.candidate_command or str(args.candidate_engine.resolve())
    engines = {'current': candidate_command,
               'v020': str(ROOT / 'build/feldmarschall-ai-v020')}
    if args.levels:
        engines = {level: candidate_command + ' --difficulty ' + level
                   for level in ('easy', 'normal', 'hard')}
    else:
        engines['current'] += ' --difficulty ' + args.difficulty
        if args.previous:
            engines = {'current': engines['current'], 'milestone-20261014': str(ROOT / 'build/feldmarschall-ai-20261014') + ' --difficulty ' + args.difficulty}
        elif args.progress:
            engines = {'current': engines['current'], 'normal-progress': str(ROOT / 'build/feldmarschall-ai-normal-progress') + ' --difficulty ' + args.difficulty}
        elif args.adaptive:
            engines = {'current': engines['current'], 'adaptive-progress': str(ROOT / 'build/feldmarschall-ai-adaptive-progress') + ' --difficulty ' + args.difficulty}
        elif args.missions:
            engines = {'current': engines['current'], 'coordinated-missions': str(ROOT / 'build/feldmarschall-ai-coordinated') + ' --difficulty ' + args.difficulty}
        elif args.league:
            engines.update({
                'planned': str(ROOT / 'build/feldmarschall-ai-planned'),
                'adaptive': str(ROOT / 'build/feldmarschall-ai-adaptive-progress') + ' --difficulty ' + args.difficulty,
                'easy': str(ROOT / 'build/feldmarschall-engine') + ' --difficulty easy',
                'greedy': shlex.join([sys.executable, str(ROOT / 'tools/bots.py'), 'greedy']),
            })
    if args.reference_command:
        engines = {'current': engines['current'], args.reference_name: args.reference_command + ' --difficulty ' + args.difficulty}
    if args.rules is not None and args.league:
        # Keep the reference league fixed when comparing Normal with Hard.
        engines['adaptive']=str(ROOT/'build/feldmarschall-ai-adaptive-progress')+' --difficulty normal'
        engines['greedy']=shlex.join([sys.executable,str(ROOT/'tools/variant_bot.py'),'greedy','--rules-library',str(args.rules_library.resolve())])
    pairs = [('normal', 'easy'), ('hard', 'normal'), ('hard', 'easy')] if args.levels else [('current', args.reference_name if args.reference_command else 'milestone-20261014' if args.previous else 'normal-progress' if args.progress else 'adaptive-progress' if args.adaptive else 'coordinated-missions' if args.missions else 'v020')]
    if args.league:
        pairs = [('current', name) for name in engines if name != 'current']
    groups = [('mixed', 20261021), ('random', 20261022), ('presets', 20261023)] if args.levels else [('mixed', 271828), ('random', 314159), ('presets', 161803)]
    if args.suite == 'broad':
        groups = [(name, 20261101+i) for i, name in enumerate(
            ('fortified', 'uniform', 'unguarded', 'forward', 'decoy', 'presets', 'broad-mixed'))]
    groups = [(kind, seed + args.seed_offset) for kind, seed in groups]
    jobs, metadata = [], []
    for kind, seed in groups:
        rng = new_rng(seed)
        for round_index in range(args.rounds):
            setups = (deployments(kind, rng), deployments(kind, rng))
            if not all(valid_setup(setup) for setup in setups):
                raise ValueError(f'invalid deployment in {kind} round {round_index}')
            move_seed = rng.randrange(1, 60000)
            for a, b in pairs:
                for names in [(a, b), (b, a)]:
                    jobs.append((names, tuple(engines[n] for n in names), setups, move_seed, 1000, args.record_moves))
                    if args.rules is not None: jobs[-1]=(*jobs[-1],args.rules,str(args.rules_library.resolve()))
                    metadata.append({'group': kind, 'round': round_index, 'deployments': list(setups),
                                     'deployment_features': [describe_setup(setup) for setup in setups],
                                     'comparison': a + '-vs-' + b})
    provenance = {
        'started_utc': started.isoformat(), 'git_revision': revision,
        'phase': args.phase, 'candidate_source': str(args.candidate_source),
        'strategy': args.strategy,
        'suite': args.suite, 'opponent_league': bool(args.league),
        'command': sys.argv,
        'git_status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True),
        'engine_commands': engines,
        'difficulty': None if args.levels else args.difficulty,
        'tracked_source_sha256': {name: sha(ROOT / name) for name in subprocess.check_output(
            ['git', 'ls-files', 'src/core', 'src/native', 'tools', 'tests/baselines', 'Makefile'], cwd=ROOT, text=True).splitlines() if (ROOT / name).is_file()},
        'rounds_per_group': args.rounds, 'groups': dict(groups), 'max_plies': 1000,
        'source_sha256': sha(args.candidate_source),
        'baseline_sha256': sha(ROOT / 'tests/baselines/ai_v020.c'),
        'rules_sha256': sha(ROOT / 'src/core/rules.c'),
        'engine_sha256': {name: sha(Path(shlex.split(command)[0])) for name, command in engines.items()},
        'level_configuration_sha256': sha(ROOT / 'src/core/ai_level.c'),
        'confidence_method': '10000 bootstrap resamples of complete side-swapped pairs; seed 8675309',
    }
    if args.rules is not None:
        provenance['rules']=args.rules
        provenance['referee']='C rules with per-ply board, disclosed casualties, own casualties, rescues and repetition audit'
    if args.previous:
        provenance['milestone_sha256'] = {name: sha(ROOT / 'tests/baselines' / name) for name in ('ai_levels_20261014.c', 'ai_level_20261014.c')}
    if args.reference_command:
        provenance['reference_source'] = str(args.reference_source)
        provenance['reference_source_sha256'] = sha(args.reference_source)
    if args.progress:
        provenance['milestone_sha256'] = {name: sha(ROOT / 'tests/baselines' / name) for name in ('ai_normal_progress_20261014.c', 'ai_level_20261014.c')}
    if args.adaptive:
        provenance['milestone_sha256'] = {name: sha(ROOT / 'tests/baselines' / name) for name in ('ai_adaptive_progress_20261014.c', 'ai_level_20261014.c')}
    if args.missions:
        provenance['milestone_sha256'] = {name: sha(ROOT / 'tests/baselines' / name) for name in ('ai_coordinated_20261014.c', 'ai_mission_20261014.c', 'ai_level_20261014.c')}
    if args.league:
        provenance['milestone_sha256'] = {name: sha(ROOT / 'tests/baselines' / name) for name in
            ('ai_v020.c', 'ai_planned.c', 'ai_adaptive_progress_20261014.c', 'ai_level_20261014.c')}
    try:
        args.out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f'output directory already exists: {args.out}; choose a new --out')
    print(f'Benchmark records: {args.out}', file=sys.stderr)
    # Retain dirty and untracked implementations too: a hash is not a snapshot.
    source_files = [ROOT / 'Makefile', ROOT / 'src/Makefile', args.candidate_source.resolve()]
    source_files.extend(path.resolve() for path in args.source_extra)
    for directory in ('src', 'tools', 'tests'):
        source_files.extend(p for p in (ROOT / directory).rglob('*') if p.suffix in ('.c', '.h', '.s', '.py', '.cfg', '.md'))
    with zipfile.ZipFile(args.out / 'sources.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(source_files)):
            if path.is_file():
                archive.write(path, str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else 'candidate/' + path.name)
    provenance['source_archive_sha256'] = sha(args.out / 'sources.zip')
    # Rebuilding the project must not change an engine half-way through a run.
    frozen_commands = {}
    (args.out / 'engines').mkdir()
    provenance['support_sha256'] = {}
    if args.rules is not None:
        frozen_referee=args.out/'engines/support/referee/rules.so'
        frozen_referee.parent.mkdir(parents=True)
        shutil.copy2(args.rules_library,frozen_referee)
        provenance['support_sha256'][str(frozen_referee.relative_to(args.out))]=sha(frozen_referee)
    for name, command in engines.items():
        executable, *arguments = shlex.split(command)
        target = args.out / 'engines' / name
        shutil.copy2(executable, target)
        # Script opponents need their imports frozen too. Running a retained
        # interpreter against mutable scripts would invalidate reproducibility.
        for index, argument in enumerate(arguments):
            script = Path(argument)
            if script.suffix == '.py' and script.is_file():
                support = args.out / 'engines' / 'support' / name
                support.mkdir(parents=True, exist_ok=True)
                for dependency in script.parent.glob('*.py'):
                    copied = support / dependency.name
                    shutil.copy2(dependency, copied)
                    provenance['support_sha256'][str(copied.relative_to(args.out))] = sha(copied)
                arguments[index] = str((support / script.name).resolve())
            elif script.is_file():
                # Teacher adapters also depend on native observer/search programs.
                support = args.out / 'engines' / 'support' / name
                support.mkdir(parents=True, exist_ok=True)
                copied = support / script.name
                if copied.exists():
                    if sha(copied) != sha(script): raise ValueError(f'conflicting support filenames: {script}')
                else: shutil.copy2(script, copied)
                provenance['support_sha256'][str(copied.relative_to(args.out))] = sha(copied)
                arguments[index] = str(copied.resolve())
        frozen_commands[name] = shlex.join([str(target.resolve()), *arguments])
        provenance['engine_sha256'][name] = sha(target)
    provenance['run_engine_commands'] = frozen_commands
    jobs = [(names, tuple(frozen_commands[name] for name in names), *rest)
            for names, commands, *rest in jobs]
    if args.rules is not None: jobs=[(*job[:-1],str(frozen_referee.resolve())) for job in jobs]
    (args.out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    games = []
    with (args.out / 'games.jsonl').open('w') as out, ProcessPoolExecutor(args.jobs) as pool:
        for i, game in enumerate(pool.map(play, jobs)):
            game.update(metadata[i])
            games.append(game)
            out.write(json.dumps(game) + '\n')
            if (i + 1) % 100 == 0:
                print(f'{i + 1}/{len(jobs)} games', file=sys.stderr)
    report = {'provenance': provenance, 'comparisons': {}}
    for a, b in pairs:
        name = a + '-vs-' + b
        selected = [g for g in games if g['comparison'] == name]
        result = {'groups': {kind: statistics([g for g in selected if g['group'] == kind], a) for kind, _ in groups},
                  'overall': statistics(selected, a)}
        report['comparisons'][name] = result
        for kind, stat in [*result['groups'].items(), ('overall', result['overall'])]:
            lo, hi = stat['paired_bootstrap_95']
            print(f'{name}, {kind}: {stat["wins"]} wins, {stat["draws"]} draws, {stat["losses"]} losses; '
                  f'score {stat["score"]:.1%}, paired 95% CI {lo:.1%}–{hi:.1%}')
    if not args.levels and not args.league:
        report.update(report['comparisons'][pairs[0][0] + '-vs-' + pairs[0][1]])
    (args.out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    illegal = [g for g in games if g['reason'].startswith('illegal')]
    if illegal:
        raise SystemExit(f'{len(illegal)} illegal decisions; see games.jsonl')


if __name__ == '__main__':
    main()
