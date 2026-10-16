"""Real native two-turn witness execution from one fixed C21 public prefix."""
import hashlib,json,shlex,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import get_policy
from campaign_native_mobile import MobileCaptureBot
from campaign_mobile_capture import _fork_public_key,_fork_successors,_fork_shuttle
from campaign_belief_values import worths
from feldmarschall import Engine,parse_square,square_name,GLYPHS
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
HERE=Path(__file__).resolve().parent
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
class Counted:
 def __init__(self,engine):self.engine=engine;self.commands=[]
 def send(self,line):self.commands.append(line);return self.engine.send(line)
 def ask(self,line,prefix):self.commands.append(line);return self.engine.ask(line,prefix)
 def read(self):return self.engine.read()
 def close(self):return self.engine.close()
def parse(text):return None if text=='none'else tuple(map(parse_square,text.split()))
def event(observation,cells):
 source,target=observation['move'];squares=' '.join(map(square_name,(source,target)))
 return 'moved '+squares if observation['quiet']else'battle '+squares+' '+GLYPHS[observation['rank']]+' '+GLYPHS[cells[target]&15]
def public(bot):
 side,board,fallen,history=bot.observer.ask('public','public').split();army=int(side);cells=list(bytes.fromhex(board));lost=list(bytes.fromhex(fallen))
 histories={sq:list(map(int,bot.observer.ask('memory '+square_name(sq),'history').split()))for sq,c in enumerate(cells)if c<254 and bool(c&16)!=bool(army)and not c&32}
 _,remaining=bot.model.rank_marginals(cells,army,lost,histories)
 return army,cells,lost,remaining,history

def run():
 spec=get_policy('student-template-flag-bomb-v1-normal');directory=ROOT/'build/ai-catalog'/spec['id'];receipt=json.loads((directory/'build.json').read_text())
 for name,sha in receipt['runtime_sha256'].items():assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==sha
 with Tournament(COHORT)as saved:game=saved.game(35)
 states,_=replay(game);events=public_events(game,states);army=int(game['blue']==spec['id']);tested=0
 with tempfile.TemporaryDirectory(prefix='public-fork-witness-')as tmp:
  observer=Path(tmp)/'observer'
  subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core'),*['-D'+v for v in spec['defines']+['AI_TRACE','AI_TRAINING']],*[str(ROOT/p)for p in spec['sources']],'-o',str(observer)],check=True,capture_output=True)
  reference=Engine(shlex.quote(str(directory/'engine')));counted=Counted(Engine(shlex.quote(str(observer))))
  bot=MobileCaptureBot(counted,adjustment_scope='quiet-fork')
  try:
   for line in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):reference.send(line);bot.observe(line.split())
   for ply,line in enumerate(events[:220]):
    if ply%2==army:
     expected=parse(reference.ask('go','move'))
     with patch('campaign_native_mobile.fork_selection',side_effect=lambda *args:(args[5],dict(reason='forced-prefix-native-control'))):selected=bot.choose()
     assert selected==expected
     actual=tuple(game['moves'][ply])
     if selected!=actual:
      correction='played '+' '.join(map(square_name,actual));reference.ask(correction,'playedok');bot.observe(correction.split())
     tested+=1
    reference.send(line);bot.observe(line.split())
   counted.commands=[];expected=parse(reference.ask('go','move'));fork=bot.choose();root=bot.last_report
   assert expected==tuple(root['native_selected']);assert fork==(25,35)and fork!=expected,root
   assert counted.commands.count('ranked')==1 and sum(c.startswith('played ')for c in counted.commands)==1
   reference.ask('played '+' '.join(map(square_name,fork)),'playedok')
   chosen=next(entry for entry in root['quiet_adjustment']['fork_certificates']if tuple(entry['move'])==fork)
   reply=next(response for response in chosen['proof']['responses']if response['enemy']['quiet'])
   before=public(bot);first='moved '+' '.join(map(square_name,fork));reference.send(first);bot.observe(first.split())
   enemy=event(reply['enemy'],before[1]);reference.send(enemy);bot.observe(enemy.split())
   current=public(bot);key=_fork_public_key(current[1],army,current[2],current[3],current[4]);assert key==reply['public_key']
   counted.commands=[];native_followup=parse(reference.ask('go','move'));capture=bot.choose();followup=bot.last_report
   assert native_followup==tuple(followup['native_selected']);assert capture==tuple(reply['response'])
   assert followup['quiet_adjustment']['phase']=='followup'and bot._fork_plan is None
   assert counted.commands.count('ranked')==1 and sum(c.startswith('played ')for c in counted.commands)==int(capture!=native_followup)
   if capture!=native_followup:reference.ask('played '+' '.join(map(square_name,capture)),'playedok')
   assert reference.ask('public','public')==bot.observer.ask('public','public')
   attack='battle '+' '.join(map(square_name,capture))+' '+GLYPHS[current[1][capture[0]]&15]+' '+GLYPHS[current[1][capture[1]]&15]
   reference.send(attack);bot.observe(attack.split());after=public(bot)
   replies=list(_fork_successors(after[1],army,after[3],_fork_shuttle(after[4]),worths(after[2]),[0,20000]))
   last=next(o for o in replies if o['observation']['quiet']);line=event(last['observation'],after[1]);reference.send(line);bot.observe(line.split())
   expected_after=parse(reference.ask('go','move'))
   with patch('campaign_native_mobile.fork_selection',side_effect=lambda *args:(args[5],dict(reason='post-witness-native-parity'))):selected_after=bot.choose()
   assert selected_after==expected_after
   return dict(kind='actual-public-prefix-committed-witness-qualification',strength_evidence=False,cohort_sha256=hashlib.sha256(COHORT.read_bytes()).hexdigest(),game=35,root_ply=220,own_army=army,forced_prefix_decisions=tested,native_root=expected,fork=fork,enemy_public_observation=reply['enemy'],witness=capture,native_followup=native_followup,witness_overrode_native=capture!=native_followup,complete_public_successor_key_matched=True,public_goal_history_and_next_native_choice_parity=True,one_ranked_search_per_turn=True,no_rng_or_extra_search=True,plan_used_once=True,root_bound=root['quiet_adjustment']['selected_bound'],scope='Recorded C21 public prefix followed by a synthetic count-feasible public enemy observation, committed witness capture and another public quiet reply. No referee hidden rank is consumed after the prefix and no match is saved.',sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in('tools/campaign_native_mobile.py','tools/campaign_mobile_capture.py')})
  finally:reference.close();bot.close()
if __name__=='__main__':
 result=run();(HERE/'witness-integration.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
