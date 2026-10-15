"""Frozen private-worker deployment replay, side binding and corrupt artifacts."""
import copy
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zlib

from campaign_dos_setup_runtime import (FrozenDOSSetups,RECORDS_ARTIFACT,_relative,
                                       audit_original_setups)
from feldmarschall import random_setup
from tournament_store import Tournament,mirror_setup


class FrozenDeploymentRuntime(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='dos-runtime-test-')
        self.folder=Path(self.temp.name);self.path=self.folder/'test.fmtour'

    def tearDown(self):self.temp.cleanup()

    def metadata_update(self, **values):
        # Deliberate corruption of a temporary test fixture; public readers stay readonly.
        with sqlite3.connect(self.path) as db:
            db.executemany('UPDATE metadata SET value=? WHERE key=?',
                           [(json.dumps(value),key) for key,value in values.items()])
            db.executemany('INSERT OR IGNORE INTO metadata VALUES (?,?)',
                           [(key,json.dumps(value)) for key,value in values.items()])

    def fixture(self,mode='referee'):
        with Tournament(self.path,create=True,metadata=dict(families=['original-dos'],planned_games=2,
                setup_mode=mode,setup_owner='candidate',participants=[dict(policy=dict(id='candidate')),
                    dict(policy=dict(id='dos',driver='msdos1990'))])) as tournament:
            records=[]
            with FrozenDOSSetups(tournament,self.folder/'working') as generator:
                # Request only seed+level; source metadata is committed already.
                self.assertIn('original_dos_setup_runtime',tournament.metadata())
                for slot,seed in (('A',1),('B',2)):
                    setup,audit=generator.generate(seed,3)
                    records.append(dict(pair_id=1,slot=slot,used_in_games=mode=='referee' or slot=='B',
                                        setup=setup,private_seed=seed,audit=audit))
                with self.assertRaises(ValueError):generator.generate(True)
                self.assertEqual(generator.generate(1,3),(records[0]['setup'],records[0]['audit']))
            a,b=(row['setup'] for row in records)
            if mode in ('policy-owned','policy-owned-rotated-v1'):a=random_setup(random.Random(401001))
            for index,(red,blue) in enumerate((('candidate','dos'),('dos','candidate'))):
                setups=(a,b) if mode=='referee' or index==0 else (b,a)
                if mode=='policy-owned-rotated-v1' and index:setups=tuple(map(mirror_setup,setups))
                # Legal empty prefixes remain unscored engine-error records.
                game=dict(red=red,blue=blue,seed=1234,result='error',reason='engine error',plies=0,moves=[])
                tournament.add_game(game,1,'original-dos',setups)
            digest=tournament.artifact(RECORDS_ARTIFACT,json.dumps(dict(schema='original-dos-setups-v1',records=records)).encode())
            tournament.set_metadata(dict(status='complete',original_dos_setup_records_artifact=RECORDS_ARTIFACT,
                                         original_dos_setup_records_sha256=digest))
        return records

    def modify_records(self,mutation):
        with Tournament(self.path,create=False) as tournament:
            metadata=tournament.metadata();old=metadata['original_dos_setup_records_sha256']
            row=tournament.db.execute('SELECT data FROM artifacts WHERE sha256=?',(old,)).fetchone()
            document=json.loads(zlib.decompress(row['data']))
        mutation(document)
        data=json.dumps(document).encode();digest=hashlib.sha256(data).hexdigest()
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR REPLACE INTO artifacts VALUES (?,?,?)',(digest,RECORDS_ARTIFACT,zlib.compress(data)))
            db.execute('UPDATE metadata SET value=? WHERE key=?',(json.dumps(digest),'original_dos_setup_records_sha256'))

    def test_referee_two_slots_replay_only_frozen_bundle_and_preserve_prefixes(self):
        self.fixture();before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with patch('campaign_dos_setup_runtime.build_policy',side_effect=AssertionError('no live runtime reads during audit')):
            report=audit_original_setups(self.path)
        self.assertTrue(report['passed']);self.assertEqual(report['regenerated_records'],2)
        self.assertEqual(report['matched_game_armies'],4)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)

    def test_policy_owned_overwrites_a_and_b_follows_dos_identity(self):
        self.fixture('policy-owned');report=audit_original_setups(self.path)
        self.assertEqual(report['regenerated_records'],2);self.assertEqual(report['matched_game_armies'],2)
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE games SET red_setup=blue_setup WHERE red=?',('dos',))
        with self.assertRaisesRegex(ValueError,'army differs'):audit_original_setups(self.path)

    def test_rotated_original_b_matches_blue_raw_and_red_reflection(self):
        self.fixture('policy-owned-rotated-v1')
        self.assertEqual(audit_original_setups(self.path)['matched_game_armies'],2)
        with sqlite3.connect(self.path) as db:
            # Rewrite the red DOS army back to the old unrotated convention.
            raw=db.execute('SELECT blue_setup FROM games WHERE red=?',('candidate',)).fetchone()[0]
            db.execute('UPDATE games SET red_setup=? WHERE red=?',(raw,'dos'))
        with self.assertRaisesRegex(ValueError,'army differs'):audit_original_setups(self.path)

    def test_honest_opponent_uses_original_army_only_with_explicit_context(self):
        self.fixture('policy-owned-rotated-v1')
        with Tournament(self.path) as tournament:
            participants=tournament.metadata()['participants']
            participants[1]['policy']=dict(id='dos',defines=[])
        self.metadata_update(participants=participants)
        with self.assertRaisesRegex(ValueError,'explicit honest opponent control'):
            audit_original_setups(self.path)
        self.metadata_update(original_dos_setup_move_context='honest-opponent-control-v1')
        self.assertEqual(audit_original_setups(self.path)['matched_game_armies'],2)
        with Tournament(self.path) as tournament:
            participants=tournament.metadata()['participants']
            participants[1]['policy']['defines']=['AI_DIAGNOSTIC_TRUTH']
        self.metadata_update(participants=participants)
        with self.assertRaisesRegex(ValueError,'explicit honest opponent control'):
            audit_original_setups(self.path)

    def test_dos_driver_cannot_be_relabelled_an_honest_control(self):
        self.fixture('policy-owned-rotated-v1')
        self.metadata_update(original_dos_setup_move_context='honest-opponent-control-v1')
        with self.assertRaisesRegex(ValueError,'context mismatch'):audit_original_setups(self.path)

    def test_hash_valid_tampered_seed_or_audit_rejected_by_regeneration(self):
        self.fixture()
        self.modify_records(lambda document:document['records'][0].update(private_seed=3))
        with self.assertRaisesRegex(ValueError,'regeneration mismatch'):audit_original_setups(self.path)

    def test_runtime_blob_corruption_rejected_before_worker_execution(self):
        self.fixture()
        with sqlite3.connect(self.path) as db:
            metadata=json.loads(db.execute("SELECT value FROM metadata WHERE key='original_dos_setup_runtime'").fetchone()[0])
            digest=metadata['files']['generator.py']
            db.execute('UPDATE artifacts SET data=? WHERE sha256=?',(zlib.compress(b'corrupt'),digest))
        with self.assertRaisesRegex(ValueError,'hash mismatch'):audit_original_setups(self.path)

    def test_unsafe_runtime_paths_and_missing_original_slots_rejected(self):
        for path in ('../escape','/absolute','a/../../escape','C:bad','a\\bad'):
            with self.assertRaises(ValueError):_relative(path)
        self.fixture()
        self.modify_records(lambda document:document['records'].pop())
        with self.assertRaisesRegex(ValueError,'missing setup slot'):audit_original_setups(self.path)


if __name__=='__main__':unittest.main()
