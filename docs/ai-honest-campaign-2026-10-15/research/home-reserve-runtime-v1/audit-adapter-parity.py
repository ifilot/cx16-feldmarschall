import json,subprocess,tempfile,shlex
from pathlib import Path
from unittest.mock import patch
from ai_registry import ROOT,build_policy,get_policy
from campaign_native_template import NativeTemplateBot
from feldmarschall import Engine,parse_square,square_name
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
spec=get_policy('student-template-flag-bomb-v1-normal');baseline,previous=build_policy(spec['id'])
(baseline.parent/'build.json').unlink();_,rebuilt=build_policy(spec['id']);assert previous==rebuilt
with Tournament(ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour') as saved:game=saved.game(3)
states,_=replay(game);events=public_events(game,states);decisions=0
with tempfile.TemporaryDirectory(prefix='home-adapter-parity-') as tmp:
 observer=Path(tmp)/'observer'
 command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core'),*['-D'+v for v in [*spec['defines'],'AI_TRACE']],*[str(ROOT/p) for p in spec['sources']],'-o',str(observer)]
 subprocess.run(command,check=True,capture_output=True,text=True)
 for army in (0,1):
  native=Engine(shlex.quote(str(baseline)));candidate=NativeTemplateBot(observer,home_interceptor=True)
  try:
   for line in ('new '+('red','blue')[army],'rules 0','seed 2439961','setup '+game[('red_setup','blue_setup')[army]]):native.send(line);candidate.observe(line.split())
   for ply,event in enumerate(events[:160]):
    if ply%2==army:
     with patch('campaign_home_reserve.evaluate',side_effect=lambda cells,army,lost,histories,moves,shuttle:(dict.fromkeys(moves,0.0),dict(active=False,reason='zero-correction-parity'))):
      first=tuple(map(parse_square,native.ask('go','move').split()));second=candidate.choose()
     assert first==second,(army,ply,first,second)
     actual=tuple(game['moves'][ply])
     if first!=actual:
      line='played '+' '.join(map(square_name,actual));native.ask(line,'playedok');candidate.observe(line.split())
     assert native.ask('public','public')==candidate.observer.ask('public','public')
     decisions+=1
    native.send(event);candidate.observe(event.split())
  finally:native.close();candidate.close()
assert decisions==160
out=ROOT/'docs/ai-honest-campaign-2026-10-15/research/home-reserve-runtime-v1/adapter-parity.json'
out.write_text(json.dumps(dict(frozen_baseline=spec['id'],old_policy_exact_rebuild=True,decisions_both_sides=decisions,ranked_single_search_no_correction_move_parity=True,public_boards_and_actual_choice_history_equal=True,scope='One completed C21 screening game,160public-historydecisions; correction patchedzero only for ranked/noop RNG+state parity. Real correction checked separately.'),indent=2)+'\n')
print('PASS160public-history decisions; oldIDexactrebuild')
