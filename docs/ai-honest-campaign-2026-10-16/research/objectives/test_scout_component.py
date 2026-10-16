import shlex,tempfile,unittest
from pathlib import Path
from scout_component import build,ROOT,Component
from ai_registry import get_policy
from feldmarschall import Engine,LAKES

class ComponentFixtures(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.directory=tempfile.TemporaryDirectory(prefix='scout-component-tests-');cls.observer,_=build(Path(cls.directory.name),get_policy('student-fortress-template-flag-bomb-v1-normal'))
 @classmethod
 def tearDownClass(cls):cls.directory.cleanup()
 def fixture(self,scout_revealed=True,actor=1):
  engine=Engine(shlex.quote(str(self.observer)));engine.send('new red');engine.send('rules 0');engine.send('difficulty normal')
  cells=[254 if s in LAKES else 255 for s in range(100)];cells[74]=actor;cells[44]=16|8|(32 if scout_revealed else 0);cells[99]=11
  engine.ask('position 0 '+'00'*12+' '+bytes(cells).hex()+' ffffffff0000','positionok')
  return engine
 def mapping(self,actor=74,target=44):
  values=[255]*100;values[actor]=target;return bytes(values).hex()
 def test_only_public_ordinary_actor_to_disclosed_scout_accepted(self):
  engine=self.fixture()
  try:engine.ask('component-veto '+self.mapping(),'component-vetook')
  finally:engine.close()
  for options in(dict(scout_revealed=False),dict(actor=8)):
   engine=self.fixture(**options)
   try:
    with self.assertRaises(RuntimeError):engine.ask('component-veto '+self.mapping(),'component-vetook')
   finally:engine.close()
 def test_out_of_range_target_and_optional_rules_rejected(self):
  engine=self.fixture()
  try:
   with self.assertRaises(RuntimeError):engine.ask('component-veto '+self.mapping(target=200),'component-vetook')
   engine.send('rules 1')
   with self.assertRaises(RuntimeError):engine.ask('component-veto '+self.mapping(),'component-vetook')
  finally:engine.close()
 def test_snapshot_restore_choice_and_rng_parity(self):
  engine=self.fixture()
  try:
   engine.send('seed 991');engine.ask('component-save','component-saveok');before=engine.ask('strategy','strategy');rng=engine.ask('component-rng','component-rng')
   first=engine.ask('go','move');after=engine.ask('strategy','strategy');afterrng=engine.ask('component-rng','component-rng')
   engine.ask('component-restore','component-restoreok');self.assertEqual(engine.ask('strategy','strategy'),before);self.assertEqual(engine.ask('component-rng','component-rng'),rng)
   engine.ask('component-veto '+self.mapping(),'component-vetook');engine.ask('go','move');engine.ask('component-restore','component-restoreok')
   self.assertEqual(engine.ask('go','move'),first);self.assertEqual(engine.ask('strategy','strategy'),after);self.assertEqual(engine.ask('component-rng','component-rng'),afterrng)
  finally:engine.close()
if __name__=='__main__':unittest.main()
