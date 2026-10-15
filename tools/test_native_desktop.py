"""Cross-check native/OpenMP tournaments, native replay and the compiled Qt6 GUI."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

from ai_registry import ROOT
from feldmarschall import Position
from tournament import FAMILIES, run
from tournament_store import Tournament, replay, verify

parser = argparse.ArgumentParser()
parser.add_argument('--bin-dir', type=Path, default=ROOT / 'build/desktop')
args, remaining = parser.parse_known_args()
BIN = args.bin_dir.resolve()
WORKER = BIN / 'feldmarschall-tournament-worker'
DESK = BIN / 'feldmarschall-desk'


class NativeDesktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='native-desk-test-')
        cls.paths = {}
        cls.timings = {}
        for name, backend, jobs in [('python', 'python', 1), ('serial', 'openmp', 1), ('parallel', 'openmp', 4)]:
            path = Path(cls.directory.name) / (name + '.fmtour')
            started = time.monotonic()
            with contextlib.redirect_stdout(io.StringIO()):
                run('student-guard-v1-normal', 'original-v1', path, seed=31526,
                    rounds=1, max_plies=1000, jobs=jobs, backend=backend, worker=WORKER)
            cls.timings[name] = time.monotonic() - started
            cls.paths[name] = path

    @classmethod
    def tearDownClass(cls):
        report = ROOT / 'build/desktop/test-report.json'
        report.write_text(json.dumps(dict(timings_seconds=cls.timings,
                                         games_per_comparison=14, seed=31526), indent=2) + '\n')
        cls.directory.cleanup()

    def worker_json(self, option, document):
        path = Path(self.directory.name) / 'request.json'
        path.write_text(json.dumps(document))
        result = subprocess.run([str(WORKER), option, str(path)], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_openmp_is_linked_and_multiple_workers_are_used(self):
        info = json.loads(subprocess.check_output([str(WORKER), '--info'], text=True))
        self.assertEqual(info['backend'], 'openmp')
        self.assertGreaterEqual(info['openmp'], 201511)
        with Tournament(self.paths['parallel']) as tournament:
            metadata = tournament.metadata()
            self.assertEqual(metadata['backend'], 'openmp')
            self.assertEqual(metadata['parallel_execution']['threads'], 4)
            self.assertIn('worker_build', metadata)
        self.assertEqual(verify(self.paths['parallel'])['games'], 14)

    def test_same_games_and_moves_for_python_one_and_four_openmp_threads(self):
        with Tournament(self.paths['python']) as reference:
            for name in ('serial', 'parallel'):
                self.assertEqual(verify(self.paths[name])['games'], 14)
                with Tournament(self.paths[name]) as candidate:
                    self.assertEqual(reference.games(), candidate.games())
                    for row in reference.games():
                        self.assertEqual(reference.game(row['id']), candidate.game(row['id']))

    def test_native_replay_matches_every_python_position(self):
        with Tournament(self.paths['parallel']) as tournament:
            for row in tournament.games():
                game = tournament.game(row['id'])
                expected, _ = replay(game)
                actual = self.worker_json('--replay', game)
                self.assertEqual(actual['states'], expected)

    def test_legal_moves_match_with_history_lakes_and_scout_rays(self):
        with Tournament(self.paths['parallel']) as tournament:
            checks = 0
            for row in tournament.games()[:4]:
                game = tournament.game(row['id'])
                position = Position()
                position.place(0, game['red_setup'])
                position.place(1, game['blue_setup'])
                for ply, (src, dst) in enumerate(game['moves']):
                    if ply % 31 == 0:
                        request = dict(cells=position.cells, side=ply % 2,
                                       shuttle=[position.shuttle[s] for s in range(2)])
                        actual = self.worker_json('--probe', request)
                        self.assertEqual(sorted(map(tuple, actual['moves'])), sorted(position.moves(ply % 2)))
                        checks += 1
                    defender = position.cells[dst]
                    if defender:
                        position.fight(src, dst, position.cells[src][1], defender[1])
                    else:
                        position.move(src, dst)
            self.assertGreater(checks, 10)

    def test_teacher_runs_in_the_parallel_backend(self):
        path = Path(self.directory.name) / 'teacher.fmtour'
        with contextlib.redirect_stdout(io.StringIO()):
            run('teacher-rollout-v1-normal', 'missions-v1-normal', path, rounds=1,
                families=['fortified'], max_plies=2, jobs=2, backend='openmp', worker=WORKER)
        self.assertEqual(verify(path)['games'], 2)

    def test_native_worker_reports_engine_failure(self):
        plan = dict(threads=2, timeout_ms=300, jobs=[dict(names=['bad', 'bad2'], commands=[
            ['/this/engine/does/not/exist'], ['/this/engine/does/not/exist']],
            setups=[''], seed=1, max_plies=5)])
        # Validate the plan first, then exercise process-start failure with legal armies.
        with Tournament(self.paths['serial']) as tournament:
            game = tournament.game(1)
            plan['jobs'][0]['setups'] = [game['red_setup'], game['blue_setup']]
        path = Path(self.directory.name) / 'failure.json'
        path.write_text(json.dumps(plan))
        result = subprocess.run([str(WORKER), str(path)], capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('"event":"error"', result.stdout)

    def test_compiled_gui_opens_legacy_file_and_runs_parallel_tournament(self):
        path = Path(self.directory.name) / 'gui.fmtour'
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
        result = subprocess.run([str(DESK), '--project', str(ROOT), '--smoke-test', str(path),
            '--screenshot', str(ROOT / 'build/native-desk.png'), str(self.paths['python'])],
            env=env, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('Native Qt6 tournament and review passed', result.stdout)
        self.assertEqual(verify(path)['games'], 14)
        with Tournament(path) as tournament:
            self.assertEqual(tournament.metadata()['backend'], 'openmp')


if __name__ == '__main__':
    unittest.main(argv=[__file__, *remaining])
