import json,time,statistics,shlex
from ai_registry import ROOT,build_policy
from campaign_native_mobile import MobileCaptureBot
from feldmarschall import Engine,parse_square,square_name
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
base,_=build_policy('student-template-flag-bomb-v1-normal')
with Tournament(ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour') as t:game=t.game(3)
states,_=replay(game);events=public_events(game,states);out=[]
for scope in ('quiet-occupancy','quiet-mobile'):
 program,receipt=build_policy('student-template-'+scope+'-v1-normal');timings=[];overrides=0
 for army in (0,1):
  native=Engine(shlex.quote(str(base)));candidate=MobileCaptureBot(program.parent/'observer',adjustment_scope=scope)
  try:
   for line in ('new '+('red','blue')[army],'rules 0','seed 2499961','setup '+game[('red_setup','blue_setup')[army]]):native.send(line);candidate.observe(line.split())
   for ply,event in enumerate(events[:300]):
    if ply%2==army:
     def first():
      start=time.perf_counter();move=tuple(map(parse_square,native.ask('go','move').split()));return move,time.perf_counter()-start
     def second():
      start=time.perf_counter();move=candidate.choose();return move,time.perf_counter()-start
     if ply%4<2:a,ta=first();b,tb=second()
     else:b,tb=second();a,ta=first()
     assert a==tuple(candidate.last_report['native_selected']);timings.append((ta,tb))
     if b!=a:native.ask('played '+' '.join(map(square_name,b)),'playedok');overrides+=1
     actual=tuple(game['moves'][ply])
     if b!=actual:
      line='played '+' '.join(map(square_name,actual));native.ask(line,'playedok');candidate.observe(line.split())
     assert native.ask('public','public')==candidate.observer.ask('public','public')
    native.send(event);candidate.observe(event.split())
  finally:native.close();candidate.close()
 assert len(timings)==300
 result=dict(scope=scope,decisions=300,overrides=overrides,baseline_mean_ms=1000*statistics.mean(a for a,b in timings),candidate_mean_ms=1000*statistics.mean(b for a,b in timings),paired_delta_median_ms=1000*statistics.median(b-a for a,b in timings),paired_delta_mean_ms=1000*statistics.mean(b-a for a,b in timings),limitation='Alternating call order on forced screening prefixes under concurrent tournament load. Observational desktop timing, no controlled target speed claim.',native_single_search_and_public_history_parity=True)
 out.append(result);print(json.dumps(result),flush=True)
p=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-39-quiet-contact-dos-screen/adapter-cost.json';p.write_text(json.dumps(out,indent=2)+'\n')
