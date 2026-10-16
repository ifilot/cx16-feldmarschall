"""Same-state native component: veto only the fourteen fixed Scout objectives."""
import hashlib,json,re,shlex,subprocess,tempfile,time,zipfile
from collections import Counter
from pathlib import Path
from audit_runtime import ROOT,HERE,sha,parse
from ai_registry import get_policy,build_policy
from campaign_native_template import NativeTemplateBot
from feldmarschall import Engine,square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

def once(text,needle,replacement):
 if text.count(needle)!=1:raise ValueError('ambiguous patchanchor '+needle[:80])
 return text.replace(needle,replacement)

def build(directory,policy):
 source=directory/'source';source.mkdir();archive=ROOT/policy['archive'];assert sha(archive)==policy['source_sha256']
 with zipfile.ZipFile(archive)as bundle:bundle.extractall(source)
 path=source/'src/core/ai.c';text=path.read_text();text=once(text,'static uint8_t own;', '''static uint8_t component_veto_valid,component_veto[100];
+void component_veto_clear(void) {component_veto_valid=0;}
+uint8_t component_veto_set(uint8_t army,const uint8_t* mapping) {
+ unsigned i;uint8_t cell,target;
+ if(game_rules || ai_difficulty!=AI_NORMAL)return 0;
+ for(i=0;i<100;i++)if(mapping[i]!=255) {
+  cell=board[i];if(mapping[i]>=100)return 0;target=board[mapping[i]];
+  if(mapping[i]>=100 || !IS_PIECE(cell) || (cell&CELL_BLUE)!=army || PIECE_TYPE(cell)>PIECE_SERGEANT ||
+     !IS_PIECE(target) || (target&CELL_BLUE)==army || !(target&CELL_REVEALED) || PIECE_TYPE(target)!=PIECE_SCOUT)return 0;
+ }
+ memcpy(component_veto,mapping,100);component_veto_valid=1;return 1;
+}
+static uint8_t own;'''.replace('\n+','\n'))
 needle='        if(!enemy(cell) || distance[sq] == NOWHERE) continue;';text=once(text,needle,needle+'\n        if(component_veto_valid && component_veto[from]==sq)continue;');path.write_text(text)
 path=source/'src/native/engine.c';text=path.read_text();text=once(text,'static uint8_t own;', '''void component_veto_clear(void);
+uint8_t component_veto_set(uint8_t army,const uint8_t* mapping);
+static uint8_t component_saved[AI_TEST_STATE_SIZE];
+static uint16_t component_seed;
+static uint8_t own;'''.replace('\n+','\n'))
 marker='        } else if(!strcmp(command, "isready")) {'
 text=once(text,marker,'''        } else if(!strcmp(command,"component-save")) {
+            ai_test_save(component_saved);component_seed=random_current();reply("component-saveok");
+        } else if(!strcmp(command,"component-restore")) {
+            ai_test_load(component_saved);random_seed(component_seed);component_veto_clear();reply("component-restoreok");
+        } else if(!strcmp(command,"component-rng")) {
+            printf("component-rng %u\\n",random_current());fflush(stdout);
+        } else if(!strcmp(command,"component-veto")) {
+            uint8_t mapping[100];
+            reply(args && hex(args,mapping,100) && component_veto_set(own,mapping)?"component-vetook":"error component-veto");
+        } else if(!strcmp(command, "isready")) {'''.replace('\n+','\n'));path.write_text(text)
 observer=directory/'observer';command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow','-Isrc/core',*['-D'+d for d in policy['defines']],'-DAI_TRACE','-o',str(observer),*policy['sources']];subprocess.run(command,cwd=source,check=True,capture_output=True,text=True)
 return observer,dict(original_archive_sha256=sha(archive),observer_sha256=sha(observer),command=command,patched_sources={name:sha(source/name)for name in('src/core/ai.c','src/native/engine.c')})

def plans(text):
 result={}
 for line in text.splitlines():
  m=re.match(r'plan (\d+) goal=(\d+) previous=(\d+) steps=(\d+) utility=(-?\d+)',line)
  if m:actor,*rest=map(int,m.groups());result[actor]=rest
 return result

