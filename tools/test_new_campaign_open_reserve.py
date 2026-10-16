"""One-swap reserve release: own geometry, native legality and setup gates."""
import ctypes
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

from ai_registry import ROOT,get_policy
from feldmarschall import COUNTS,Engine,GLYPHS,LAKES,setup_squares,valid_setup,parse_square,square_name
from research_deployment_double_shell import geometry
from tournament_store import mirror_setup

SOURCE=ROOT/'tools/new_campaign_open_reserve_deploy.c'
OUT=ROOT/'docs/ai-honest-campaign-2026-10-16/research/open-reserve'

def layouts():
 text=(ROOT/'src/core/ai_deploy.c').read_text();arrays=re.findall(r'\{([\d,]+)\}',text)
 base=''.join(GLYPHS[int(n)]for n in next(a for a in arrays if len(a.split(','))==40).split(','));candidate=list(base);candidate[28],candidate[38]=candidate[38],candidate[28]
 return base,''.join(candidate)

class OpenReserveTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='open-reserve-');cls.folder=Path(cls.temp.name);cls.base,cls.candidate=layouts();cls.programs={};cls.records=[]
  spec=get_policy('student-fortress-template-flag-bomb-v1-normal');engine=(ROOT/'src/native/engine.c').read_text();anchor='        } else if(!strcmp(command, "seed")) {'
  assert engine.count(anchor)==1
  engine=engine.replace(anchor,'''        } else if(!strcmp(command,"fixture-rng")) { printf("rng %u\\n",random_current());fflush(stdout);
        } else if(!strcmp(command,"fixture-targets")) {
            uint8_t list[MAX_TARGETS],n,i;from=square(args);
            if(from>=100){reply("error fixture-targets");continue;}
            n=rules_targets(from,list);printf("fixture-targets %u",n);
            for(i=0;i<n;i++)printf(" %u",list[i]);putchar('\\n');fflush(stdout);
'''+anchor)
  (cls.folder/'engine.c').write_text(engine)
  for mode in('control','default-off','candidate'):
   path=cls.folder/mode;path.mkdir();deploy=path/'ai_deploy.c';deploy.write_bytes((ROOT/'src/core/ai_deploy.c'if mode=='control'else SOURCE).read_bytes())
   sources=[str(cls.folder/'engine.c')if s=='src/native/engine.c'else str(deploy)if s=='src/core/ai_deploy.c'else s for s in spec['sources']]
   command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow','-Isrc/core',*['-D'+d for d in spec['defines']],*(['-DAI_FORTRESS_OPEN_RESERVE']if mode=='candidate'else[]),'-o',str(path/'engine'),*sources]
   subprocess.run(command,cwd=ROOT,check=True,capture_output=True);cls.programs[mode]=path/'engine'
 @classmethod
 def tearDownClass(cls):
  OUT.mkdir(parents=True,exist_ok=True)
  report=dict(scope='Geometry and synthetic native own-mobility components only; no policy registration/tournament/strength claim',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in(SOURCE,Path(__file__),ROOT/'src/core/ai_deploy.c')},
   layouts={name:dict(setup=s,geometry=geometry(s))for name,s in(('Fortress',cls.base),('OpenReserve',cls.candidate))},native_components=cls.records,
   prior='The exact single-swap geometry was already proposed as MobilityOnlyFortress in old research_deployment_double_shell.py; prior C22 played a different three-swap double-shell package.',
   caveat='Permanent front access assumes mobile teammates can vacate. Initial reserve has no legal move in either formation. Synthetic residue removes other mobile teammates from the board; this demonstrates legal activation after corridors clear, not reachable-history timing or higher game strength.')
  (OUT/'component.json').write_text(json.dumps(report,indent=2)+'\n');cls.temp.cleanup()
 def test_one_swap_inventory_and_retained_flag_defense(self):
  self.assertTrue(valid_setup(self.candidate));self.assertEqual(sorted(self.base),sorted(self.candidate));self.assertEqual([i for i in range(40)if self.base[i]!=self.candidate[i]],[28,38])
  self.assertEqual(self.base[28],'B');self.assertEqual(self.base[38],'6')
  for index in(20,31,30,27,21):self.assertEqual(self.base[index],self.candidate[index])
  a,b=geometry(self.base),geometry(self.candidate);self.assertEqual(a['mobile_pieces_with_permanent_front_access'],32);self.assertEqual(b['mobile_pieces_with_permanent_front_access'],33);self.assertEqual(a['trapped_mobile_squares'],[38]);self.assertEqual(b['trapped_mobile_squares'],[])
  self.assertEqual(a['min_bomb_captures_from_front'],b['min_bomb_captures_from_front']);self.assertEqual(b['min_bomb_captures_from_front'],1)
 def test_reflections_and_both_color_native_initial_and_cleared_mobility(self):
  for army in(0,1):
   for reflection in(False,True):
    own=setup_squares(army);transform=lambda n:n//10*10+9-n%10 if reflection else n
    for mode,layout,reserve in(('control',self.base,38),('candidate',self.candidate,28)):
     if reflection:layout=mirror_setup(layout)
     reserve_square=own[transform(reserve)];bot=Engine(shlex.quote(str(self.programs[mode])))
     try:
      bot.send('new '+('red','blue')[army]);bot.send('difficulty normal');bot.send('rules 0');bot.send('setup '+layout)
      initial=list(map(int,bot.ask('fixture-targets '+chr(97+reserve_square%10)+str(10-reserve_square//10),'fixture-targets').split()));self.assertEqual(initial,[0])
      cells=[254 if sq in LAKES else 255 for sq in range(100)]
      for index,glyph in enumerate(layout):
       if glyph in'BF' or index==transform(reserve):cells[own[index]]=army*16|GLYPHS.index(glyph)
      enemy=1-army;far=setup_squares(enemy);enemyflag=far[transform(30)];cells[enemyflag]=enemy*16|12;cells[far[transform(0)]]=enemy*16|8|32;lost=COUNTS[:];lost[11]-=1;lost[8]-=1
      bot.ask('position %d %s %s ffffffff0000'%(army,bytes(lost).hex(),bytes(cells).hex()),'positionok')
      options=list(map(int,bot.ask('fixture-targets '+chr(97+reserve_square%10)+str(10-reserve_square//10),'fixture-targets').split()));chosen=bot.ask('go','move')
      if mode=='control':self.assertEqual(options,[0]);self.assertEqual(chosen,'none')
      else:
       self.assertGreater(options[0],0);self.assertEqual(options[0],len(options)-1);move=tuple(map(parse_square,chosen.split()));self.assertEqual(move[0],reserve_square);self.assertIn(move[1],options[1:])
      self.records.append(dict(army=army,horizontal_reflection=reflection,mode=mode,reserve_origin=reserve,initial_legal_targets=initial[0],cleared_corridor_legal_targets=options[1:],selected=chosen,synthetic_residue=True))
     finally:bot.close()
 def test_two_specific_native_corridor_vacancies_release_candidate_in_full_own_army(self):
  for army in(0,1):
   for reflection in(False,True):
    transform=lambda n:n//10*10+9-n%10 if reflection else n
    own=setup_squares(army);front=own[transform(8)];second=own[transform(18)];forward=front+(10 if army else -10)
    for mode,layout,reserve in(('control',self.base,38),('candidate',self.candidate,28)):
     if reflection:layout=mirror_setup(layout)
     self.assertEqual(GLYPHS.index(layout[transform(8)]),3);self.assertEqual(GLYPHS.index(layout[transform(18)]),6)
     bot=Engine(shlex.quote(str(self.programs[mode])))
     try:
      for command in('new '+('red','blue')[army],'rules 0','difficulty normal','setup '+layout):bot.send(command)
      for source,target in((front,forward),(second,front)):
       options=list(map(int,bot.ask('fixture-targets '+square_name(source),'fixture-targets').split()))
       self.assertIn(target,options[1:]);bot.send('moved '+square_name(source)+' '+square_name(target))
      square=own[transform(reserve)];options=list(map(int,bot.ask('fixture-targets '+square_name(square),'fixture-targets').split()))
      if mode=='control':self.assertEqual(options,[0])
      else:self.assertIn(second,options[1:])
      self.records.append(dict(army=army,horizontal_reflection=reflection,mode=mode,reserve_origin=reserve,full_own_army=True,corridor_actor_ranks=[GLYPHS.index(layout[transform(8)]),GLYPHS.index(layout[transform(18)])],own_corridor_moves=[[front,forward],[second,front]],reserve_targets_after_two_vacancies=options[1:],synthetic_own_movement_component_not_complete_history=True))
     finally:bot.close()
 def setup(self,bot,army,seed,level,rules):
  for command in('new '+('red','blue')[army],'rules '+str(rules),'difficulty '+level,'seed '+str(seed)):bot.send(command)
  return bot.ask('setup','setup')
 def test_default_off_exact_native_binary_and_rng_difficulty_rules_gates(self):
  self.assertEqual(self.programs['control'].read_bytes(),self.programs['default-off'].read_bytes())
  bots={name:Engine(shlex.quote(str(path)))for name,path in self.programs.items()}
  try:
   for army in(0,1):
    for level in('easy','normal','hard'):
     for rules in(0,1,63):
      for seed in(1,17,9123,65535):
       outputs={name:self.setup(bot,army,seed,level,rules)for name,bot in bots.items()}
       self.assertEqual(outputs['control'],outputs['default-off'])
       if level=='normal'and rules==0:self.assertEqual(outputs['candidate'],self.candidate)
       else:self.assertEqual(outputs['candidate'],outputs['control'])
       self.assertEqual(len({bot.ask('fixture-rng','rng')for bot in bots.values()}),1)
  finally:
   for bot in bots.values():bot.close()
 def test_macro_requires_matched_control_and_isolated_factor(self):
  for defines,message in[(['AI_FORTRESS_OPEN_RESERVE'],'requires AI_DEPLOY_FORTRESS_ONLY'),(['AI_FORTRESS_OPEN_RESERVE','AI_DEPLOY_FORTRESS_ONLY','AI_DEPLOY_DOUBLE_SHELL'],'separate single-swap'),(['AI_FORTRESS_OPEN_RESERVE','AI_DEPLOY_FORTRESS_ONLY','AI_FORTRESS_INNER_GUARD'],'separate single-swap')]:
   result=subprocess.run(['gcc','-E','-Isrc/core',*['-D'+d for d in defines],str(SOURCE)],cwd=ROOT,capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertIn(message,result.stderr)
 def test_own_setup_cannot_observe_enemy_board_or_change_other_squares(self):
  stub=self.folder/'boundary.c';stub.write_text('#include <stdint.h>\n#include "board.h"\n#include "ai.h"\nuint8_t board[SQUARES],game_rules=0,ai_difficulty=AI_NORMAL;\nuint16_t random_next(void){return 123u;}\nvoid setup_random(uint8_t blue){(void)blue;}\n')
  library=self.folder/'boundary.so';subprocess.run(['gcc','-shared','-fPIC','-O2','-Wno-unknown-pragmas','-Isrc/core','-DAI_DEPLOY_FORTRESS_ONLY','-DAI_FORTRESS_OPEN_RESERVE',str(SOURCE),str(stub),'-o',str(library)],cwd=ROOT,check=True,capture_output=True)
  native=ctypes.CDLL(str(library));board=(ctypes.c_uint8*100).in_dll(native,'board')
  for army in(0,1):
   own=setup_squares(army);expected=None
   for salt in(0,1,7,31,254):
    for square in range(100):board[square]=(square*17+salt)%256
    before=list(board);native.setup_ai(army);actual=[board[sq]for sq in own]
    self.assertTrue(all(board[sq]==before[sq]for sq in range(100)if sq not in own))
    if expected is None:expected=actual
    else:self.assertEqual(actual,expected)

if __name__=='__main__':unittest.main()
