"""Frozen executable setup replay, transcripts, and source/path corruption."""
import json
from pathlib import Path
import random
import sqlite3
import subprocess
import tempfile
import unittest

from audit_policy_setups import audit
from feldmarschall import GLYPHS, COUNTS, Position, random_setup
from tournament_store import Tournament


class SetupAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='test-frozen-setup-audit-')
        self.directory = Path(self.temp.name)
        self.path = self.directory/'fixture.fmtour'

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, variable_stderr=False, change=None, unsafe_runtime=False):
        pool = ''.join(g*n for g, n in zip(GLYPHS, COUNTS))
        engine = self.directory/'engine'
        (self.directory/'assets').mkdir(exist_ok=True)
        (self.directory/'assets/pool.txt').write_text(pool)
        program = '''#!/usr/bin/env python3
import os, pathlib, random, sys
assert sys.argv[1:]==['--difficulty','normal']
lines=sys.stdin.read().splitlines()
assert len(lines)==7
assert lines[:4]==['feldmarschall','new red','rules 0','difficulty normal']
assert lines[4].startswith('seed ') and lines[5:]==['setup','quit']
seed=int(lines[4][5:])
pool=list((pathlib.Path(__file__).parent/'assets/pool.txt').read_text())
random.Random(seed).shuffle(pool)
print('id name frozen setup fixture\\nok')
print('setup '+''.join(pool))
print('pid='+str(os.getpid()) if VARIABLE else 'frozen setup fixture',file=sys.stderr)
'''.replace('VARIABLE', repr(variable_stderr))
        engine.write_text(program)
        engine.chmod(0o755)
        opponent = random_setup(random.Random(3333))
        records = []
        for pair, move_seed in enumerate((12345, 22222), 1):
            setup_seed = (move_seed*109+0x5e7a) % 65535+1
            protocol = ['feldmarschall', 'new red', 'rules 0', 'difficulty normal',
                        'seed '+str(setup_seed), 'setup', 'quit']
            completed = subprocess.run([str(engine), '--difficulty', 'normal'],
                                       input='\n'.join(protocol)+'\n', capture_output=True, text=True, check=True)
            setup = next(line[6:] for line in completed.stdout.splitlines() if line.startswith('setup '))
            records.append(dict(pair_id=pair, family='uniform', move_seed=move_seed,
                                setup_seed=setup_seed, owner_setup=setup, opponent_setup=opponent,
                                protocol=protocol, stdout=completed.stdout, stderr=completed.stderr))
        if change:
            change(records)
        document = dict(schema='classic-policy-owned-setups-v1', owner='first', opponent='second', records=records)
        with Tournament(self.path, create=True) as tournament:
            participants = []
            for identity in ('first', 'second'):
                source = tournament.artifact(identity+'/source.zip', (identity+' source').encode())
                runtime = tournament.artifact(identity+'/engine', program.encode() if identity == 'first' else b'inert second runtime')
                runtimes = {'engine': runtime}
                if identity == 'first':
                    runtimes['assets/pool.txt'] = tournament.artifact(identity+'/assets/pool.txt', pool.encode())
                    if unsafe_runtime:
                        runtimes['../escape'] = runtime
                participants.append(dict(policy=dict(id=identity, source_sha256=source, difficulty='normal'),
                                         runtime_sha256=runtimes))
            document_sha = tournament.artifact('setup/policy-owned-v1.json', json.dumps(document).encode())
            setup_sources = {name: tournament.artifact('setup/'+name, (name+' frozen source').encode())
                             for name in ('tournament.py', 'arena.py', 'feldmarschall.py')}
            tournament.set_metadata(dict(participants=participants, families=['uniform'], planned_games=4,
                                         max_plies=1, setup_mode='policy-owned', setup_owner='first',
                                         setup_records_artifact='setup/policy-owned-v1.json',
                                         setup_records_sha256=document_sha, setup_source_sha256=setup_sources))
            for record in records:
                for index, names in enumerate((('first', 'second'), ('second', 'first'))):
                    setups = ((record['owner_setup'], opponent) if index == 0 else (opponent, record['owner_setup']))
                    position = Position()
                    for army, setup in enumerate(setups):
                        position.place(army, setup)
                    game = dict(red=names[0], blue=names[1], seed=record['move_seed'],
                                result='draw', reason='ply limit', plies=1, moves=[position.moves(0)[0]])
                    tournament.add_game(game, record['pair_id'], 'uniform', setups)
            tournament.set_metadata(dict(status='complete'))

    def test_replays_every_record_from_frozen_runtime_with_nested_asset(self):
        self.fixture()
        # Destroy the live fixture executable and asset. The audit must use the
        # embedded runtime and must not use registry/worktree policy binaries.
        (self.directory/'engine').unlink()
        (self.directory/'assets/pool.txt').unlink()
        result = audit(self.path)
        self.assertTrue(result['passed'])
        self.assertEqual(result['records'], 2)
        self.assertEqual(result['verified_games'], 4)
        self.assertTrue(result['all_streams_repeatable'])
        self.assertTrue(result['no_opponent_input'])
        for row in result['records_audited']:
            self.assertTrue(row['setup_matches'])
            self.assertTrue(row['streams']['stdout']['exact_recorded_match'])
            self.assertTrue(row['streams']['stderr']['exact_recorded_match'])

    def test_wrong_frozen_setup_is_rejected_despite_valid_saved_armies(self):
        replacement = random_setup(random.Random(8888))
        def change(records):
            records[0]['owner_setup'] = replacement
            records[0]['stdout'] = 'id name frozen setup fixture\nok\nsetup '+replacement+'\n'
        self.fixture(change=change)
        with self.assertRaisesRegex(ValueError, 'setup replay mismatch'):
            audit(self.path)

    def test_repeatable_stdout_or_stderr_mismatch_fails(self):
        for stream in ('stdout', 'stderr'):
            with self.subTest(stream=stream):
                self.fixture(change=lambda records: records[0].__setitem__(stream, 'extra\n'+records[0][stream]))
                with self.assertRaisesRegex(ValueError, 'Repeatable '+stream):
                    audit(self.path)
                self.path.unlink()

    def test_variable_stderr_is_reported_without_exact_claim(self):
        self.fixture(variable_stderr=True)
        result = audit(self.path)
        self.assertFalse(result['all_streams_repeatable'])
        self.assertTrue(all(row['streams']['stderr']['exact_recorded_match'] is None
                            for row in result['records_audited']))
        self.assertTrue(all(row['streams']['stdout']['exact_recorded_match'] for row in result['records_audited']))

    def test_missing_setup_source_artifact_fails(self):
        self.fixture()
        with sqlite3.connect(self.path) as db:
            value = json.loads(db.execute('SELECT value FROM metadata WHERE key="setup_source_sha256"').fetchone()[0])
            value['tournament.py'] = '0'*64
            db.execute('UPDATE metadata SET value=? WHERE key="setup_source_sha256"', (json.dumps(value),))
        with self.assertRaisesRegex(ValueError, 'Missing setup selection source artifact'):
            audit(self.path)

    def test_extra_enemy_input_and_missing_protocol_are_rejected(self):
        for missing in (False, True):
            def change(records):
                if missing:
                    records[0].pop('protocol')
                else:
                    records[0]['protocol'].insert(-1, 'opponent-setup '+records[0]['opponent_setup'])
            self.fixture(change=change)
            with self.assertRaisesRegex(ValueError, '[Pp]rotocol'):
                audit(self.path)
            self.path.unlink()

    def test_runtime_path_cannot_escape_temporary_directory(self):
        self.fixture(unsafe_runtime=True)
        with self.assertRaisesRegex(ValueError, 'Unsafe runtime artifact path'):
            audit(self.path)


if __name__ == '__main__':
    unittest.main()
