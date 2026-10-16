"""Historical public-root numerical mechanism; never a strength experiment."""
from collections import Counter
import hashlib,json,math
from pathlib import Path
import shlex,time
from campaign_native_template import NativeTemplateBot
from feldmarschall import Engine,parse_square
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-target-prototype-v1'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 destination=OUT/'historical-mechanism.json'
 if destination.exists():raise ValueError('preserve completedmechanism')
 source_roots=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon/quiescence-mechanism.json'
 spec=json.loads(source_roots.read_text());source=ROOT/spec['source'];assert digest(source)==spec['source_sha256']
 selections={}
 for r in spec['roots']:selections.setdefault((r['game'],r['army']),{})[r['ply']]=r
 float_observer=ROOT/'build/ai-catalog/student-template-flag-bomb-v1-normal/observer'
 receipt=json.loads(float_observer.with_name('build.json').read_text());assert digest(float_observer)==receipt['runtime_sha256']['observer']
 native=Path('/tmp/template-target-observer-signed');base=Engine(shlex.quote(str(native)))
 floating=NativeTemplateBot(float_observer);records=[];statuses=Counter();seconds=Counter();choices=0
 try:
  with Tournament(source) as tournament:
   for (game_id,army),targets in sorted(selections.items()):
    game=tournament.game(game_id);states,_=replay(game);events=public_events(game,states)
    for command in ('new '+('red','blue')[army],'rules 0','difficulty normal','seed '+str(game['seed']*2+army+1),'setup '+game[('red_setup','blue_setup')[army]]):
     base.send(command);floating.observe(command.split())
    for ply,event in enumerate(events[:max(targets)+1]):
     if ply%2==army:
      public=base.ask('public','public');assert floating.observer.ask('public','public')==public
      if ply in targets:assert hashlib.sha256(public.encode()).hexdigest()==targets[ply]['public_sha256']
      started=time.perf_counter();text=base.ask('go','move');move=None if text=='none' else tuple(map(parse_square,text.split()));seconds['Q24']+=time.perf_counter()-started
      prior=list(map(int,base.ask('template-prior','prior').split()));statuses[prior[0]]+=1
      started=time.perf_counter();float_move=floating.choose();seconds['float']+=time.perf_counter()-started;choices+=1
      if ply in targets:
       delta=[];squares={origin:sq for sq,(owner,origin) in floating.model.tokens.items() if owner!=army}
       for origin in range(40):
        sq=squares.get(origin)
        if sq is None:continue
        for k,name in enumerate(('flag','bomb')):
         a=prior[4+2*origin+k];b=floating.last_report['q12'][name][sq]
         if a!=b:delta.append(dict(origin=origin,square=sq,kind=name,Q24=a,floating=b))
       records.append(dict(game=game_id,army=army,family=game['family'],ply=ply,public_sha256=targets[ply]['public_sha256'],Q24_move=move,floating_move=float_move,status=prior[0],valid=prior[1],evidence_Q24=prior[2],compatible_mask=prior[3],q12_differences=delta))
      played='played '+' '.join(event.split()[1:3]);base.ask(played,'playedok');floating.observe(played.split())
     base.send(event);floating.observe(event.split())
 finally:base.close();floating.close()
 assert len(records)==140
 report=dict(schema='historical-template-Q24-mechanism-v1',strength_evidence=False,source=spec['source'],source_sha256=digest(source),root_selection_sha256=digest(source_roots),native_sha256=digest(native),floating_observer_sha256=digest(float_observer),current_driver_sha256=digest(ROOT/'tools/campaign_native_template.py'),roots=records,summary=dict(roots=len(records),orientations=dict(Counter(r['army'] for r in records)),decisions_changed=sum(r['Q24_move']!=r['floating_move'] for r in records),roots_with_q12_differences=sum(bool(r['q12_differences']) for r in records),max_Q12_difference=max((abs(x['Q24']-x['floating']) for r in records for x in r['q12_differences']),default=0),all_forced_choices=choices,all_forced_statuses=dict(statuses),all_forced_wall_seconds=dict(seconds)),interpretation='Q24 arithmetic and origin-index rounding tie order both differ from floating/current-square rounding. Earlier choice differences can affect persistent goals on later forced roots. These are numerical policy mechanisms, not wins, and use historical development only.')
 destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2))
if __name__=='__main__':main()
