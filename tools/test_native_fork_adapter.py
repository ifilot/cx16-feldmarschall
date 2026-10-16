"""Production public-event keys for the fork continuation, Classic only."""
from pathlib import Path
import shlex,subprocess,tempfile,unittest
from ai_registry import ROOT,get_policy
from campaign_mobile_capture import (_fork_successors,_fork_public_key,_fork_enemy_lost,_fork_shuttle)
from campaign_native_mobile import MobileCaptureBot
from campaign_belief_values import worths
from feldmarschall import COUNTS,GLYPHS,LAKES,Engine,square_name

class NativeForkAdapterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='fork-native-');cls.observer=Path(cls.tmp.name)/'observer'
  spec=get_policy('student-template-flag-bomb-v1-normal')
  subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Isrc/core',*['-D'+v for v in spec['defines']+['AI_TRACE','AI_TRAINING']],'-o',str(cls.observer),*spec['sources']],cwd=ROOT,check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_public_successor_keys_match_real_quiet_scout_and_combat_events(self):
  for army in(0,1):
   def sq(s):return s if army==0 else 99-s
   for defender in(1,9):
    for destination in(70,60,50):
     cells=[254 if s in LAKES else 255 for s in range(100)]
     cells[sq(50)]=army*16|defender;cells[sq(80)]=(1-army)*16|64|12
     cells[sq(0)]=(1-army)*16|32|11;cells[sq(99)]=army*16|11
     remaining=[0]*12;remaining[8]=1;shuttle={0:(None,None,0),1:(None,None,0)}
     lost=_fork_enemy_lost(cells,army,remaining)
     outcomes=list(_fork_successors(cells,army,remaining,shuttle,worths(lost),[0,20000]))
     expected=next(o for o in outcomes if o['observation']['move']==[sq(80),sq(destination)])
     engine=Engine(shlex.quote(str(self.observer)))
     try:
      engine.send('new '+('red','blue')[army]);engine.send('rules 0')
      engine.ask('position '+str(army)+' '+bytes(lost).hex()+' '+bytes(cells).hex()+' ffffffff0000','positionok')
      event=('moved '+square_name(sq(80))+' '+square_name(sq(destination))if destination!=50 else
             'battle '+square_name(sq(80))+' '+square_name(sq(50))+' '+GLYPHS[8]+' '+GLYPHS[defender])
      engine.send(event)
      actual_side,board,fallen,history=engine.ask('public','public').split();actual=list(bytes.fromhex(board));actual_lost=list(bytes.fromhex(fallen))
      seen=[0]*12
      for c in actual:
       if c<254 and bool(c&16)!=bool(army)and c&32:seen[c&15]+=1
      hidden=[n-l-s for n,l,s in zip(COUNTS,actual_lost,seen)]
      expected_key=_fork_public_key(expected['cells'],army,_fork_enemy_lost(expected['cells'],army,expected['remaining']),expected['remaining'],expected['shuttle'])
      self.assertEqual(_fork_public_key(actual,army,actual_lost,hidden,history),expected_key,(army,defender,destination))
     finally:engine.close()
 def test_actual_immediate_flag_win_precedes_a_pending_witness(self):
  class PublicModel:
   army=0
   def rank_marginals(self,cells,army,lost,histories):return {},[0]*12
   def posterior(self):return[1.],{}
  bot=MobileCaptureBot(self.observer,adjustment_scope='quiet-fork');bot.model=PublicModel()
  try:
   cells=[254 if s in LAKES else 255 for s in range(100)];cells[0]=11;cells[22]=4;cells[23]=16|32|11
   lost=COUNTS[:];lost[11]=0
   bot.observer.ask('position 0 '+bytes(lost).hex()+' '+bytes(cells).hex()+' ffffffff0000','positionok')
   bot._fork_plan=dict(stage='ready',states={'stale':(22,12)},first_move=(22,12),bound=15)
   self.assertEqual(bot.choose(),(22,23));self.assertIsNone(bot._fork_plan)
   self.assertEqual(bot.last_report['quiet_adjustment']['reason'],'immediate-native-flag-win')
  finally:bot.close()
 def test_scope_cli_accepts_fork_and_preserves_no_moves(self):
  result=subprocess.run(['python3',str(ROOT/'tools/campaign_native_mobile.py'),'--help'],capture_output=True,text=True,check=True)
  self.assertIn('quiet-fork',result.stdout)
  class PublicModel:
   army=0
   def rank_marginals(self,cells,army,lost,histories):return {},[0]*12
   def posterior(self):return[1.],{}
  bot=MobileCaptureBot(self.observer,adjustment_scope='quiet-fork');bot.model=PublicModel()
  try:
   cells=[254 if s in LAKES else 255 for s in range(100)];cells[0]=11;cells[99]=16|32|11
   lost=COUNTS[:];lost[11]=0
   bot.observer.ask('position 0 '+bytes(lost).hex()+' '+bytes(cells).hex()+' ffffffff0000','positionok')
   bot._fork_plan={'untrusted':'stale'}
   self.assertIsNone(bot.choose());self.assertIsNone(bot._fork_plan)
  finally:bot.close()

if __name__=='__main__':unittest.main()