class Component:
 def __init__(self,engine,log):self.engine=engine;self.log=log;self.offset=0;self.mapping={};self.last=None
 def send(self,line):return self.engine.send(line)
 def tracego(self):
  self.engine.send('trace on');move=self.engine.ask('go','move');self.engine.send('trace off');self.engine.ask('isready','readyok');text=self.log.read_text()[self.offset:];self.offset=self.log.stat().st_size
  return move,plans(text)
 def ask(self,line,prefix):
  if line!='go':return self.engine.ask(line,prefix)
  self.engine.ask('component-save','component-saveok');base,oldplans=self.tracego();self.last=dict(baseline_move=base,candidate_move=base,changed_goals=0,actor_plans=len(oldplans),vetoed_actors=len(self.mapping),changed_choice=False)
  if self.mapping:
   oldstrategy=self.engine.ask('strategy','strategy');oldrng=self.engine.ask('component-rng','component-rng')
   self.engine.ask('component-restore','component-restoreok');mapping=[255]*100
   for actor,target in self.mapping.items():mapping[actor]=target
   self.engine.ask('component-veto '+bytes(mapping).hex(),'component-vetook');new,newplans=self.tracego()
   assert oldplans.keys()==newplans.keys();changed=sum(oldplans[a][0]!=newplans[a][0]for a in oldplans)
   self.last.update(candidate_move=new,changed_goals=changed,changed_choice=new!=base,
     goal_changes=[dict(actor=a,before=oldplans[a][0],after=newplans[a][0])for a in oldplans if oldplans[a][0]!=newplans[a][0]])
   self.engine.ask('component-restore','component-restoreok');again,againplans=self.tracego()
   assert again==base and againplans==oldplans
   assert self.engine.ask('strategy','strategy')==oldstrategy
   assert self.engine.ask('component-rng','component-rng')==oldrng
   self.last['same_state_rng_and_replayed_baseline']=True
  return base
 def close(self):self.engine.close()

def run():
 protocol=json.loads((HERE/'RUNTIME-PROTOCOL.json').read_text());preflight=json.loads((HERE/'scout-pursuit-result.json').read_text());vetoes={(r['game'],r['ordinal']):{p['source']:p['goal']for p in r['proofs']}for r in preflight['records']};assert sum(len(v)for v in vetoes.values())==14
 cohort=ROOT/protocol['history'];assert sha(cohort)==preflight['cohort_sha256'];policy=get_policy(protocol['reference']);launcher,_=build_policy(policy['id']);counts=Counter();rows=[];started=time.perf_counter()
 with tempfile.TemporaryDirectory(prefix='scout-component-')as text:
  tmp=Path(text);observer,binding=build(tmp,policy)
  with Tournament(cohort)as store:
   for identity in protocol['game_ids']:
    game=store.game(identity);army=int(game['blue']=='student-template-flag-bomb-v1-normal');states,_=replay(game);events=public_events(game,states);log=tmp/f'{identity}.log';wrapper=Component(Engine(shlex.quote(str(observer))+' 2>'+shlex.quote(str(log))),log);bot=NativeTemplateBot(wrapper);reference=Engine(shlex.quote(str(launcher)));ordinal=0
    try:
     for command in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):bot.observe(command.split());reference.send(command)
     for ply,event in enumerate(events):
      if ply%2==army:
       ordinal+=1;sampled=(identity,ordinal)in vetoes;wrapper.mapping=vetoes.get((identity,ordinal),{});expected=parse(reference.ask('go','move'));chosen=bot.choose();assert chosen==expected;counts['frozen_baseline_prefix_parity']+=1
       if sampled:
        row=dict(game=identity,army=army,ply=ply,ordinal=ordinal,**wrapper.last);rows.append(row);counts['sampled_roots']+=1;counts['vetoed_actor_goals']+=row['vetoed_actors'];counts['changed_goals']+=row['changed_goals'];counts['changed_choices']+=row['changed_choice'];counts['component_roots_with_veto']+=bool(row['vetoed_actors']);counts['roots_army_'+str(army)]+=1
       actual=tuple(game['moves'][ply])
       if chosen!=actual:
        command='played '+' '.join(map(square_name,actual));reference.ask(command,'playedok');bot.observe(command.split())
       if ordinal>=protocol['maximum_own_decisions']:break
      bot.observe(event.split());reference.send(event)
    finally:bot.close();reference.close()
    counts['games']+=1
    if counts['games']%8==0:print(json.dumps(dict(counts,elapsed_seconds=time.perf_counter()-started)),flush=True)
 result=dict(kind='same-state-native-scout-goal-veto-component',strength_evidence=False,runtime_policy=False,counts=dict(counts),source_binding=binding,preflight_sha256=sha(HERE/'scout-pursuit-result.json'),protocol_sha256=sha(HERE/'SCOUT-COMPONENT-PROTOCOL.json'),cohort_sha256=sha(cohort),elapsed_seconds=time.perf_counter()-started,records=rows)
 (HERE/'scout-component-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('records','source_binding')},indent=2))
if __name__=='__main__':run()
