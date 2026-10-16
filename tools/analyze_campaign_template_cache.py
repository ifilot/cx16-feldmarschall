"""Historical public replay: exact cache V2 versus frozen V1, not strength games."""
from pathlib import Path
import hashlib,json,subprocess,time
from collections import Counter
from feldmarschall import Engine
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-target-cache-v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 old=Path('/tmp/template-target-rng-probe');binding=json.loads((OUT.parent/'template-target-prototype-v1/rng-probe-binding.json').read_text());assert sha(old)==binding['private_probe_binary_sha256']
 source=Path('/tmp/template-target-rng-probe.c').read_text().replace('} else if(!strcmp(command, "fixture-rng")) {','} else if(!strcmp(command, "fixture-cache")) {\n printf("cache %u\\n",ai_template_test_cache_hit());fflush(stdout);\n } else if(!strcmp(command, "fixture-rng")) {')
 probe=OUT/'cache-probe-engine.c';probe.write_text(source)
 flags=['AI_TEST','AI_DIAGNOSTICS','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2','AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD','AI_TEMPLATE_PRIOR_Q24','AI_TEMPLATE_PRIOR_Q24_CACHE']
 files=['pieces','board','rules','setup','random','ai','ai_level','ai_deploy','ai_mission','ai_memory','ai_student','ai_template']
 new=Path('/tmp/template-cache-probe');cmd=['cc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core')]+['-D'+f for f in flags]+['-o',str(new),str(probe)]+[str(ROOT/'src/core'/(f+'.c')) for f in files];subprocess.run(cmd,check=True,capture_output=True)
 spec=json.loads((OUT.parent/'horizon/quiescence-mechanism.json').read_text());selections={}
 for r in spec['roots']:selections[(r['game'],r['army'])]=max(r['ply'],selections.get((r['game'],r['army']),0))
 records=[];seconds=Counter()
 with Tournament(ROOT/spec['source']) as tour:
  for (gameid,army),end in sorted(selections.items()):
   game=tour.game(gameid);states,_=replay(game);events=public_events(game,states);bots=[Engine(str(old)),Engine(str(new))]
   try:
    for b in bots:
     for c in ['new '+('red','blue')[army],'rules 0','difficulty normal','seed '+str(game['seed']*2+army+1),'setup '+game[('red_setup','blue_setup')[army]]]:b.send(c)
    for ply,event in enumerate(events[:end+1]):
     if ply%2==army:
      moves=[];priors=[];rng=[]
      for i,b in enumerate(bots):
       begin=time.perf_counter();moves.append(b.ask('go','move'));seconds[str(i)]+=time.perf_counter()-begin
       priors.append(b.ask('template-prior','prior'));rng.append(b.ask('fixture-rng','rng'))
      assert moves[0]==moves[1] and priors[0]==priors[1] and rng[0]==rng[1],(gameid,army,ply)
      hit=int(bots[1].ask('fixture-cache','cache'));records.append(dict(game=gameid,army=army,ply=ply,hit=hit,move=moves[0],rng=rng[0],status=int(priors[1].split()[0])))
      for b in bots:b.ask('played '+' '.join(event.split()[1:3]),'playedok')
     for b in bots:b.send(event)
   finally:
    for b in bots:b.close()
 report=dict(schema='template-cache-public-replay-v2',strength_evidence=False,source=spec['source'],source_sha256=spec['source_sha256'],old_binary_sha256=sha(old),new_binary_sha256=sha(new),probe_source_sha256=sha(probe),command=cmd,summary=dict(decisions=len(records),hits=sum(r['hit'] for r in records),misses=sum(not r['hit'] for r in records),moves_rng_q12_cache_all_identical=True,wall_seconds=dict(seconds)),records=records)
 (OUT/'historical-parity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary']))
if __name__=='__main__':main()
