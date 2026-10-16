"""Incidence only: structural own-secrecy gate, old screening data only."""
import json,shlex,tempfile,time
from collections import Counter
from pathlib import Path
from audit_runtime import HERE,ROOT,sha,build_trace,parse
from ai_registry import get_policy,build_policy
from campaign_native_template import NativeTemplateBot
from campaign_capture_net import capture
from campaign_mobile_capture import _fork_danger,_fork_record,_fork_shuttle
from feldmarschall import Engine,square_name,battle
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

class Ranked:
 def __init__(self,engine):self.engine=engine;self.scores={}
 def ask(self,line,prefix):
  if line!='go':return self.engine.ask(line,prefix)
  self.engine.send('ranked');self.scores={}
  while True:
   words=self.engine.read().split()
   if words[0]=='candidate':self.scores[tuple(map(int,words[1:3]))]=int(words[3])
   elif words[0]=='move':return ' '.join(words[1:])
   elif words[0]=='error':raise RuntimeError(' '.join(words))
 def send(self,line):return self.engine.send(line)
 def close(self):self.engine.close()

def gate(cells,army,remaining,shuttle,scores,selected,counts):
 if selected is None:return False
 source,target=selected;actor=cells[source];victim=cells[target]
 if actor&15 not in(0,1) or actor&32 or victim>=254:return False
 counts['selected_concealed_highrank_attacks']+=1
 if not victim&32 or victim&15>=10 or battle(actor&15,victim&15)!='attacker':return False
 counts['disclosed_mobile_surviving_captures']+=1
 alternatives=[move for move in scores if move[0]!=source and move[1]==target and cells[move[0]]&32 and capture(cells,army,*move,shuttle[army])]
 if not alternatives:return False
 counts['same_victim_already_public_surviving_alternative']+=1
 ties=[move for move in alternatives if scores[move]==scores[selected]]
 if not ties:return False
 counts['exact_native_score_ties']+=1
 flag=next((sq for sq,c in enumerate(cells)if c<254 and bool(c&16)==bool(army)and c&15==11),None)
 if flag is None:return False
 def safe(move):
  after=cells[:];after[move[1]]=after[move[0]]|32|64;after[move[0]]=255
  return not _fork_danger(after,army,remaining,move[1],after[move[1]]&15,shuttle[1-army],True)
 if not safe(selected):return False
 safe_ties=[move for move in ties if safe(move)]
 if not safe_ties:return False
 counts['both_immediate_recapture_safe']+=1
 if _fork_danger(cells,army,remaining,flag,11,shuttle[1-army],True):return False
 def flag_safe(move):
  after=cells[:];after[move[1]]=after[move[0]]|32|64;after[move[0]]=255
  return not _fork_danger(after,army,remaining,flag,11,shuttle[1-army],True)
 if flag_safe(selected)and any(flag_safe(move)for move in safe_ties):counts['all_gate_conditions']+=1;return True
 return False

def run():
 protocol=json.loads((HERE/'RUNTIME-PROTOCOL.json').read_text());cohort=ROOT/protocol['history'];policy=get_policy(protocol['reference']);candidate=get_policy(protocol['candidate']);executable,_=build_policy(policy['id']);counts=Counter();records=[];started=time.perf_counter()
 with tempfile.TemporaryDirectory(prefix='secrecy-preflight-')as tmptext:
  observer,binding=build_trace(Path(tmptext),candidate)
  with Tournament(cohort)as store:
   for identity in protocol['game_ids']:
    game=store.game(identity);army=int(game['blue']=='student-template-flag-bomb-v1-normal');states,_=replay(game);events=public_events(game,states);bot=NativeTemplateBot(Ranked(Engine(shlex.quote(str(observer)))));reference=Engine(shlex.quote(str(executable)));ordinal=0
    try:
     for line in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):bot.observe(line.split());reference.send(line)
     for ply,event in enumerate(events):
      if ply%2==army:
       ordinal+=1;expected=parse(reference.ask('go','move'));selected=bot.choose();assert selected==expected;counts['frozen_baseline_prefix_parity']+=1
       if ordinal in protocol['sample_own_ordinals']:
        _,_,_,shuttle_text=bot.observer.ask('public','public').split();cells=list(bytes.fromhex(bot.last_report['public_board_hex']));remaining=bot.last_report['remaining'];rootcounts=Counter()
        accepted=gate(cells,army,remaining,_fork_shuttle(shuttle_text),bot.observer.scores,selected,rootcounts)
        counts.update(rootcounts);counts['sampled_roots']+=1;counts['roots_army_'+str(army)]+=1
        records.append(dict(game=identity,army=army,ply=ply,ordinal=ordinal,counts=dict(rootcounts),eligible=accepted))
       actual=tuple(game['moves'][ply])
       if selected!=actual:
        line='played '+' '.join(map(square_name,actual));reference.ask(line,'playedok');bot.observe(line.split())
       if ordinal>=protocol['maximum_own_decisions']:break
      bot.observe(event.split());reference.send(event)
    finally:bot.close();reference.close()
    counts['games']+=1
    if counts['games']%8==0:print(json.dumps(dict(counts,elapsed_seconds=time.perf_counter()-started)),flush=True)
 result=dict(kind='structural-own-secrecy-incidence-preflight',strength_evidence=False,no_policy_implemented=True,counts=dict(counts),cohort_sha256=sha(cohort),protocol_sha256=sha(HERE/'SECRECY-PROTOCOL.json'),binding=binding,elapsed_seconds=time.perf_counter()-started,records=records)
 (HERE/'secrecy-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('records','binding')},indent=2))
if __name__=='__main__':run()
