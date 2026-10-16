"""Exact public-key cache lifecycle tests; inherits the V1 numerical/public oracle."""
import ctypes as C
from pathlib import Path
from unittest.mock import patch
import subprocess,unittest
from test_campaign_template_target import TargetTemplates,TEMPLATES,ROOT

class CachedTemplates(TargetTemplates):
 @classmethod
 def setUpClass(cls):
  original=subprocess.run
  def compile_cache(command,**kwargs):
   wrapper=Path(command[command.index('-o')+2]);text=wrapper.read_text().replace('ai_memory_reset();','ai_reset();');wrapper.write_text(text)
   command=command+['-DAI_TEMPLATE_PRIOR_Q24_CACHE','-DAI_MISSIONS']+[str(ROOT/'src/core'/f) for f in ('ai.c','ai_mission.c','random.c')]
   return original(command,**kwargs)
  with patch('test_campaign_template_target.subprocess.run',compile_cache):super().setUpClass()
  cls.lib.ai_template_test_cache_hit.restype=C.c_uint8
 def hit(self,army,expected):
  result=self.infer(army);self.assertEqual(result[0],4);self.assertEqual(self.lib.ai_template_test_cache_hit(),expected);return result
 def snapshot(self):
  return ([self.lib.ai_template_test_flags()[i] for i in range(40)],[self.lib.ai_template_test_bombs()[i] for i in range(40)],[self.lib.ai_template_test_cache(a,i) for a in range(12) for i in range(40)])
 def test_cache_requires_base_prior(self):
  result=subprocess.run(['cc','-fsyntax-only','-DAI_TEMPLATE_PRIOR_Q24_CACHE','-I'+str(ROOT/'src/core'),str(ROOT/'src/core/ai_template.c')],capture_output=True,text=True)
  self.assertNotEqual(result.returncode,0);self.assertIn('requires AI_TEMPLATE_PRIOR_Q24',result.stderr)
 def test_same_constraints_hit_own_move_and_enemy_map_refresh(self):
  self.initialize([TEMPLATES[0],TEMPLATES[1]])
  self.hit(0,0);before=self.snapshot();self.hit(0,1);self.assertEqual(before,self.snapshot())
  self.move(61,51);self.hit(0,1);self.assertEqual(before,self.snapshot())
  self.move(30,40);self.hit(0,0);before=self.snapshot()
  self.move(64,54);self.hit(0,1)
  self.move(40,50);self.hit(0,1);self.assertEqual(before,self.snapshot())
  self.lib.ai_template_actor(0);row=(C.c_int16*100).in_dll(self.lib,'ai_template_transfer');self.assertEqual(row[40],0)
  self.assertEqual(row[50],0) # moved unknown targets retain native mobile-only handling
  self.infer(0,lambda sq:(sq*11)%16);self.assertEqual(self.lib.ai_template_test_cache_hit(),1)
 def test_disclosure_dead_origin_owner_and_reset_invalidate(self):
  self.initialize([TEMPLATES[0],TEMPLATES[1]])
  self.hit(0,0);self.move(60,50);self.hit(0,1);self.move(30,40);self.hit(0,0)
  self.position.cells[40][3]=True;self.write_board();self.hit(0,0);self.hit(0,1)
  self.move(50,40);self.hit(0,0);self.hit(0,1)
  self.hit(1,0);self.hit(1,1);self.hit(0,0)
  self.lib.ai_template_test_cache_poison();self.lib.fixture_reset();self.lib.ai_template_start();self.assertEqual(self.infer(0)[0],1)
  self.initialize([TEMPLATES[0],TEMPLATES[1]]);self.hit(0,0)
  self.lib.ai_template_test_cache_poison();self.lib.fixture_reset();self.lib.ai_template_start();self.hit(0,0);self.hit(0,1)
 def test_every_prepare_validates_public_inventory(self):
  self.initialize([TEMPLATES[0],TEMPLATES[1]]);self.hit(0,0);self.hit(0,1)
  lost=((C.c_uint8*12)*2).in_dll(self.lib,'rules_known_lost');lost[1][0]=1
  self.assertEqual(self.infer(0)[0],2);self.assertFalse(self.valid.value);self.assertEqual(self.lib.ai_template_test_cache_hit(),0)
  lost[1][0]=0;self.hit(0,1)
 def test_dynamic_marshal_and_last_bomb_worth_changes(self):
  # Known ranks stay fixed across capture; public losses change Spy/Miner worth.
  for rank,actor in ((0,9),(10,7)):
   self.initialize([TEMPLATES[0],TEMPLATES[1]])
   squares=[s for s,c in enumerate(self.position.cells) if c and c[0]==1 and c[1]==rank]
   for sq in squares:self.position.cells[sq][3]=True
   self.write_board();self.lib.ai_memory_sync()
   for sq in squares[:-1]:self.position.cells[sq]=None
   self.write_board()
   lost=((C.c_uint8*12)*2).in_dll(self.lib,'rules_known_lost');lost[1][rank]=len(squares)-1
   self.hit(0,0);before=self.snapshot();self.hit(0,1)
   self.position.cells[squares[-1]]=None;self.write_board();lost[1][rank]=len(squares)
   self.hit(0,0);after=self.snapshot();self.hit(0,1)
   self.assertEqual(before[:2],after[:2])
   self.assertNotEqual(before[2][actor*40:(actor+1)*40],after[2][actor*40:(actor+1)*40])
   self.lib.ai_template_forget();self.assertEqual(self.infer(0)[0],1)

if __name__=='__main__':unittest.main(defaultTest='CachedTemplates')
