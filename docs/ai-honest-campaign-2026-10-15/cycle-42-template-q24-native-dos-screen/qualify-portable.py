import hashlib,json,shlex,shutil,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
from ai_registry import ROOT,build_policy,get_policy,receives_opponent_setup
from feldmarschall import Engine,Position,parse_square,valid_setup
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
identity='student-template-q24-native-v1-normal';program,receipt=build_policy(identity);policy=get_policy(identity)
assert receipt['policy']==policy and not receives_opponent_setup(policy)
for name,sha in receipt['runtime_sha256'].items():assert hashlib.sha256((program.parent/name).read_bytes()).hexdigest()==sha
with Tournament(ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour') as t:game=t.game(3)
states,_=replay(game);events=public_events(game,states);decisions=0
with tempfile.TemporaryDirectory(prefix='template-q24-portable-') as temp:
 root=Path(temp);runtime=root/'runtime';shutil.copytree(program.parent,runtime);exe=runtime/program.name
 reference_program=root/'reference'
 subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core'),*['-D'+x for x in policy['defines']],*[str(ROOT/x)for x in policy['sources']],'-o',str(reference_program)],check=True,capture_output=True,text=True)
 assert subprocess.check_output([str(exe),'--identity'],cwd=temp,text=True).strip()==identity
 for army in (0,1):
  with patch('feldmarschall.ROOT',root):portable=Engine(shlex.quote(str(exe)))
  reference=Engine(shlex.quote(str(reference_program)))
  try:
   for engine in (portable,reference):
    for line in ('new '+('red','blue')[army],'rules 0','difficulty normal','seed 2529971'):engine.send(line)
   setup=portable.ask('setup','setup');assert valid_setup(setup)and setup==reference.ask('setup','setup')
   for engine in (portable,reference):engine.send('setup '+game[('red_setup','blue_setup')[army]])
   for ply,event in enumerate(events[:300]):
    if ply%2==army:
     raw=portable.ask('go','move');assert raw==reference.ask('go','move'),(army,ply,raw)
     position=Position();position.cells=states[ply][:];assert tuple(map(parse_square,raw.split()))in position.moves(army)
     decisions+=1
    portable.send(event);reference.send(event)
  finally:portable.close();reference.close()
assert decisions==300
out=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-42-template-q24-native-dos-screen'
(out/'portable-qualification.json').write_text(json.dumps(dict(policy=identity,source_sha256=policy['source_sha256'],receipt=receipt,public_history_decisions_both_sides=decisions,portable_outside_checkout=True,reference='Independent current-source GCC production-flag compile; both receive identical public forced history and own setup only.',setup_and_legal_move_parity=True,no_diagnostic_flags_in_registered_policy=not any(x in policy['defines']for x in('AI_TEST','AI_DIAGNOSTICS')),scope='Packaging integration and deterministic move parity. Forced historical actions need not equal selected actions, so this is not a counterfactual strength result. Every actual tournament follows selected actions.'),indent=2)+'\n')
print('PASS frozen portable',decisions,'both-side public-history decisions')
