"""Systematic public-history goal component pilot; no policy or matches."""
import gzip,hashlib,json,re,shlex,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from component import analyze
from campaign_native_template import NativeTemplateBot
from feldmarschall import Engine,parse_square,square_name
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour';POLICY='student-template-flag-bomb-v1-normal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(tmp,spec):
 archive=ROOT/spec['archive'];assert sha(archive)==spec['source_sha256']
 with zipfile.ZipFile(archive)as z:z.extractall(tmp)
 p=tmp/'src/core/ai.c';s=p.read_text();needle='        if(g < -worth[a] / 2) continue;';assert s.count(needle)==1
 callback='''        ai_trace_goal(from,sq,g,distance[sq],previous,
            utility + ((flag_square != NOWHERE && manhattan(sq,flag_square) <= 2 &&
            (!(cell&CELL_REVEALED) || PIECE_TYPE(cell)<PIECE_BOMB)) ? 40 : 0)
            - (int16_t)distance[sq]*3 + (sq==previous ? 8 : 0),
            !(g < -worth[a]/2));
'''
 s=s.replace('static uint8_t plan(uint8_t from) {','extern void ai_trace_goal(uint8_t,uint8_t,int16_t,uint8_t,uint8_t,int16_t,uint8_t);\nstatic uint8_t plan(uint8_t from) {').replace(needle,callback+needle);p.write_text(s)
 p=tmp/'src/native/engine.c';s=p.read_text();marker='void ai_trace_plan(';i=s.index(marker)
 s=s[:i]+'''void ai_trace_goal(uint8_t from,uint8_t goal,int16_t g,uint8_t steps,uint8_t previous,int16_t utility,uint8_t accepted) {
    if(tracing==2) fprintf(stderr,"goalrow %u %u %d %u %u %d %u\\n",from,goal,g,steps,previous,utility,accepted);
}
'''+s[i:];p.write_text(s)
 observer=tmp/'observer';command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(tmp/'src/core'),*['-D'+v for v in spec['defines']+['AI_TRACE']],*[str(tmp/p)for p in spec['sources']],'-o',str(observer)]
 completed=subprocess.run(command,check=True,capture_output=True,text=True)
 return observer,dict(frozen_archive_sha256=sha(archive),observer_sha256=sha(observer),modified_copied_source_sha256={n:sha(tmp/n)for n in('src/core/ai.c','src/native/engine.c')},only_added_public_readonly_callback=True,compile_command=command,stderr=completed.stderr)
