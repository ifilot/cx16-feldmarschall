"""Frozen prospective old-screen mechanism/cost audit; never starts matches."""
import hashlib,importlib.util,json,re,shlex,subprocess,sys,tempfile,time,zipfile,statistics
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import build_policy,get_policy
from campaign_native_template import NativeTemplateBot as BaseBot
from new_campaign_objectives_bot import NativeTemplateBot as GoalBot
from feldmarschall import Engine,parse_square,square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def parse(text):return None if text=='none'else tuple(map(parse_square,text.split()))
class Measured:
 def __init__(self,engine):self.engine=engine;self.goseconds=0.;self.bytes=0
 def ask(self,line,prefix):
  self.bytes+=len(line)+1;start=time.perf_counter();result=self.engine.ask(line,prefix)
  if line=='go':self.goseconds+=time.perf_counter()-start
  return result
 def send(self,line):self.bytes+=len(line)+1;return self.engine.send(line)
 def close(self):self.engine.close()

def build_trace(directory,policy):
 source=directory/'source';source.mkdir();archive=ROOT/policy['archive'];assert sha(archive)==policy['source_sha256']
 with zipfile.ZipFile(archive)as bundle:bundle.extractall(source)
 observer=directory/'trace-observer';command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow','-Isrc/core',*['-D'+d for d in policy['defines']],'-DAI_TRACE','-o',str(observer),*policy['sources']]
 subprocess.run(command,cwd=source,check=True,capture_output=True,text=True)
 return observer,dict(archive_sha256=sha(archive),observer_sha256=sha(observer),command=command,unchanged_sources=True,only_extra_define='AI_TRACE')

def run():
 protocol=json.loads((HERE/'RUNTIME-PROTOCOL.json').read_text());cohort=ROOT/protocol['history'];candidate=get_policy(protocol['candidate']);reference=get_policy(protocol['reference'])
 executable,candidate_receipt=build_policy(candidate['id']);baseline,base_receipt=build_policy(reference['id'])
 records=[];counts=Counter();started=time.perf_counter();samples=set(protocol['sample_own_ordinals'])
 with tempfile.TemporaryDirectory(prefix='objective-runtime-')as tmptext:
  tmp=Path(tmptext);observer,binding=build_trace(tmp,candidate)
  with Tournament(cohort)as store:
   for index,identity in enumerate(protocol['game_ids']):
    game=store.game(identity);army=int(game['blue']=='student-template-flag-bomb-v1-normal');states,_=replay(game);events=public_events(game,states)
    bots=[];launchers=[];logs=[];offsets=[0,0]
    for kind,launcher,name in((BaseBot,baseline,'base'),(GoalBot,executable,'goal')):
     log=tmp/f'{name}-{identity}.log';logs.append(log)
     bots.append(kind(Measured(Engine(shlex.quote(str(observer))+' 2>'+shlex.quote(str(log))))))
     launchers.append(Engine(shlex.quote(str(launcher))))
    ordinal=0
    try:
     for line in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):
      for bot in bots:bot.observe(line.split())
      for engine in launchers:engine.send(line)
     for ply,event in enumerate(events):
      if ply%2==army:
       ordinal+=1;sampled=ordinal in samples;order=(0,1)if index%2==0 else(1,0);moves=[None,None];metrics=[None,None];plans=[{},{}]
       for n in order:
        bot=bots[n];expected=parse(launchers[n].ask('go','move'))
        if sampled:bot.observer.send('trace on')
        start=time.perf_counter();go_before=bot.observer.goseconds;bytes_before=bot.observer.bytes;moves[n]=bot.choose();elapsed=time.perf_counter()-start
        assert moves[n]==expected,(identity,army,ply,n,'frozen launcher parity')
        counts['frozen_launcher_choice_parity']+=1
        if sampled:
         bot.observer.send('trace off');text=logs[n].read_text()[offsets[n]:];offsets[n]=logs[n].stat().st_size
         for line in text.splitlines():
          match=re.match(r'plan (\d+) goal=(\d+) previous=(\d+) steps=(\d+) utility=(-?\d+)',line)
          if match:
           actor,goal,previous,steps,utility=map(int,match.groups());plans[n][actor]=(goal,previous,steps,utility)
         native=bot.observer.goseconds-go_before
         metrics[n]=dict(total_seconds=elapsed,preparation_seconds=elapsed-native,native_seconds=native,command_bytes=bot.observer.bytes-bytes_before)
       if sampled:
        assert set(plans[0])==set(plans[1]),(identity,ply,'same actors')
        changed=sum(plans[0][actor][0]!=plans[1][actor][0]for actor in plans[0]);counts['sampled_roots']+=1;counts['actor_plans']+=len(plans[0]);counts['changed_goals']+=changed;counts['changed_choices']+=moves[0]!=moves[1];counts['roots_with_changed_goal']+=bool(changed);counts['roots_army_'+str(army)]+=1
        records.append(dict(game=identity,army=army,ply=ply,ordinal=ordinal,changed_choice=moves[0]!=moves[1],actor_plans=len(plans[0]),changed_goals=changed,baseline=metrics[0],candidate=metrics[1]))
       actual=tuple(game['moves'][ply])
       for n,bot in enumerate(bots):
        if moves[n]!=actual:
         line='played '+' '.join(map(square_name,actual));launchers[n].ask(line,'playedok');bot.observe(line.split())
       if ordinal>=protocol['maximum_own_decisions']:break
      for bot in bots:bot.observe(event.split())
      for engine in launchers:engine.send(event)
    finally:
     for bot in bots:bot.close()
     for engine in launchers:engine.close()
    counts['games']+=1
    if counts['games']%8==0:print(json.dumps(dict(counts,elapsed_seconds=time.perf_counter()-started)),flush=True)
 def distribution(values):
  ordered=sorted(values);return dict(n=len(values),mean=statistics.mean(values),median=statistics.median(values),p95=ordered[int(.95*(len(ordered)-1))],maximum=max(values))
 result=dict(kind='old-screen-full-native-goal-runtime-audit',strength_evidence=False,counts=dict(counts),cohort_sha256=sha(cohort),protocol_sha256=sha(HERE/'RUNTIME-PROTOCOL.json'),source_binding=binding,candidate_policy=candidate,reference_policy=reference,elapsed_seconds=time.perf_counter()-started,
   metrics={kind:{metric:distribution([row[kind][metric]for row in records])for metric in('total_seconds','preparation_seconds','native_seconds','command_bytes')}for kind in('baseline','candidate')},records=records)
 (HERE/'runtime-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('records','candidate_policy','reference_policy','source_binding')},indent=2))
if __name__=='__main__':run()
