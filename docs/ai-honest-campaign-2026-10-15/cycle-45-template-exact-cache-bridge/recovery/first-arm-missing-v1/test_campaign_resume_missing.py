import copy
import json
from pathlib import Path
import unittest
import zlib

from campaign_resume_missing import schedule
from tournament_store import Tournament,mirror_setup


class RecoveryScheduleTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'docs/ai-honest-campaign-2026-10-15/cycle-45-template-exact-cache-bridge/student-template-q24-native-v1-normal.fmtour'
        with Tournament(path) as tournament:
            self.metadata=tournament.metadata()
            raw=tournament.db.execute('SELECT data FROM artifacts WHERE sha256=?',(self.metadata['setup_records_sha256'],)).fetchone()[0]
            self.document=json.loads(zlib.decompress(raw))

    def test_complete_ids_and_rotation(self):
        jobs=schedule(self.metadata,self.document)
        self.assertEqual([j['id'] for j in jobs],list(range(1,401)))
        for a,b in zip(jobs[::2],jobs[1::2]):
            self.assertEqual(b['names'],a['names'][::-1])
            self.assertEqual(b['setups'],tuple(mirror_setup(s) for s in a['setups'][::-1]))
            self.assertEqual((a['pair_id'],a['seed']),(b['pair_id'],b['seed']))

    def test_malformed_frozen_schedule_rejected(self):
        for field,value in [('pair_id',2),('family','uniform'),('move_seed',0),('setup_seed',1),('owner_setup','F')]:
            document=copy.deepcopy(self.document)
            document['records'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                schedule(self.metadata,document)
        document=copy.deepcopy(self.document)
        document['records'].pop()
        with self.assertRaises(ValueError):schedule(self.metadata,document)

    def test_privileged_owner_and_changed_owner_rejected(self):
        metadata=copy.deepcopy(self.metadata)
        metadata['participants'][0]['policy']['driver']='msdos1990'
        with self.assertRaises(ValueError):schedule(metadata,self.document)
        document=copy.deepcopy(self.document)
        document['owner']='different-policy'
        with self.assertRaises(ValueError):schedule(self.metadata,document)


if __name__=='__main__':unittest.main()
