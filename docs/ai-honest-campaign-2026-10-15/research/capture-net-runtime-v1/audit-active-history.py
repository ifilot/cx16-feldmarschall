"""One-search/actual-choice/RNG parity for fork scope on fixed public history."""
import hashlib,json,shlex,subprocess,sys,tempfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import get_policy
from campaign_native_mobile import MobileCaptureBot
from feldmarschall import Engine,parse_square,square_name
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
HERE=Path(__file__).resolve().parent
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
class Counted:
 def __init__(self,engine):self.engine=engine;self.commands=[]
 def send(self,line):self.commands.append(line);return self.engine.send(line)
 def ask(self,line,prefix):self.commands.append(line);return self.engine.ask(line,prefix)
 def read(self):return self.engine.read()
 def close(self):return self.engine.close()
def run():
 spec=get_policy('student-template-flag-bomb-v1-normal');directory=ROOT/'build/ai-catalog'/spec['id'];receipt=json.loads((directory/'build.json').read_text())
 for name,sha in receipt['runtime_sha256'].items():assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==sha
 with Tournament(COHORT)as saved:game=saved.game(2)
 states,_=replay(game);events=public_events(game,states);counts=Counter()
 with tempfile.TemporaryDirectory(prefix='fork-active-history-')as tmp:
  observer=Path(tmp)/'observer'
  subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core'),*['-D'+v for v in spec['defines']+['AI_TRACE','AI_TRAINING']],*[str(ROOT/p)for p in spec['sources']],'-o',str(observer)],check=True,capture_output=True)
  for army in(0,1):
   reference=Engine(shlex.quote(str(directory/'engine')));counted=Counted(Engine(shlex.quote(str(observer))));candidate=MobileCaptureBot(counted,adjustment_scope='quiet-net')
   try:
    for line in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):reference.send(line);candidate.observe(line.split())
    for ply,event in enumerate(events[:300]):
     if ply%2==army:
      counted.commands=[];raw=tuple(map(parse_square,reference.ask('go','move').split()));selected=candidate.choose();report=candidate.last_report
      assert raw==tuple(report['native_selected']),(army,ply,raw,report['native_selected'])
      assert counted.commands.count('ranked')==1 and not any(line=='go'or line.startswith('seed ')for line in counted.commands)
      assert sum(line.startswith('played ')for line in counted.commands)==int(selected!=raw)
      counts['decisions']+=1;counts['overrides']+=selected!=raw;counts[report['quiet_adjustment'].get('phase','unknown')]+=1
      if selected!=raw:reference.ask('played '+' '.join(map(square_name,selected)),'playedok')
      actual=tuple(game['moves'][ply])
      if selected!=actual:
       correction='played '+' '.join(map(square_name,actual));reference.ask(correction,'playedok');candidate.observe(correction.split())
      assert reference.ask('public','public')==candidate.observer.ask('public','public')
     reference.send(event);candidate.observe(event.split())
   finally:reference.close();candidate.close()
 assert counts['decisions']==300
 return dict(kind='net-actual-public-history-parity',strength_evidence=False,counts=dict(counts),game=2,both_armies=True,one_ranked_per_decision=True,played_iff_override=True,raw_native_and_actual_choice_history_and_public_states_equal=True,no_extra_go_seed_or_rng=True,scope='Forced recorded C21 public histories; choices are corrected to the historical action after each diagnostic. Stale plans are discarded by played correction. No new games.',cohort_sha256=hashlib.sha256(COHORT.read_bytes()).hexdigest(),sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in('tools/campaign_native_mobile.py','tools/campaign_mobile_capture.py','tools/campaign_capture_net.py')})
if __name__=='__main__':
 result=run();(HERE/'active-history.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
