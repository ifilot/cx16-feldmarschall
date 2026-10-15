"""Frozen-only portable qualification for cycles20/21 honest public beliefs."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from ai_registry import ROOT,build_policy,get_policy,receives_opponent_setup
from feldmarschall import Engine,Position,parse_square
from information_strategy_cycle import digest
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

BASE=ROOT/'docs/ai-honest-campaign-2026-10-15'

# Executed with only a copied frozen runtime on sys.path; cwd is outside checkout.
AUDIT=r'''
import copy,json,sys
from pathlib import Path
from unittest.mock import patch
runtime=Path(sys.argv[1]);sys.path.insert(0,str(runtime))
request=json.load(sys.stdin);spec=request['spec'];kind=spec.get('driver');army=request['army']
from feldmarschall import ROOT
assert not str(ROOT).startswith(request['checkout'])
if kind=='teacher':
 from teacher_bot import TeacherBot
 kwargs={};args=spec['driver_args']
 if '--objective-belief-model' in args:
  from campaign_inverse_objectives import ObjectiveSampler
  kwargs['public_belief']=ObjectiveSampler.load(runtime/Path(spec['objective_belief_model']).name)
 elif '--template-prior' in args:
  from campaign_template_beliefs import TemplateMixtureBeliefs
  kwargs['public_belief']=TemplateMixtureBeliefs()
 elif '--world-sampling' in args:kwargs['world_sampling']=args[args.index('--world-sampling')+1]
 def factory():return TeacherBot(runtime/'observer',runtime/'teacher',samples=8,depth=4,blend='correction',strategic=True,context=True,**kwargs)
else:
 if kind=='native-template':
  from campaign_native_template import NativeTemplateBot
  def factory():return NativeTemplateBot(runtime/'observer')
 else:
  from campaign_native_beliefs import NativeBeliefBot
  def factory():return NativeBeliefBot(runtime/'observer',runtime/Path(spec['joint_belief_model']).name,mode='counts')
reports=[]
for mutate in (False,True):
 # Fresh public tracker per repeat, including constructor kwargs for teachers.
 if kind=='teacher' and 'public_belief' in kwargs:
  if '--objective-belief-model' in spec['driver_args']:kwargs['public_belief']=ObjectiveSampler.load(runtime/Path(spec['objective_belief_model']).name)
  else:kwargs['public_belief']=TemplateMixtureBeliefs()
 bot=factory()
 try:
  if kind=='teacher':bot.rng.seed(817)
  for line in request['commands']:
   words=line.split()
   if kind=='teacher':
    if bot.public_belief is not None:bot.public_belief.observe(words)
    bot.observer.send(line)
   else:bot.observe(words)
  original=bot.observer.ask
  def ask(line,prefix):
   result=original(line,prefix)
   if mutate and line=='public':
    side,board,lost,shuttle=result.split();cells=list(bytes.fromhex(board))
    for sq,c in enumerate(cells):
     if c<254 and bool(c&16)!=bool(army) and not c&32:cells[sq]=(c&240)|(sq%12)
    return ' '.join((side,bytes(cells).hex(),lost,shuttle))
   return result
  with patch.object(bot.observer,'ask',side_effect=ask):move=bot.choose()
  report=copy.deepcopy(bot.last_report);report.pop('elapsed_seconds',None)
  reports.append(dict(move=move,report=report))
 finally:bot.close()
assert reports[0]==reports[1], 'Concealed enemy nibbles changed chosen move/report'
print(json.dumps(dict(passed=True,army=army,move=reports[0]['move'],report=reports[0]['report'],frozen_module_root=str(ROOT))))
'''


class PortableQualification:
    @classmethod
    def setUpClass(cls):
        cls.directory=BASE/cls.cycle
        cls.evidence={'test_source_sha256':digest(Path(__file__)),'scope':'Portable frozen-runtime mechanism qualification, not strength evaluation.','policies':{}}
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:cls.game=saved.game(9)
        cls.states,_=replay(cls.game);cls.events=public_events(cls.game,cls.states)
    @classmethod
    def tearDownClass(cls):
        (cls.directory/'portable-qualification.json').write_text(json.dumps(cls.evidence,indent=2)+'\n')
    def copied(self,identity,tmp):
        program,receipt=build_policy(identity);portable=Path(tmp)/'runtime';shutil.copytree(program.parent,portable)
        return portable/program.name,receipt
    def test_frozen_integrity_receipts_and_models(self):
        frozen=json.loads((self.directory/'frozen-policies.json').read_text())
        for identity in self.policies:
            spec=get_policy(identity);self.assertEqual(spec,frozen[identity]);self.assertFalse(receives_opponent_setup(spec))
            program,receipt=build_policy(identity);self.assertEqual(receipt['policy'],spec)
            self.assertEqual(digest(ROOT/spec['archive']),spec['source_sha256'])
            self.assertEqual(digest(program),receipt['executable_sha256'])
            with zipfile.ZipFile(ROOT/spec['archive']) as archive:
                for name,sha in receipt['runtime_sha256'].items():
                    self.assertEqual(digest(program.parent/name),sha)
                    if name.endswith('.py'):self.assertEqual(archive.read('tools/'+name),(program.parent/name).read_bytes())
                for asset in spec.get('asset_files',[]):self.assertEqual(archive.read(asset),(program.parent/Path(asset).name).read_bytes())
            self.evidence['policies'].setdefault(identity,{})['integrity']=dict(source_sha256=spec['source_sha256'],runtime_sha256=receipt['runtime_sha256'],passed=True)
    def test_portable_launcher_bare_setup_go_and_public_history(self):
        for identity in self.policies:
            records=[]
            for army in (0,1):
                with tempfile.TemporaryDirectory(prefix='frozen-public-launcher-') as tmp:
                    program,_=self.copied(identity,tmp)
                    actual=subprocess.run([str(program),'--identity'],cwd=tmp,text=True,capture_output=True,check=True)
                    self.assertEqual(actual.stdout.strip(),identity)
                    with patch('feldmarschall.ROOT',Path(tmp)):bot=Engine(shlex.quote(str(program)))
                    try:
                        for line in ['new '+('red','blue')[army],'rules 0','difficulty normal','seed 817']:bot.send(line)
                        generated=bot.ask('setup','setup');first=tuple(map(parse_square,bot.ask('go','move').split()))
                        position=Position();position.place(army,generated);position.place(1-army,self.game[('blue_setup','red_setup')[army]])
                        self.assertIn(first,position.moves(army))
                        for line in ['new '+('red','blue')[army],'seed 817','setup '+self.game[('red_setup','blue_setup')[army]]]+self.events[:80]:bot.send(line)
                        selected=tuple(map(parse_square,bot.ask('go','move').split()));position.cells=copy_cells=self.states[80][:]
                        self.assertIn(selected,position.moves(army))
                        public=bot.ask('public','public').split();self.assertEqual(int(public[0]),army)
                        hidden=sum(1 for c in bytes.fromhex(public[1]) if c<254 and bool(c&16)!=bool(army) and not c&32)
                        self.assertTrue(all(c&15==12 for c in bytes.fromhex(public[1]) if c<254 and bool(c&16)!=bool(army) and not c&32))
                        records.append(dict(army=army,identity_ok=True,bare_setup_legal_move=list(first),public_prefix_events=80,legal_prefix_move=list(selected),concealed_enemy_pieces=hidden,passed=True))
                    finally:bot.close()
            self.evidence['policies'].setdefault(identity,{})['portable_launchers']=records
    def test_frozen_only_concealed_rank_invariance_after_public_history(self):
        for identity in self.policies:
            records=[]
            for army in (0,1):
                with tempfile.TemporaryDirectory(prefix='frozen-public-secrecy-') as tmp:
                    program,_=self.copied(identity,tmp)
                    request=dict(spec=get_policy(identity),army=army,checkout=str(ROOT),commands=[
                        'new '+('red','blue')[army],'rules 0','difficulty normal','seed 817',
                        'setup '+self.game[('red_setup','blue_setup')[army]]]+self.events[:80])
                    result=subprocess.run([sys.executable,'-I','-c',AUDIT,str(program.parent)],input=json.dumps(request),cwd=tmp,text=True,capture_output=True)
                    self.assertEqual(result.returncode,0,result.stderr);records.append(json.loads(result.stdout))
            self.evidence['policies'].setdefault(identity,{})['concealed_rank_invariance']=records

class Cycle20PortableTests(PortableQualification,unittest.TestCase):
    cycle='cycle-20-own-objective-beliefs'
    policies=('teacher-own-flag-motion-v1-normal','teacher-mirrored-flag-motion-v1-normal')

class Cycle21PortableTests(PortableQualification,unittest.TestCase):
    cycle='cycle-21-template-opening-prior'
    policies=('student-validated-counts-v1-normal','student-template-flag-bomb-v1-normal',
              'teacher-validated-uniform-v1-normal','teacher-template-opening-v1-normal')

if __name__=='__main__':unittest.main()
