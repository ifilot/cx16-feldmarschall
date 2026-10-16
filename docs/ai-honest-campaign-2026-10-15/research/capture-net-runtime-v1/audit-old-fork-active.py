"""Current older scopes must exactly match their immutable frozen launchers."""
import hashlib,json,shlex,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import get_policy
from campaign_native_mobile import MobileCaptureBot
from feldmarschall import Engine,parse_square,square_name
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
HERE=Path(__file__).resolve().parent
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
def run():
 with Tournament(COHORT)as saved:game=saved.game(35)
 states,_=replay(game);events=public_events(game,states);spec=get_policy('student-template-flag-bomb-v1-normal');results=[]
 with tempfile.TemporaryDirectory(prefix='fork-old-scope-')as tmp:
  observer=Path(tmp)/'observer'
  subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core'),*['-D'+v for v in spec['defines']+['AI_TRACE','AI_TRAINING']],*[str(ROOT/p)for p in spec['sources']],'-o',str(observer)],check=True,capture_output=True)
  for scope,identity in(('quiet-fork','student-template-public-forks-v1-normal'),):
   directory=ROOT/'build/ai-catalog'/identity;receipt=json.loads((directory/'build.json').read_text())
   for name,sha in receipt['runtime_sha256'].items():assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==sha
   decisions=overrides=0
   for army in(0,1):
    reference=Engine(shlex.quote(str(directory/'engine')));candidate=MobileCaptureBot(observer,adjustment_scope=scope)
    try:
     for line in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):reference.send(line);candidate.observe(line.split())
     for ply,line in enumerate(events[:300]):
      if ply%2==army:
       expected=tuple(map(parse_square,reference.ask('go','move').split()));selected=candidate.choose();assert expected==selected,(scope,army,ply,expected,selected)
       overrides+=candidate.last_report['overridden'];actual=tuple(game['moves'][ply])
       if actual!=selected:
        correction='played '+' '.join(map(square_name,actual));reference.ask(correction,'playedok');candidate.observe(correction.split())
       assert reference.ask('public','public')==candidate.observer.ask('public','public');decisions+=1
      reference.send(line);candidate.observe(line.split())
    finally:reference.close();candidate.close()
   assert decisions==300
   results.append(dict(scope=scope,immutable_identity=identity,decisions_both_sides=decisions,actual_overrides=overrides,exact_choice_and_public_actual_history_parity=True,recipe_sha256=receipt['recipe_sha256']))
 return dict(kind='older-frozen-scope-exact-parity',strength_evidence=False,cohort_sha256=hashlib.sha256(COHORT.read_bytes()).hexdigest(),game=35,results=results,sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in('tools/campaign_native_mobile.py','tools/campaign_mobile_capture.py','tools/campaign_capture_net.py')})
if __name__=='__main__':
 data=run();(HERE/'old-fork-active-parity.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data,indent=2))
