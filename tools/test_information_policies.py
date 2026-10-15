"""Frozen information policies: fair transport and Python/native pool parity."""
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

from ai_registry import build_policy, get_policy, receives_opponent_setup
from tournament import run
from tournament_store import Tournament, verify

POLICIES=('teacher-info-lifetime-v1-normal','teacher-info-corridor-v1-normal','teacher-info-followthrough-v1-normal')


class FrozenInformationPolicies(unittest.TestCase):
    def test_no_privileged_transport_or_observer_command(self):
        for identity in POLICIES:
            program,receipt=build_policy(identity)
            self.assertFalse(receives_opponent_setup(receipt['policy']))
            self.assertNotIn('AI_DIAGNOSTIC_TRUTH',receipt['policy']['defines'])
            result=subprocess.run([str(program)],input='opponent-setup rejected\n',capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('rejects opponent setup',result.stderr)
            result=subprocess.run([str(program.parent/'observer')],input='diagnostic-truth\nquit\n',capture_output=True,text=True,check=True)
            self.assertIn('error unknown command',result.stdout)

    def test_frozen_sources_python_native_and_reused_processes_agree(self):
        with tempfile.TemporaryDirectory() as temp:
            for identity in POLICIES:
                paths=[]
                for name,backend,reuse in (('python','python',None),('native','openmp',False),('pooled','openmp',True)):
                    path=Path(temp)/(identity+'-'+name+'.fmtour');paths.append(path)
                    with contextlib.redirect_stdout(io.StringIO()):
                        run(identity,'teacher-context-v1-normal',path,rounds=1,seed=1950099,
                            jobs=1,families=['uniform'],max_plies=16,backend=backend,reuse_processes=reuse)
                    self.assertEqual(verify(path)['errors'],0)
                with Tournament(paths[0]) as reference:
                    for path in paths[1:]:
                        with Tournament(path) as candidate:
                            for row in reference.games():self.assertEqual(reference.game(row['id']),candidate.game(row['id']))


if __name__=='__main__':unittest.main()
