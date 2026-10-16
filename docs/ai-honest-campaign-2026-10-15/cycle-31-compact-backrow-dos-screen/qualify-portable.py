import hashlib,json,shlex,shutil,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
from ai_registry import ROOT,build_policy,get_policy,receives_opponent_setup
from feldmarschall import Engine,Position,parse_square,valid_setup
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
identity='student-compact-backrow-v1-normal';program,receipt=build_policy(identity)
assert receipt['policy']==get_policy(identity) and not receives_opponent_setup(get_policy(identity))
for name,sha in receipt['runtime_sha256'].items():assert hashlib.sha256((program.parent/name).read_bytes()).hexdigest()==sha
with Tournament(ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour') as t:game=t.game(9)
states,_=replay(game);events=public_events(game,states);decisions=0
with tempfile.TemporaryDirectory(prefix='compact-portable-') as tmp:
 target=Path(tmp)/'runtime';shutil.copytree(program.parent,target);exe=target/program.name
 assert subprocess.check_output([str(exe),'--identity'],cwd=tmp,text=True).strip()==identity
 for army in (0,1):
  with patch('feldmarschall.ROOT',Path(tmp)):portable=Engine(shlex.quote(str(exe)))
  reference=Engine(shlex.quote(str(ROOT/'build/ai-compact-backrow-native')))
  try:
   for engine in (portable,reference):
    for line in ('new '+('red','blue')[army],'rules 0','difficulty normal','seed 2419971'):engine.send(line)
   generated=portable.ask('setup','setup');assert valid_setup(generated) and generated==reference.ask('setup','setup')
   for engine in (portable,reference):engine.send('setup '+game[('red_setup','blue_setup')[army]])
   for ply,event in enumerate(events[:120]):
    if ply%2==army:
     raw=portable.ask('go','move');assert raw==reference.ask('go','move')
     position=Position();position.cells=states[ply][:];assert tuple(map(parse_square,raw.split())) in position.moves(army)
     decisions+=1
    portable.send(event);reference.send(event)
  finally:portable.close();reference.close()
assert decisions==120
out=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-31-compact-backrow-dos-screen/portable-qualification.json'
out.write_text(json.dumps(dict(policy=identity,source_sha256=get_policy(identity)['source_sha256'],receipt=receipt,public_history_decisions_both_sides=decisions,portable_outside_checkout=True,reference='build/ai-compact-backrow-native; independent production-flags GCC build also used in80bankeddecisiontest',setup_and_move_parity=True),indent=2)+'\n')
print('PASS portable:',decisions,'public-history decisions')
