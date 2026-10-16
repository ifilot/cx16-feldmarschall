"""Persistent candidate-memory Scout refusal on old forced public prefixes."""
import json,shlex,tempfile,time
from collections import Counter
from pathlib import Path
from scout_component import build,plans
from scout_pursuit_preflight import inspect
from audit_runtime import ROOT,HERE,sha,parse
from ai_registry import get_policy,build_policy
from campaign_native_template import NativeTemplateBot
from campaign_native_beliefs import quantize
from campaign_mobile_capture import _fork_shuttle
from feldmarschall import Engine,square_name,parse_square
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

def tracego(engine,log,offset):
 engine.send('trace on');move=engine.ask('go','move');engine.send('trace off');engine.ask('isready','readyok');text=log.read_text()[offset:]
 return parse(move),plans(text),log.stat().st_size

def memory_difference(base,candidate):
 a=bytes.fromhex(base);b=bytes.fromhex(candidate);assert len(a)==len(b)
 return dict(goal_bytes=[dict(army=i//100,square=i%100,baseline_goal=x,candidate_goal=y)for i,(x,y)in enumerate(zip(a[:200],b[:200]))if x!=y],other_byte_difference_offsets=[i for i,(x,y)in enumerate(zip(a,b))if i>=200 and x!=y])

class PersistentScoutBot(NativeTemplateBot):
 def __init__(self,observer,log):
  super().__init__(observer);self.log=log;self.offset=0;self.sampled=False;self.last_component=None
 def choose(self):
  army_text,board,lost,shuttle=self.observer.ask('public','public').split();army=int(army_text);cells=list(bytes.fromhex(board));lost_counts=list(bytes.fromhex(lost))
  if self.model.army!=army:raise ValueError('public side mismatch')
  cells=[(c&240)|12 if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in cells]
  histories={sq:list(map(int,self.observer.ask('memory '+square_name(sq),'history').split()))for sq,c in enumerate(cells)if c<254 and bool(c&16)!=bool(army)and not c&32}
  marginals,remaining=self.model.rank_marginals(cells,army,lost_counts,histories);flag,bomb,mobile,packet=quantize(marginals,remaining)
  self.observer.ask('belief-priors '+packet,'belief-priorsok');self.observer.ask('component-veto '+'ff'*100,'component-vetook');self.last_component=None
  if self.sampled:
   self.observer.ask('component-save','component-saveok');proposed,oldplans,self.offset=tracego(self.observer,self.log,self.offset)
   counts,proofs=inspect(cells,army,remaining,lost_counts,marginals,flag,bomb,oldplans,proposed,_fork_shuttle(shuttle));selected=proposed
   mapping={row['source']:row['goal']for row in proofs};newplans=oldplans
   if mapping:
    self.observer.ask('component-restore','component-restoreok');values=[255]*100
    for source,target in mapping.items():values[source]=target
    self.observer.ask('component-veto '+bytes(values).hex(),'component-vetook');selected,newplans,self.offset=tracego(self.observer,self.log,self.offset)
   self.last_component=dict(gate_counts=dict(counts),vetoes=mapping,proposed_move=proposed,final_move=selected,immediate_changed_choice=proposed!=selected,
    changed_goals=[dict(actor=s,before=oldplans[s][0],after=newplans[s][0])for s in oldplans if oldplans[s][0]!=newplans[s][0]])
  else:selected=parse(self.observer.ask('go','move'))
  self.last_report=dict(public_board_hex=bytes(cells).hex(),lost_hex=lost,packet_sha256=__import__('hashlib').sha256(packet.encode()).hexdigest())
  return selected

def run():
 protocol=json.loads((HERE/'RUNTIME-PROTOCOL.json').read_text());old=json.loads((HERE/'scout-pursuit-result.json').read_text());cohort=ROOT/protocol['history'];assert sha(cohort)==old['cohort_sha256'];rootset={(r['game'],r['ordinal'])for r in old['records']};assert len(rootset)==356
 policy=get_policy(protocol['reference']);frozen,_=build_policy(policy['id']);counts=Counter();rootrecords=[];divergences=[];game_records=[];memory_records=[];started=time.perf_counter()
 with tempfile.TemporaryDirectory(prefix='scout-persistent-')as text:
  tmp=Path(text);observer,binding=build(tmp,policy)
  with Tournament(cohort)as store:
   for identity in protocol['game_ids']:
    game=store.game(identity);army=int(game['blue']=='student-template-flag-bomb-v1-normal');states,_=replay(game);events=public_events(game,states);log=tmp/f'{identity}.log';baseline=NativeTemplateBot(Engine(shlex.quote(str(observer))));candidate=PersistentScoutBot(Engine(shlex.quote(str(observer))+' 2>'+shlex.quote(str(log))),log);reference=Engine(shlex.quote(str(frozen)));ordinal=0;first=None;last_gate=None;game_divergences=0
    try:
     for command in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):
      baseline.observe(command.split());candidate.observe(command.split());reference.send(command)
     for ply,event in enumerate(events):
      if ply%2==army:
       ordinal+=1;sampled=(identity,ordinal)in rootset;candidate.sampled=sampled
       before=memory_difference(baseline.observer.ask('strategy','strategy'),candidate.observer.ask('strategy','strategy'))
       chosen_base=baseline.choose();assert chosen_base==parse(reference.ask('go','move'));chosen_candidate=candidate.choose()
       assert baseline.last_report['public_board_hex']==candidate.last_report['public_board_hex']
       assert baseline.last_report['lost_hex']==candidate.last_report['lost_hex']
       assert baseline.last_report['packet_sha256']==candidate.last_report['packet_sha256']
       counts['frozen_baseline_choice_parity']+=1;counts['identical_public_belief_packets']+=1
       if sampled:
        component=candidate.last_component;gate=bool(component['vetoes']);counts['sampled_roots']+=1;counts['vetoed_actor_goals']+=len(component['vetoes']);counts['gate_active_roots']+=gate;counts['immediate_veto_choice_changes']+=component['immediate_changed_choice']
        if gate:last_gate=ordinal
       if chosen_base!=chosen_candidate:
        row=dict(game=identity,army=army,ply=ply,ordinal=ordinal,sampled_gate_root=sampled,last_gate_ordinal=last_gate,baseline_move=chosen_base,candidate_move=chosen_candidate,predecision_memory_difference=before)
        divergences.append(row);game_divergences+=1;counts['different_actual_choices']+=1
        if first is None:first=row;counts['games_with_choice_divergence']+=1
       actual=tuple(game['moves'][ply]);command='played '+' '.join(map(square_name,actual))
       if chosen_base!=actual:baseline.observe(command.split());reference.ask(command,'playedok')
       if chosen_candidate!=actual:candidate.observe(command.split())
       after=memory_difference(baseline.observer.ask('strategy','strategy'),candidate.observer.ask('strategy','strategy'));same_rng=baseline.observer.ask('component-rng','component-rng')==candidate.observer.ask('component-rng','component-rng')
       counts['decisions_with_goal_memory_difference']+=bool(after['goal_bytes']);counts['decisions_with_other_memory_difference']+=bool(after['other_byte_difference_offsets']);counts['rng_equal_after_forced_correction']+=same_rng
       if before['goal_bytes']or after['goal_bytes']or before['other_byte_difference_offsets']or after['other_byte_difference_offsets']:
        memory_records.append(dict(game=identity,army=army,ply=ply,ordinal=ordinal,sampled_gate_root=sampled,last_gate_ordinal=last_gate,before=before,after=after,rng_equal=same_rng))
       if sampled:rootrecords.append(dict(game=identity,army=army,ply=ply,ordinal=ordinal,component=candidate.last_component,before=before,after=after,rng_equal=same_rng,whole_choice_differs_from_baseline=chosen_base!=chosen_candidate))
       if ordinal>=protocol['maximum_own_decisions']:break
      baseline.observe(event.split());candidate.observe(event.split());reference.send(event)
    finally:baseline.close();candidate.close();reference.close()
    game_records.append(dict(game=identity,army=army,own_decisions=ordinal,first_choice_divergence=first,choice_divergences=game_divergences));counts['games']+=1
    if counts['games']%8==0:print(json.dumps(dict(counts,elapsed_seconds=time.perf_counter()-started)),flush=True)
 result=dict(kind='persistent-own-memory-scout-refusal-forced-prefix',strength_evidence=False,on_policy_play=False,no_baseline_memory_restoration=True,counts=dict(counts),source_binding=binding,cohort_sha256=sha(cohort),protocol_sha256=sha(HERE/'SCOUT-PERSISTENT-PROTOCOL.json'),
  gate_source_sha256=sha(HERE/'scout_pursuit_preflight.py'),component_source_sha256=sha(HERE/'scout_component.py'),elapsed_seconds=time.perf_counter()-started,roots=rootrecords,games=game_records,divergences=divergences,memory_records=memory_records)
 (HERE/'scout-persistent-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('roots','games','divergences','memory_records','source_binding')},indent=2))
if __name__=='__main__':run()
