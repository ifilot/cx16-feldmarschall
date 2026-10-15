"""Two explicit setup pairing modes, frozen setup evidence and corruption cases."""
import copy
import json
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest

from feldmarschall import Position,random_setup
from tournament_store import Tournament,verify


class SetupStore(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='feld-setup-store-')
        self.path=Path(self.temp.name)/'test.fmtour'
        self.own=random_setup(random.Random(2392001))
        self.opponent=random_setup(random.Random(2392002))
        seed=12345
        self.record=dict(pair_id=1,family='uniform',move_seed=seed,
            setup_seed=((seed*109+0x5e7a)%65535)+1,owner_setup=self.own,opponent_setup=self.opponent)
        self.record['protocol']=['feldmarschall','new red','rules 0','difficulty normal',
                                 'seed '+str(self.record['setup_seed']),'setup','quit']
        self.record['stdout']='id name unit fixture\nok\nsetup '+self.own+'\n'
        self.document=dict(schema='classic-policy-owned-setups-v1',owner='first',opponent='second',records=[self.record])

    def tearDown(self):self.temp.cleanup()

    def fixture(self,mode='policy-owned',document=None,setup_mode_metadata=True,swap_armies=None):
        with Tournament(self.path,create=True) as tournament:
            participants=[]
            for identity in ('first','second'):
                source=tournament.artifact(identity+'/source.zip',(identity+'-source').encode())
                runtime=tournament.artifact(identity+'/engine',(identity+'-engine').encode())
                participants.append(dict(policy=dict(id=identity,source_sha256=source,difficulty='normal'),
                                         runtime_sha256={'engine':runtime}))
            metadata=dict(participants=participants,families=['uniform'],planned_games=2,max_plies=1)
            if setup_mode_metadata:metadata['setup_mode']=mode
            if mode=='policy-owned':
                sha=tournament.artifact('setup/policy-owned-v1.json',json.dumps(document or self.document).encode())
                metadata.update(setup_owner='first',setup_records_artifact='setup/policy-owned-v1.json',setup_records_sha256=sha)
            tournament.set_metadata(metadata)
            if swap_armies is None:swap_armies=mode=='policy-owned'
            for index,names in enumerate((('first','second'),('second','first'))):
                setups=(self.opponent,self.own) if index and swap_armies else (self.own,self.opponent)
                position=Position()
                for army,setup in enumerate(setups):position.place(army,setup)
                move=position.moves(0)[0]
                game=dict(red=names[0],blue=names[1],seed=self.record['move_seed'],result='draw',reason='ply limit',plies=1,moves=[move])
                tournament.add_game(game,1,'uniform',setups)
            tournament.set_metadata(dict(status='complete'))

    def test_policy_owned_armies_follow_participants_and_verify(self):
        self.fixture()
        self.assertEqual(verify(self.path)['scored_games'],2)

    def test_legacy_missing_or_explicit_referee_mode_keeps_physical_armies(self):
        for explicit in (False,True):
            self.fixture('referee',setup_mode_metadata=explicit)
            self.assertEqual(verify(self.path)['scored_games'],2)
            self.path.unlink()

    def test_unknown_mode_and_wrong_pairing_mode_are_rejected(self):
        for mode,swap in (('other',False),('referee',True),('policy-owned',False)):
            self.fixture(mode,swap_armies=swap)
            with self.assertRaises(ValueError):verify(self.path)
            self.path.unlink()

    def test_missing_or_wrong_named_setup_artifact_is_rejected(self):
        for key,value in (('setup_records_sha256','0'*64),('setup_records_artifact','other.json'),('setup_owner','second')):
            self.fixture()
            with sqlite3.connect(self.path) as db:
                db.execute('UPDATE metadata SET value=? WHERE key=?',(json.dumps(value),key))
            with self.assertRaises(ValueError):verify(self.path)
            self.path.unlink()

    def test_hash_valid_artifact_with_corrupted_record_is_rejected(self):
        mutations=[('owner_setup',self.opponent),('opponent_setup',self.own),('move_seed',12346),
                   ('setup_seed',2),('family','decoy'),('pair_id',2),('owner_setup','F'*40),
                   ('protocol',self.record['protocol'][:-1]+['opponent-setup '+self.opponent,'quit']),
                   ('stdout','setup '+self.opponent+'\n')]
        for key,value in mutations:
            document=copy.deepcopy(self.document);document['records'][0][key]=value
            self.fixture(document=document)
            with self.assertRaises(ValueError,msg=key):verify(self.path)
            self.path.unlink()

    def test_duplicate_missing_and_wrong_owner_records_are_rejected(self):
        documents=[]
        for key,value in (('records',[]),('records',[self.record,self.record]),('owner','second'),
                          ('opponent','first'),('schema','wrong')):
            document=copy.deepcopy(self.document);document[key]=value;documents.append(document)
        for document in documents:
            self.fixture(document=document)
            with self.assertRaises(ValueError):verify(self.path)
            self.path.unlink()


if __name__=='__main__':unittest.main()
