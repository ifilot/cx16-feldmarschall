import json,subprocess,tempfile,shlex,time,statistics
from pathlib import Path
from unittest.mock import patch
from ai_registry import ROOT,build_policy,get_policy
from campaign_native_mobile import MobileCaptureBot
from feldmarschall import Engine,parse_square,square_name
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
spec=get_policy('student-template-flag-bomb-v1-normal');baseline,previous=build_policy(spec['id'])
(baseline.parent/'build.json').unlink();_,rebuilt=build_policy(spec['id']);assert previous==rebuilt
with Tournament(ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour') as saved:game=saved.game(3)
states,_=replay(game);events=public_events(game,states);decisions=0;overrides=0;timings=[]
with tempfile.TemporaryDirectory(prefix='home-adapter-parity-') as tmp:
 observer=Path(tmp)/'observer'
 command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core'),*['-D'+v for v in [*spec['defines'],'AI_TRACE','AI_TRAINING']],*[str(ROOT/p) for p in spec['sources']],'-o',str(observer)]
 subprocess.run(command,check=True,capture_output=True,text=True)
 for army in (0,1):
  native=Engine(shlex.quote(str(baseline)));candidate=MobileCaptureBot(observer)
  try:
   for line in ('new '+('red','blue')[army],'rules 0','seed 2439961','setup '+game[('red_setup','blue_setup')[army]]):native.send(line);candidate.observe(line.split())
   for ply,event in enumerate(events[:300]):
    if ply%2==army:
     start=time.perf_counter();first=tuple(map(parse_square,native.ask('go','move').split()));baseline_time=time.perf_counter()-start
     start=time.perf_counter();second=candidate.choose();candidate_time=time.perf_counter()-start
     timings.append((baseline_time,candidate_time))
     report=candidate.last_report
     assert first==tuple(report['native_selected']),(army,ply,first,report)
     if report['overridden']:
      overrides+=1
      native.ask('played '+' '.join(map(square_name,second)),'playedok')
     actual=tuple(game['moves'][ply])
     if second!=actual:
      line='played '+' '.join(map(square_name,actual));native.ask(line,'playedok');candidate.observe(line.split())
     assert native.ask('public','public')==candidate.observer.ask('public','public')
     decisions+=1
    native.send(event);candidate.observe(event.split())
  finally:native.close();candidate.close()
assert decisions==min(300,len(events))
out=ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-mobile-captures-v1/adapter-cost.json'
out.write_text(json.dumps(dict(frozen_baseline=spec['id'],old_policy_exact_rebuild=True,decisions_both_sides=decisions,actual_overrides=overrides,native_single_search_history_parity=True,observational_timing_seconds=dict(baseline_mean=statistics.mean(a for a,b in timings),candidate_mean=statistics.mean(b for a,b in timings),paired_delta_mean=statistics.mean(b-a for a,b in timings),paired_delta_median=statistics.median(b-a for a,b in timings),scope="same300publicpositions under concurrent tournament load; walltime observational, not controlled target timing"),public_boards_and_actual_choice_history_equal=True,scope='One completed C21 screening game,up to300public-historydecisions; real mobile-capture correction. Reference go is corrected to the same actual choice, then both receive identical historical events. No strength claim.'),indent=2)+'\n')
print('PASS active history',decisions,'decisions;',overrides,'actual overrides')
