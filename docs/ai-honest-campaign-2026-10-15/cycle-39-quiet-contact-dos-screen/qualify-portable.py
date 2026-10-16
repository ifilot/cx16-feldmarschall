import hashlib,json,shutil,tempfile,subprocess,shlex
from pathlib import Path
from unittest.mock import patch
from ai_registry import ROOT,build_policy,get_policy,receives_opponent_setup
from campaign_native_mobile import MobileCaptureBot
from feldmarschall import Engine,Position,parse_square,square_name,valid_setup
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
folder=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-39-quiet-contact-dos-screen'
reports=[]
with Tournament(ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour') as t:game=t.game(3)
states,_=replay(game);events=public_events(game,states)
for scope in ('quiet-occupancy','quiet-mobile'):
 identity='student-template-'+scope+'-v1-normal';program,receipt=build_policy(identity)
 assert receipt['policy']==get_policy(identity) and not receives_opponent_setup(get_policy(identity))
 for name in ('campaign_mobile_capture.py','campaign_native_mobile.py'):
  assert receipt['runtime_sha256'][name]==hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest()
 for name,sha in receipt['runtime_sha256'].items():assert hashlib.sha256((program.parent/name).read_bytes()).hexdigest()==sha
 decisions=overrides=0
 with tempfile.TemporaryDirectory(prefix='quiet-portable-') as tmp:
  target=Path(tmp)/'runtime';shutil.copytree(program.parent,target);exe=target/program.name
  assert subprocess.check_output([str(exe),'--identity'],cwd=tmp,text=True).strip()==identity
  for army in (0,1):
   with patch('feldmarschall.ROOT',Path(tmp)):portable=Engine(shlex.quote(str(exe)))
   reference=MobileCaptureBot(target/'observer',adjustment_scope=scope)
   try:
    for line in ('new '+('red','blue')[army],'rules 0','seed 2499961'):portable.send(line);reference.observe(line.split())
    generated=portable.ask('setup','setup');assert valid_setup(generated) and generated==reference.observe(['setup'])
    line='setup '+game[('red_setup','blue_setup')[army]];portable.send(line);reference.observe(line.split())
    for ply,event in enumerate(events[:300]):
     if ply%2==army:
      selected=tuple(map(parse_square,portable.ask('go','move').split()));assert selected==reference.choose(),(scope,army,ply)
      position=Position();position.cells=states[ply][:];assert selected in position.moves(army)
      overrides+=int(reference.last_report['overridden']);actual=tuple(game['moves'][ply])
      if selected!=actual:
       line='played '+' '.join(map(square_name,actual));portable.ask(line,'playedok');reference.observe(line.split())
      assert portable.ask('public','public')==reference.observer.ask('public','public')
      decisions+=1
     portable.send(event);reference.observe(event.split())
   finally:portable.close();reference.close()
 assert decisions==300
 reports.append(dict(policy=identity,source_sha256=get_policy(identity)['source_sha256'],receipt=receipt,public_history_decisions_both_sides=decisions,reference_overrides=overrides,portable_outside_checkout=True,setup_moves_public_state_and_actual_history_parity=True,scope='Portable integration, no counterfactual strength claim.'))
 print('PASS',scope,decisions,'decisions',overrides,'overrides',flush=True)
(folder/'portable-qualification.json').write_text(json.dumps(reports,indent=2)+'\n')
for identity in ('student-template-flag-bomb-v1-normal','student-template-mobile-captures-v1-normal'):
 _,receipt=build_policy(identity);assert receipt['policy']==get_policy(identity)
 print('PASS immutable rebuild',identity,flush=True)