def parse(text):return None if text=='none'else tuple(map(parse_square,text.split()))
def run():
 protocol=json.loads((HERE/'PROTOCOL.json').read_text());assert sha(COHORT)==protocol['cohort_sha256'];counts=Counter();records=[];opportunities=[];start=time.perf_counter()
 spec=json.loads((COHORT.parent/'frozen-policies.json').read_text())[POLICY];directory=ROOT/'build/ai-catalog'/POLICY;receipt=json.loads((directory/'build.json').read_text())
 for name,expected in receipt['runtime_sha256'].items():assert sha(directory/name)==expected
 workspace={str(p):sha(p)for p in(ROOT/'src').rglob('*')if p.is_file()}
 with tempfile.TemporaryDirectory(prefix='template-mobile-goal-pilot-')as tmptext:
  tmp=Path(tmptext);observer,buildreport=build(tmp,spec)
  with Tournament(COHORT)as saved:
   for identity in protocol['game_ids']:
    game=saved.game(identity);states,_=replay(game);events=public_events(game,states);army=int(game['blue']==POLICY);log=tmp/('trace-'+str(identity)+'.log');offset=0
    candidate=NativeTemplateBot(Engine(shlex.quote(str(observer))+' 2>'+shlex.quote(str(log))));reference=Engine(shlex.quote(str(directory/'engine')));ordinal=0
    try:
     for line in('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):reference.send(line);candidate.observe(line.split())
     for ply,event in enumerate(events):
      if ply%2==army:
       ordinal+=1;sampled=ordinal<=181 and ordinal%20==1
       if sampled:
        before=bytes.fromhex(candidate.observer.ask('strategy','strategy'));candidate.observer.send('trace on')
       expected=parse(reference.ask('go','move'));chosen=candidate.choose();assert chosen==expected,(identity,ply,'choice');counts['persistent_prefix_decisions']+=1
       if sampled:
        candidate.observer.send('trace off');text=log.read_text()[offset:];offset=log.stat().st_size;goalrows=[];plans={};scores={}
        for line in text.splitlines():
         if line.startswith('goalrow '):goalrows.append(tuple(map(int,line.split()[1:])))
         m=re.match(r'plan (\d+) goal=(\d+) previous=(\d+) steps=(\d+) utility=(-?\d+)',line)
         if m:source,*row=map(int,m.groups());plans[source]=row
         m=re.match(r'candidate (\d+) (\d+) (-?\d+)',line)
         if m:source,target,score=map(int,m.groups());scores[source,target]=score
        report=candidate.last_report;cells=list(bytes.fromhex(report['public_board_hex']));lost=list(bytes.fromhex(report['lost_hex']));remaining=report['remaining'];flag=report['q12']['flag'];bomb=report['q12']['bomb'];marginals=report['marginals']
        assert plans or chosen is None
        for source,(_,previous,_,_)in plans.items():assert before[army*100+source]==previous,(identity,ply,source,'persistent previous')
        diag,changed=analyze(cells,army,lost,remaining,marginals,flag,bomb,goalrows,plans,scores,chosen)
        counts['sampled_roots']+=1;counts['actor_plans']+=len(plans);counts['goal_rows']+=len(goalrows);counts['goal_changes']+=sum(r['oldgoal']!=r['newgoal']for r in diag);counts['target_rejection_changes']+=sum(r['rejection_changes']for r in diag)
        counts['strict_same_actor_quiet_changes']+=len(changed);counts['actual_native_actor_quiet_changes']+=sum(r['actual_native_quiet']for r in changed)
        fixture=dict(cells=cells,lost=lost,remaining=remaining,flag=flag,bomb=bomb,marginals=marginals,strategy_before_hex=before.hex(),native_selected=chosen,native_goalrows=goalrows,native_plans=plans,native_scores=[dict(move=m,score=v)for m,v in scores.items()])
        records.append(dict(game=identity,army=army,ply=ply,ordinal=ordinal,public_fixture=fixture,actor_diagnostics=diag))
        opportunities.extend(dict(game=identity,army=army,ply=ply,ordinal=ordinal,**row)for row in changed)
       actual=tuple(game['moves'][ply])
       if chosen!=actual:
        line='played '+' '.join(map(square_name,actual));reference.ask(line,'playedok');candidate.observe(line.split())
       assert reference.ask('public','public')==candidate.observer.ask('public','public'),(identity,ply,'public history')
       if ordinal>=181:break
      reference.send(event);candidate.observe(event.split())
    finally:reference.close();candidate.close()
    counts['games']+=1;print(json.dumps(dict(games=counts['games'],sampled=counts['sampled_roots'],opportunities=counts['strict_same_actor_quiet_changes'],seconds=time.perf_counter()-start)),flush=True)
  assert workspace=={str(p):sha(p)for p in(ROOT/'src').rglob('*')if p.is_file()}
  (HERE/'temporary-source-binding.json').write_text(json.dumps(buildreport,indent=2)+'\n')
 with gzip.GzipFile(filename=str(HERE/'public-component-fixtures.json.gz'),mode='wb',mtime=0)as f:f.write((json.dumps(records,separators=(',',':'))+'\n').encode())
 result=dict(kind='persistent-native-goal-public-component-pilot',strength_evidence=False,runtime_policy=False,counts=dict(counts),opportunity_games=len({r['game']for r in opportunities}),actual_native_actor_opportunity_games=len({r['game']for r in opportunities if r['actual_native_quiet']}),all_prefix_native_choices_and_public_histories_match_frozen=True,native_goal_previous_utility_gain_rejection_and_route_parity=True,workspace_src_all_hashes_unchanged=True,elapsed_seconds=time.perf_counter()-start,cohort_sha256=sha(COHORT),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'component.py',HERE/'PROTOCOL.json',HERE/'SOURCE-FREEZE.json')},opportunities=opportunities)
 (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('opportunities','sources')},indent=2))
if __name__=='__main__':run()
