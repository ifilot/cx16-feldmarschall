"""Bounded progress failure for disclosedScout objectives, incidence only."""
import importlib.util,json,re,shlex,tempfile,time
from collections import Counter
from pathlib import Path
from audit_runtime import ROOT,HERE,sha,build_trace,parse
from ai_registry import get_policy,build_policy
from campaign_native_template import NativeTemplateBot
from campaign_belief_values import gain,worths
from campaign_mobile_capture import _fork_shuttle,_fork_record,_fork_danger
from feldmarschall import Engine,LAKES,battle,Position,square_name,TWO_SQUARES
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay
old=ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-mobile-objectives-pilot-v1/component.py';spec=importlib.util.spec_from_file_location('old_goal_component',old);component=importlib.util.module_from_spec(spec);spec.loader.exec_module(component)

def own_can_capture(cells,army,target,shuttle):
 victim=cells[target]
 for source,cell in enumerate(cells):
  if cell>=254 or bool(cell&16)!=bool(army) or cell&15>=10:continue
  rank=cell&15
  if battle(rank,8)=='defender':continue
  a,b,n=shuttle[army]
  if n>=TWO_SQUARES and source==b and target==a:continue
  dist=abs(source//10-target//10)+abs(source%10-target%10)
  if dist==1:return True
  if rank==8 and(source//10==target//10 or source%10==target%10):
   step=(1 if target>source else -1)if source//10==target//10 else(10 if target>source else -10)
   if all(cells[s]==255 for s in range(source+step,target,step)):return True
 return False

def quiet_scout(cells,source,shuttle,army):
 row,col=divmod(source,10);a,b,n=shuttle[1-army]
 for dr,dc in((-1,0),(0,1),(1,0),(0,-1)):
  r,c=row,col;distance=0
  while True:
   r+=dr;c+=dc;distance+=1
   if not(0<=r<10 and 0<=c<10):break
   target=10*r+c
   if cells[target]!=255:break
   if distance>=2 and not(n>=TWO_SQUARES and source==b and target==a):yield target

def certificate(cells,army,actor,scout,shuttle):
 distance=component.route(cells,army,scout,actor);d=distance[actor]
 if d==255 or d<3:return dict(certified=False,reason='close-or-unreachable')
 row,col=divmod(actor,10);progress=[];a,b,n=shuttle[army]
 for dr,dc in((-1,0),(0,1),(1,0),(0,-1)):
  r,c=row+dr,col+dc
  if not(0<=r<10 and 0<=c<10):continue
  target=10*r+c
  if cells[target]==255 and distance[target]==d-1 and not(n>=TWO_SQUARES and actor==b and target==a):progress.append(target)
 if not progress:return dict(certified=False,reason='no-progress-move')
 flags=[s for s,c in enumerate(cells)if c<254 and bool(c&16)==bool(army)and c&15==11]
 witness={};endpoints=0
 for step in progress:
  after=cells[:];after[step]=after[actor]|64;after[actor]=255;updated=_fork_record(shuttle,army,actor,step);escape=None
  for target in quiet_scout(after,scout,updated,army):
   endpoints+=1;board=after[:];board[target]=board[scout]|64;board[scout]=255
   if own_can_capture(board,army,target,updated):continue
   if flags:
    f=flags[0];delta=abs(f//10-target//10)+abs(f%10-target%10)
    if delta==1:continue
    if f//10==target//10 or f%10==target%10:
     inc=(1 if f>target else -1)if f//10==target//10 else(10 if f>target else -10)
     if all(board[s]==255 for s in range(target+inc,f,inc)):continue
   new=component.route(board,army,target,step)[step]
   if new==255 or new>=d:escape=target;break
  if escape is None:return dict(certified=False,reason='one-progress-step-has-no-certified-escape',progress_steps=len(progress),endpoints=endpoints)
  witness[str(step)]=escape
 return dict(certified=True,progress_steps=len(progress),endpoints=endpoints,witness=witness,original_distance=d)

def inspect(cells,army,remaining,lost,marginals,flag,bomb,plans,selected,shuttle):
 counts=Counter();certs=[];worth=worths(lost)
 ownflag=next((s for s,c in enumerate(cells)if c<254 and bool(c&16)==bool(army)and c&15==11),None)
 for source,(goal,previous,steps,utility)in plans.items():
  if goal==255 or cells[source]&15>6 or cells[goal]>=254 or not cells[goal]&32 or cells[goal]&15!=8:continue
  counts['ordinary_actor_native_scout_goals']+=1
  distances=component.route(cells,army,goal,source)
  if distances[source]==255 or distances[source]<3:continue
  counts['distant_scout_goals']+=1
  if ownflag is None or abs(goal//10-ownflag//10)+abs(goal%10-ownflag%10)<=2 or _fork_danger(cells,army,remaining,ownflag,11,shuttle[1-army],True):continue
  counts['outside_flag_defense_and_flag_safe']+=1
  other=False;rank=cells[source]&15;reach=component.route(cells,army,source,source)
  for target,cell in enumerate(cells):
   if cell>=254 or bool(cell&16)==bool(army)or target==goal or reach[target]==255:continue
   g=component.expected(rank,target,cells,remaining,worth,marginals,flag,bomb)
   u=24+component.cdiv(g,4)+(12 if not cell&32 and rank>=6 else 0)-3*reach[target]+(8 if target==previous else 0)
   if abs(target//10-ownflag//10)+abs(target%10-ownflag%10)<=2 and(not cell&32 or cell&15<10):u+=40
   if g>=-component.cdiv(worth[rank],2)and u>=0:other=True;break
  if not other:continue
  counts['has_other_accepted_nonnegative_objective']+=1
  proof=certificate(cells,army,source,goal,shuttle);counts['endpoint_tests']+=proof.get('endpoints',0)
  if not proof['certified']:continue
  counts['certified_actor_goals']+=1;is_selected=selected is not None and selected[0]==source and cells[selected[1]]==255 and str(selected[1])in proof['witness'];counts['selected_quiet_progress_opportunities']+=is_selected
  certs.append(dict(source=source,goal=goal,selected_actor=bool(is_selected),**proof))
 return counts,certs

def run():
 protocol=json.loads((HERE/'RUNTIME-PROTOCOL.json').read_text());cohort=ROOT/protocol['history'];policy=get_policy(protocol['reference']);candidate=get_policy(protocol['candidate']);launcher,_=build_policy(policy['id']);counts=Counter();rows=[];started=time.perf_counter()
 with tempfile.TemporaryDirectory(prefix='scout-pursuit-')as tmptext:
  tmp=Path(tmptext);observer,binding=build_trace(tmp,candidate)
  with Tournament(cohort)as store:
   for identity in protocol['game_ids']:
    game=store.game(identity);army=int(game['blue']=='student-template-flag-bomb-v1-normal');states,_=replay(game);events=public_events(game,states);log=tmp/f'{identity}.log';offset=0;bot=NativeTemplateBot(Engine(shlex.quote(str(observer))+' 2>'+shlex.quote(str(log))));reference=Engine(shlex.quote(str(launcher)));ordinal=0
    try:
     for line in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):bot.observe(line.split());reference.send(line)
     for ply,event in enumerate(events):
      if ply%2==army:
       ordinal+=1;sampled=ordinal in protocol['sample_own_ordinals']
       if sampled:bot.observer.send('trace on')
       selected=bot.choose();assert selected==parse(reference.ask('go','move'));counts['frozen_baseline_prefix_parity']+=1
       if sampled:
        bot.observer.send('trace off');text=log.read_text()[offset:];offset=log.stat().st_size;plans={}
        for line in text.splitlines():
         m=re.match(r'plan (\d+) goal=(\d+) previous=(\d+) steps=(\d+) utility=(-?\d+)',line)
         if m:s,*rest=map(int,m.groups());plans[s]=rest
        report=bot.last_report;cells=list(bytes.fromhex(report['public_board_hex']));_,_,_,shuttle=bot.observer.ask('public','public').split()
        local,proofs=inspect(cells,army,report['remaining'],list(bytes.fromhex(report['lost_hex'])),report['marginals'],report['q12']['flag'],report['q12']['bomb'],plans,selected,_fork_shuttle(shuttle));counts.update(local);counts['sampled_roots']+=1;counts['roots_army_'+str(army)]+=1
        rows.append(dict(game=identity,army=army,ply=ply,ordinal=ordinal,counts=dict(local),proofs=proofs))
       actual=tuple(game['moves'][ply])
       if selected!=actual:
        line='played '+' '.join(map(square_name,actual));reference.ask(line,'playedok');bot.observe(line.split())
       if ordinal>=protocol['maximum_own_decisions']:break
      bot.observe(event.split());reference.send(event)
    finally:bot.close();reference.close()
    counts['games']+=1
    if counts['games']%8==0:print(json.dumps(dict(counts,elapsed_seconds=time.perf_counter()-started)),flush=True)
 result=dict(kind='bounded-scout-goal-nonprogress-incidence',strength_evidence=False,no_policy_implemented=True,counts=dict(counts),cohort_sha256=sha(cohort),protocol_sha256=sha(HERE/'SCOUT-PURSUIT-PROTOCOL.json'),source_binding=binding,elapsed_seconds=time.perf_counter()-started,records=rows)
 (HERE/'scout-pursuit-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('records','source_binding')},indent=2))
if __name__=='__main__':run()
