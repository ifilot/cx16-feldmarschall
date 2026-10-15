"""Check legacy fatal-exit isolation, schema compatibility and unscored statistics."""
import contextlib
import io
import json
from pathlib import Path
import shlex
import sqlite3
import subprocess
import tempfile
import unittest
import zipfile

from ai_registry import ROOT,build_policy,get_policy
from ai_cycle import score
from arena import play
from tournament_store import Tournament,replay,SCHEMA

BASE=ROOT/'docs/msdos-1990-framework-2026-10-15'
DOS='msdos-1990-v2-normal';PROD='student-guard-v1-normal'

class ErrorIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(BASE/'checks/reference-error.zip') as z:cls.fixture=json.loads(z.read('repro107.json'))
        cls.programs={name:str(build_policy(name)[0]) for name in (DOS,PROD)}
        cls.games=[]
        for side in (0,1,0):
            names=[DOS,PROD] if side==0 else [PROD,DOS]
            commands=[[cls.programs[name],'--difficulty','normal'] for name in names]
            cls.games.append(dict(names=names,commands=commands,setups=cls.fixture['setups'],seed=8585,max_plies=1000,original_dos_setup=[name==DOS for name in names]))
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'plan.json';plan.write_text(json.dumps(dict(threads=1,timeout_ms=10000,reuse_processes=True,jobs=cls.games)))
            result=subprocess.run([str(ROOT/'build/desktop/feldmarschall-tournament-worker'),str(plan)],text=True,capture_output=True,timeout=30)
            if result.returncode:raise RuntimeError(result.stderr+result.stdout)
            events=[json.loads(l) for l in result.stdout.splitlines()]
            cls.native=[e['game'] for e in events if e['event']=='game']
        cls.python=[]
        for game in cls.games:
            cls.python.append(play((game['names'],[shlex.join(c) for c in game['commands']],game['setups'],8585,1000,
                 dict(record_moves=True,original_dos_setup=game['original_dos_setup']))))

    def test_original_failure_is_unscored_and_next_game_runs(self):
        self.assertEqual(len(self.native),3)
        for rows in (self.native,self.python):
            for index in (0,2):
                self.assertEqual(rows[index]['result'],'error')
                self.assertEqual(rows[index]['plies'],177)
                self.assertIn('Unexpected original interrupt 3f',rows[index]['reason'])
                self.assertIsNone(rows[index]['winner'])
            self.assertEqual(rows[1]['reason'],'flag');self.assertEqual(rows[1]['plies'],88)
            self.assertEqual(rows[1]['result'],'blue')
            self.assertEqual(rows[0]['moves'],rows[2]['moves'])

    def test_native_and_python_fault_boundaries_match(self):
        for a,b in zip(self.native,self.python):
            for key in ('moves','result','plies','winner'):self.assertEqual(a[key],b[key])

    def test_new_schema_replay_summary_and_strength_gate(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fault.fmtour'
            meta=dict(participants=[dict(policy=get_policy(n)) for n in (DOS,PROD)],max_plies=1000)
            with Tournament(path,create=True,metadata=meta) as t:
                for i,g in enumerate(self.native):t.add_game(g,i+1,'presets',self.fixture['setups'])
                self.assertEqual(t.db.execute('PRAGMA user_version').fetchone()[0],2)
                report=t.summary();self.assertEqual(report['scored_games'],1);self.assertEqual(report['errors'],2)
                self.assertEqual(report['standings'][DOS]['wins'],1)
                self.assertEqual(report['standings'][DOS]['losses'],0)
                self.assertEqual(report['standings'][DOS]['score'],1.)
                for row in t.games():replay(t.game(row['id']))
                with self.assertRaisesRegex(ValueError,'Unscored engine error'):score(t.games()[0],DOS)
                # The same reader remains compatible with old schema-1 files.
                t.db.execute('PRAGMA user_version=1');t.db.commit()
            with Tournament(path) as t:self.assertEqual(len(t.games()),3)

if __name__=='__main__':unittest.main()
