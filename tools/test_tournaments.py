"""Integration tests for preserved policies, portable storage and legal replays."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zlib

from ai_registry import ROOT, build_policy, catalog, digest, register, restore_tournament
from tournament import run
from tournament_store import Tournament, replay, verify


class Tournaments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = Path(cls.directory.name) / 'test.fmtour'
        with contextlib.redirect_stdout(io.StringIO()):
            run('student-guard-v1-normal', 'original-v1', cls.path, rounds=1, seed=83171,
                jobs=2, families=['fortified', 'decoy'], max_plies=160)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_preserved_identity_and_duplicate_rejection(self):
        ids = [p['id'] for p in catalog()]
        self.assertEqual(len(ids), len(set(ids)))
        for identity in ('original-v1', 'missions-v1-normal', 'student-guard-v1-normal'):
            executable, receipt = build_policy(identity)
            self.assertEqual(subprocess.check_output([str(executable), '--identity'], text=True).strip(), identity)
            self.assertEqual(digest(executable.read_bytes()), receipt['executable_sha256'])
        with self.assertRaisesRegex(ValueError, 'already exists'):
            register(catalog()[0])

    def test_complete_pairs_and_exact_replay(self):
        summary = verify(self.path)
        self.assertEqual(summary['status'], 'complete')
        self.assertEqual(summary['games'], 4)
        with Tournament(self.path) as tournament:
            games = tournament.games()
            for row in games:
                game = tournament.game(row['id'])
                states, events = replay(game)
                self.assertEqual(len(states), game['plies'] + 1)
                self.assertEqual(len(events), game['plies'])
                self.assertEqual(sum(c is not None for c in states[0]), 80)
            self.assertEqual(games[0]['red'], games[1]['blue'])
            for participant in tournament.metadata()['participants']:
                source = participant['policy']['source_sha256']
                self.assertIsNotNone(tournament.db.execute('SELECT 1 FROM artifacts WHERE sha256=?', (source,)).fetchone())

    def test_tournament_is_portable_and_read_only(self):
        copy = Path(self.directory.name) / 'portable.fmtour'
        shutil.copy2(self.path, copy)
        self.assertEqual(verify(copy)['games'], 4)
        with Tournament(copy) as tournament:
            with self.assertRaises(sqlite3.OperationalError):
                tournament.db.execute('DELETE FROM games')
        with self.assertRaises(FileExistsError):
            Tournament(copy, create=True)

    def test_restore_sources_into_empty_catalog_and_reject_conflict(self):
        destination = Path(self.directory.name) / 'registry.json'
        destination.write_text('{"schema": 1, "policies": []}')
        with patch('ai_registry.CATALOG', destination):
            restored = restore_tournament(self.path)
            self.assertEqual(set(restored), {'student-guard-v1-normal', 'original-v1'})
            self.assertEqual(len(catalog()), 2)
            for identity in restored:
                self.assertTrue(build_policy(identity)[0].exists())
            document = json.loads(destination.read_text())
            document['policies'][0]['description'] = 'A conflicting identity'
            destination.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, 'ID conflict'):
                restore_tournament(self.path)

    def test_corrupt_move_and_missing_runtime_rejected(self):
        copy = Path(self.directory.name) / 'corrupt.fmtour'
        shutil.copy2(self.path, copy)
        with contextlib.closing(sqlite3.connect(copy)) as db, db:
            db.execute('UPDATE games SET moves=? WHERE id=1', (zlib.compress(bytes([99, 99])),))
        with self.assertRaises(ValueError):
            verify(copy)
        shutil.copy2(self.path, copy)
        with contextlib.closing(sqlite3.connect(copy)) as db, db:
            db.execute('DELETE FROM artifacts')
        with self.assertRaisesRegex(ValueError, 'Missing participant'):
            verify(copy)

    def test_bad_result_and_mismatched_pair_rejected(self):
        copy = Path(self.directory.name) / 'bad-result.fmtour'
        shutil.copy2(self.path, copy)
        with contextlib.closing(sqlite3.connect(copy)) as db, db:
            db.execute("UPDATE games SET reason='flag', result='red' WHERE id=1")
        with self.assertRaises(ValueError):
            verify(copy)
        shutil.copy2(self.path, copy)
        with contextlib.closing(sqlite3.connect(copy)) as db, db:
            db.execute('UPDATE games SET seed=seed+1 WHERE id=2')
        with self.assertRaisesRegex(ValueError, 'Mismatched paired'):
            verify(copy)

    def test_repeated_seed_reproduces_moves(self):
        copy = Path(self.directory.name) / 'repeat.fmtour'
        with contextlib.redirect_stdout(io.StringIO()):
            run('student-guard-v1-normal', 'original-v1', copy, rounds=1, seed=83171,
                jobs=1, families=['fortified', 'decoy'], max_plies=160)
        with Tournament(self.path) as first, Tournament(copy) as second:
            self.assertEqual(first.games(), second.games())
            for game in first.games():
                self.assertEqual(first.game(game['id']), second.game(game['id']))

    def test_teacher_can_play_through_same_protocol(self):
        copy = Path(self.directory.name) / 'teacher.fmtour'
        with contextlib.redirect_stdout(io.StringIO()):
            run('teacher-rollout-v1-normal', 'missions-v1-normal', copy, rounds=1,
                families=['fortified'], max_plies=2)
        self.assertEqual(verify(copy)['games'], 2)


if __name__ == '__main__':
    unittest.main()
