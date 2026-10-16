"""Forced C21 public histories only; no new games, registry edits or builds."""
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
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class CountingObserver:
 def __init__(self,engine):self.engine=engine;self.commands=[]
 def send(self,line):self.commands.append(line);return self.engine.send(line)
 def ask(self,line,prefix):self.commands.append(line);return self.engine.ask(line,prefix)
 def read(self):return self.engine.read()
 def close(self):return self.engine.close()
def frozen(identity):
 directory=ROOT/'build/ai-catalog'/identity;receipt=json.loads((directory/'build.json').read_text())
 for name,expected in receipt['runtime_sha256'].items():assert sha(directory/name)==expected,(identity,name)
 return directory/'engine',receipt

def run():
 baseline,base_receipt=frozen('student-template-flag-bomb-v1-normal')
 oldmobile,mobile_receipt=frozen('student-template-mobile-captures-v1-normal')
 with Tournament(COHORT)as saved:game=saved.game(3)
 states,_=replay(game);events=public_events(game,states);results=[]
 spec=get_policy('student-template-flag-bomb-v1-normal')
 with tempfile.TemporaryDirectory(prefix='quiet-contact-history-')as tmp:
  observer=Path(tmp)/'observer'
  command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core'),*['-D'+v for v in [*spec['defines'],'AI_TRACE','AI_TRAINING']],*[str(ROOT/p)for p in spec['sources']],'-o',str(observer)]
  subprocess.run(command,check=True,capture_output=True,text=True)
  for scope in('captures','quiet-occupancy','quiet-mobile'):
   decisions=overrides=cold=0;examples=[]
   for army in(0,1):
    reference=Engine(shlex.quote(str(oldmobile if scope=='captures'else baseline)))
    counted=CountingObserver(Engine(shlex.quote(str(observer))))
    candidate=MobileCaptureBot(counted,adjustment_scope=scope)
    try:
     for line in('new '+('red','blue')[army],'rules 0','seed 2699531','setup '+game[('red_setup','blue_setup')[army]]):reference.send(line);candidate.observe(line.split())
     for ply,event in enumerate(events[:300]):
      if ply%2==army:
       counted.commands=[]
       answer=reference.ask('go','move');expected=None if answer=='none'else tuple(map(parse_square,answer.split()))
       selected=candidate.choose();report=candidate.last_report
       assert counted.commands.count('ranked')==1
       assert not any(line=='go'or line.startswith('seed ')for line in counted.commands)
       assert sum(line.startswith('played ')for line in counted.commands)==int(report['overridden'])
       if scope=='captures':
        assert expected==selected,(scope,army,ply,expected,selected)
        overrides+=int(report['overridden'])
       else:
        assert expected==tuple(report['native_selected']),(scope,army,ply,expected,report['native_selected'])
        if report['overridden']:
         reference.ask('played '+' '.join(map(square_name,selected)),'playedok');overrides+=1
         if len(examples)<8:examples.append(dict(army=army,ply=ply,native=expected,selected=selected))
       if ply in(0,1):cold+=1
       actual=tuple(game['moves'][ply])
       if selected!=actual:
        line='played '+' '.join(map(square_name,actual));reference.ask(line,'playedok');candidate.observe(line.split())
       assert reference.ask('public','public')==candidate.observer.ask('public','public')
       decisions+=1
      reference.send(event);candidate.observe(event.split())
    finally:reference.close();candidate.close()
   assert decisions==300
   results.append(dict(scope=scope,decisions=decisions,both_armies=True,cold_roots=cold,scope_overrides=overrides,one_ranked_search_per_decision=True,no_seed_or_go_in_candidate=True,played_exactly_if_override=True,reference_choices_equal=(scope=='captures'),raw_native_and_actual_choice_history_equal=(scope!='captures'),examples=examples))
 return dict(kind='forced-public-history-adapter-qualification',strength_evidence=False,cohort=str(COHORT.relative_to(ROOT)),cohort_sha256=sha(COHORT),game=3,scope='One fixed completed C21 screening game,300 decisions per scope across both sides. Frozen mobile-v1 launcher default exact choice parity; quiet modes compare raw ranked choice with frozen template native go and correct reference to the same actual choice before replay. No new games.',results=results,frozen_references={r['policy']['id']:dict(recipe_sha256=r['recipe_sha256'],runtime_sha256=r['runtime_sha256'])for r in(base_receipt,mobile_receipt)},current_sources={name:sha(ROOT/name)for name in('tools/campaign_native_mobile.py','tools/campaign_mobile_capture.py')})
if __name__=='__main__':
 result=run();(HERE/'adapter-history.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['results'],indent=2))
