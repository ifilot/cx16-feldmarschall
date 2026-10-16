"""Corpus disjointness, generator structure and portable tournament provenance."""
import contextlib
import copy
import io
import json
from pathlib import Path
import random
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

from feldmarschall import ROOT, setup_neighbors
from setup_dataset import (DEVELOPMENT, HELD_OUT, LANES, SPLITS, audit_documents,
    build_dataset, generate_army, load_dataset, playable, reflected,
    select_records, validate_bundle)
from tournament import run
from tournament_store import Tournament, replay, verify


class SetupDatasets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='setup-dataset-test-')
        cls.root = Path(cls.temp.name)
        cls.dataset = cls.root/'suite'
        build_dataset(cls.dataset, development_pairs=2, validation_pairs=2)
        cls.bundle = load_dataset(cls.dataset)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_generation_is_byte_reproducible_and_never_overwrites(self):
        other = self.root/'reproduced'
        build_dataset(other, development_pairs=2, validation_pairs=2)
        for path in self.dataset.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (other/path.relative_to(self.dataset)).read_bytes())
        with self.assertRaises(FileExistsError):
            build_dataset(other, development_pairs=2, validation_pairs=2)

    def test_full_frozen_corpus(self):
        bundle = load_dataset(ROOT/'tests/datasets/classic-generalization-v1')
        self.assertEqual(bundle['coverage']['pairs'], 1920)
        self.assertEqual(bundle['coverage']['unique_armies_including_reflection_check'], 3840)
        self.assertEqual(bundle['coverage']['cross_split_duplicate_or_mirror_count'], 0)
        for split in SPLITS:
            rows = bundle['coverage']['splits'][split].values()
            self.assertTrue(all(row['minimum_legacy_distance'] >= 12 for row in rows))
            # Each partition covers every flag row and column across its families.
            self.assertTrue(all(sum(r['flag_rows'][i] for r in rows) > 0 for i in range(4)))
            self.assertTrue(all(sum(r['flag_columns'][i] for r in rows) > 0 for i in range(10)))

    def test_new_generator_structures_and_mobility(self):
        for family in HELD_OUT:
            for seed in range(80):
                army = generate_army(family, random.Random(seed))
                self.assertTrue(playable(army), (family, seed))
                flag = army.index('F')
                if family == 'interior-shell-v1': self.assertIn(flag//10, (1, 2))
                if family == 'flank-flag-v1': self.assertIn(flag % 10, (0, 1, 8, 9))
                if family == 'double-decoy-v1':
                    self.assertLess(flag, 20)
                    decoys = [i for i in range(30, 40) if army[i] not in 'BF'
                              and all(army[n] == 'B' for n in setup_neighbors(i))]
                    self.assertEqual(len(decoys), 2)
                if family == 'front-fence-v1':
                    self.assertEqual(army[:10].count('B'), 6)
                    self.assertGreaterEqual(sum(army[i] != 'B' for i in LANES), 2)
                if family == 'lane-vanguard-v1':
                    self.assertEqual(sorted(army[i] for i in LANES), sorted('999988'))

    def test_integrity_inventory_mirrors_and_holdout_boundaries(self):
        bundle = self.bundle
        broken = dict(bundle['files']); broken['development.json'] += b' '
        with self.assertRaisesRegex(ValueError, 'integrity'):
            validate_bundle(bundle['manifest'], broken)
        manifest, docs = copy.deepcopy(bundle['manifest']), copy.deepcopy(bundle['documents'])
        exclusions = json.loads(bundle['files']['exclusions.json'])
        docs['seed-validation']['records'][0]['army_a'] = reflected(docs['development']['records'][0]['army_a'])
        with self.assertRaisesRegex(ValueError, 'Duplicate or mirrored'):
            audit_documents(manifest, docs, exclusions)
        docs = copy.deepcopy(bundle['documents'])
        docs['development']['records'][0]['army_a'] = 'F'*40
        with self.assertRaisesRegex(ValueError, 'Invalid or immobile'):
            audit_documents(manifest, docs, exclusions)
        manifest['splits']['generator-holdout']['families'][0] = DEVELOPMENT[0]
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            audit_documents(manifest, bundle['documents'], exclusions)
        with self.assertRaisesRegex(ValueError, 'never wrap'):
            select_records(bundle, 'development', 2, 1)

    def test_runner_rejects_incompatible_requests_before_creating_output(self):
        output = self.root/'invalid.fmtour'
        for kwargs in (dict(setup_mode='policy-owned'), dict(dataset_offset=2), dict(families=['uniform'])):
            with self.assertRaises(ValueError):
                run('student-guard-v1-normal', 'original-v1', output, rounds=1,
                    setup_dataset=self.dataset, **kwargs)
            self.assertFalse(output.exists())

    def test_portable_python_and_openmp_matches_and_tampering(self):
        paths = []
        for backend in ('python', 'openmp'):
            path = self.root/(backend+'.fmtour'); paths.append(path)
            with contextlib.redirect_stdout(io.StringIO()):
                run('student-guard-v1-normal', 'original-v1', path, rounds=1,
                    seed=20261016, jobs=2, max_plies=40, backend=backend,
                    setup_dataset=self.dataset, dataset_offset=1)
            self.assertEqual(verify(path)['games'], 12)
        selected = select_records(self.bundle, 'development', 1, 1)
        with Tournament(paths[0]) as python, Tournament(paths[1]) as native:
            for row in python.games():
                game = python.game(row['id'])
                self.assertEqual(game, native.game(row['id']))
                record = selected[game['pair_id']-1]
                self.assertEqual((game['red_setup'], game['blue_setup']), (record['army_a'], record['army_b']))
                request = self.root/'replay.json'; request.write_text(json.dumps(game))
                result = subprocess.check_output([str(ROOT/'build/desktop/feldmarschall-tournament-worker'),
                                                  '--replay', str(request)], text=True)
                self.assertEqual(json.loads(result)['states'], replay(game)[0])
        # Verification relies only on embedded corpus bytes, not its source directory.
        hidden = self.root/'hidden-suite'; self.dataset.rename(hidden)
        try:
            self.assertEqual(verify(paths[0])['games'], 12)
        finally:
            hidden.rename(self.dataset)
        corrupt = self.root/'corrupt.fmtour'; shutil.copyfile(paths[0], corrupt)
        with sqlite3.connect(corrupt) as db:
            pin = json.loads(db.execute("SELECT value FROM metadata WHERE key='setup_dataset'").fetchone()[0])
            pin['record_ids'][0] = 'wrong-record'
            db.execute("UPDATE metadata SET value=? WHERE key='setup_dataset'", (json.dumps(pin),))
        with self.assertRaisesRegex(ValueError, 'cohort mismatch'):
            verify(corrupt)
        shutil.copyfile(paths[0], corrupt)
        with sqlite3.connect(corrupt) as db:
            # Even changing both halves consistently must fail dataset verification.
            db.execute('UPDATE games SET red_setup=blue_setup WHERE pair_id=1')
        with self.assertRaisesRegex(ValueError, 'frozen dataset'):
            verify(corrupt)


if __name__ == '__main__':
    unittest.main()
