"""Run named Classic AIs in paired tournaments; inspect and verify .fmtour files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import importlib
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from ai_registry import ROOT, build_policy, catalog, digest
from arena import deployments
from feldmarschall import new_rng
from tournament_store import Tournament, verify

FAMILIES = ('fortified', 'uniform', 'unguarded', 'forward', 'decoy', 'presets', 'broad-mixed')
DEFAULT_WORKER = ROOT / 'build/desktop/feldmarschall-tournament-worker'


def openmp_results(queue, worker, working, threads, argv_commands, original_dos=None, reuse_processes=False):
    """Stream independently completed C++/OpenMP matches; storage stays single-writer."""
    plan = working / 'openmp-plan.json'
    plan.write_text(json.dumps(dict(threads=threads, timeout_ms=60000, reuse_processes=reuse_processes, jobs=[
        dict(names=names, commands=[argv_commands[n] for n in names], setups=setups,
             original_dos_setup=[bool(original_dos and original_dos.get(n)) for n in names],
             seed=seed, max_plies=max_plies)
        for names, commands, setups, seed, max_plies, record in queue])))
    errors = []
    process = subprocess.Popen([str(worker), str(plan)], cwd=ROOT, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for line in process.stdout:
            event = json.loads(line)
            if event.get('event') == 'backend':
                yield None, event
            elif event.get('event') == 'game':
                yield event['index'], event['game']
            elif event.get('event') == 'error':
                errors.append(f'Match {event["index"] + 1}: {event["message"]}')
        stderr = process.stderr.read()
        code = process.wait()
        if code or errors:
            raise ValueError('\n'.join(errors) or stderr.strip() or f'Native worker exited with {code}')
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        process.stdout.close()
        process.stderr.close()


def load_referee(directory):
    # Engines run in independent native processes. Threads dispatch games without
    # multiprocessing semaphores and work on Windows and restricted Linux hosts.
    # An isolated package pins the Python referee without replacing live modules.
    name = 'fmtour_referee_' + uuid.uuid4().hex
    (directory / '__init__.py').write_text('')
    spec = importlib.util.spec_from_file_location(name, directory / '__init__.py')
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return importlib.import_module(name + '.arena').play


def run(first, second, out, rounds=10, seed=1, jobs=1, families=FAMILIES, max_plies=1000,
        backend='python', worker=DEFAULT_WORKER, reuse_processes=None):
    if first == second:
        raise ValueError('Choose two different AI versions')
    if rounds < 1 or jobs < 1 or max_plies < 1 or not families or any(f not in FAMILIES for f in families):
        raise ValueError('Positive rounds, workers and ply limit, and known layout families required')
    if Path(out).exists():
        raise FileExistsError(f'Tournament already exists: {out}')
    worker = Path(worker).resolve()
    if backend not in ('python', 'openmp'):
        raise ValueError('Unknown tournament backend')
    if backend == 'openmp' and not worker.is_file():
        raise ValueError('OpenMP worker is missing; run make desktop-build first')
    if backend == 'openmp':
        worker_receipt = json.loads(worker.with_name('worker-build.json').read_text())
        worker_sources = worker.with_name('worker-sources.zip').read_bytes()
        if (digest(worker.read_bytes()) != worker_receipt['executable_sha256'] or
                digest(worker_sources) != worker_receipt['source_archive_sha256']):
            raise ValueError('Native worker build integrity mismatch; rebuild the desktop targets')
    built = [build_policy(identity) for identity in (first, second)]
    participants = [receipt for _, receipt in built]
    if reuse_processes is None:
        reuse_processes = backend == 'openmp' and any(p['policy'].get('driver') == 'msdos1990' for p in participants)
    if backend != 'openmp' and reuse_processes:
        raise ValueError('Process reuse requires the OpenMP backend')
    plan = dict(created_utc=datetime.now(timezone.utc).isoformat(), participants=participants,
                seed=seed, rounds=rounds, families=list(families), max_plies=max_plies,
                planned_games=2 * rounds * len(families),
                backend=backend, requested_workers=jobs, reuse_engine_processes=reuse_processes,
                comparison='move policies with common referee-generated deployments; swapped sides',
                score='win=1, draw=0.5, loss=0; paired games share deployments and seed')
    with Tournament(out, create=True, metadata=plan) as tournament, tempfile.TemporaryDirectory(prefix='fmtour-') as temp:
        working = Path(temp)
        commands, argv_commands, original_dos = {}, {}, {}
        for (executable, receipt), identity in zip(built, (first, second)):
            bundle = working / identity
            bundle.mkdir()
            for name in receipt['runtime_sha256']:
                (bundle / name).parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(executable.parent / name, bundle / name)
                tournament.artifact(identity + '/' + name, (bundle / name).read_bytes())
            frozen = bundle / executable.name
            argv_commands[identity] = [str(frozen), '--difficulty', receipt['policy']['difficulty']]
            commands[identity] = shlex.join(argv_commands[identity])
            original_dos[identity] = receipt['policy'].get('driver') == 'msdos1990'
            tournament.artifact(receipt['policy']['archive'], (ROOT / receipt['policy']['archive']).read_bytes())
        referee = working / 'referee'
        referee.mkdir()
        referee_hashes = {}
        sources = ('arena.py', 'feldmarschall.py') if backend == 'python' else ()
        for name in sources:
            data = (ROOT / 'tools' / name).read_bytes()
            if name == 'arena.py':
                data = data.replace(b'from feldmarschall import', b'from .feldmarschall import')
            if backend == 'python':
                (referee / name).write_bytes(data)
            referee_hashes[name] = tournament.artifact('referee/' + name, data)
        tournament.set_metadata(dict(referee_sha256=referee_hashes))
        if backend == 'openmp':
            frozen_worker = working / worker.name
            shutil.copy2(worker, frozen_worker)
            worker_sha = tournament.artifact('referee/openmp-worker', frozen_worker.read_bytes())
            source_sha = tournament.artifact('referee/worker-sources.zip', worker_sources)
            tournament.set_metadata(dict(worker_sha256=worker_sha, worker_source_sha256=source_sha,
                                         worker_build=worker_receipt))
        else:
            play_game = load_referee(referee)
        queue, descriptions = [], []
        rng = new_rng(seed)
        for family in families:
            for _ in range(rounds):
                setups = (deployments(family, rng), deployments(family, rng))
                move_seed = rng.randrange(1, 60000)
                pair_id = len(descriptions) // 2 + 1
                for names in ((first, second), (second, first)):
                    recording = dict(record_moves=True,original_dos_setup=[original_dos[n] for n in names]) if any(original_dos.values()) else True
                    queue.append((names, tuple(commands[n] for n in names), setups, move_seed, max_plies, recording))
                    descriptions.append((pair_id, family, setups))
        execution_started = time.perf_counter()
        try:
            if backend == 'openmp':
                completed, seen = 0, set()
                for index, game in openmp_results(queue, frozen_worker, working, jobs, argv_commands, original_dos, reuse_processes):
                    if index is None:
                        tournament.set_metadata(dict(parallel_execution=game))
                        continue
                    if index in seen or not 0 <= index < len(queue):
                        raise ValueError('Invalid native match index')
                    seen.add(index)
                    pair_id, family, setups = descriptions[index]
                    tournament.add_game(game, pair_id, family, setups, game_id=index + 1)
                    completed += 1
                    print(json.dumps(dict(event='progress', completed=completed, total=len(queue))), flush=True)
                if completed != len(queue):
                    raise ValueError('Native worker returned an incomplete tournament')
            else:
                with ThreadPoolExecutor(max_workers=jobs) as pool:
                    for completed, (game, (pair_id, family, setups)) in enumerate(zip(pool.map(play_game, queue), descriptions), 1):
                        if game['reason'].startswith('illegal'):
                            raise ValueError(f'AI produced an {game["reason"]}')
                        tournament.add_game(game, pair_id, family, setups)
                        print(json.dumps(dict(event='progress', completed=completed, total=len(queue))), flush=True)
            tournament.set_metadata(dict(status='complete', finished_utc=datetime.now(timezone.utc).isoformat(),
                                         execution_seconds=time.perf_counter()-execution_started))
        except BaseException as error:
            tournament.set_metadata(dict(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', error=str(error)))
            raise
        return tournament.summary()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('list')
    play = actions.add_parser('run')
    play.add_argument('first')
    play.add_argument('second')
    play.add_argument('--out', type=Path, required=True)
    play.add_argument('--rounds', type=int, default=10, help='paired rounds per layout family')
    play.add_argument('--seed', type=int, default=1)
    play.add_argument('--jobs', type=int, default=int(os.environ.get('OMP_NUM_THREADS', '4').split(',')[0]),
                      help='parallel matches (default: OMP_NUM_THREADS, otherwise 4)')
    play.add_argument('--backend', choices=('python', 'openmp'), default='python')
    play.add_argument('--worker', type=Path, default=DEFAULT_WORKER, help='compiled OpenMP worker executable')
    play.add_argument('--families', nargs='+', choices=FAMILIES, default=FAMILIES)
    play.add_argument('--max-plies', type=int, default=1000)
    actions.add_parser('show').add_argument('path', type=Path)
    actions.add_parser('verify').add_argument('path', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'list':
            for policy in catalog():
                print(f'{policy["id"]:38s} {policy["name"]} [{policy["status"]}]')
        elif args.action == 'run':
            print(json.dumps(run(args.first, args.second, args.out, args.rounds, args.seed,
                                 args.jobs, args.families, args.max_plies, args.backend, args.worker), indent=2))
        elif args.action == 'verify':
            print(json.dumps(verify(args.path), indent=2))
        else:
            with Tournament(args.path) as tournament:
                print(json.dumps(tournament.summary(), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
