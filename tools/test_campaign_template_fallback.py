"""Macro-on disabled-prior move/RNG parity, with public histories and late roots."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from feldmarschall import Engine,GLYPHS
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-target-prototype-v1'

def main():
 records=[]
 with tempfile.TemporaryDirectory(prefix='template-fallback-') as name:
  t=Path(name);source=(ROOT/'src/native/engine.c').read_text()
  source=source.replace('} else if(!strcmp(command, "seed")) {','} else if(!strcmp(command, "fixture-rng")) {\n printf("rng %u\\n",random_current());fflush(stdout);\n } else if(!strcmp(command, "seed")) {')
  assert 'printf("rng %u' in source
  (t/'engine.c').write_text(source)
  flags=['AI_TEST','AI_DIAGNOSTICS','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2','AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD']
  files=['pieces','board','rules','setup','random','ai','ai_level','ai_deploy','ai_mission','ai_memory','ai_student','ai_template']
  for mode in ('off','on'):
   cmd=['cc','-O2','-std=c99','-Wno-unknown-pragmas','-I'+str(ROOT/'src/core')]+['-D'+f for f in flags+(['AI_TEMPLATE_PRIOR_Q24'] if mode=='on' else [])]+['-o',str(t/mode),str(t/'engine.c')]+[str(ROOT/'src/core'/(f+'.c')) for f in files]
   subprocess.run(cmd,check=True,capture_output=True)
  with Tournament(ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour') as tour:
   row=next(r for r in tour.games() if r['result']!='error' and r['plies']>=80);game=tour.game(row['id']);states,_=replay(game);events=public_events(game,states)
  for level in ('easy','hard'):
   for army in (0,1):
    bots=[Engine(str(t/m)) for m in ('off','on')]
    try:
     for bot in bots:
      for c in ['new '+('red','blue')[army],'rules 0','difficulty '+level,'seed 19281','setup '+game[('red_setup','blue_setup')[army]]]:bot.send(c)
     for ply,event in enumerate(events[:80]):
      if ply%2==army:
       moves=[b.ask('go','move') for b in bots];rng=[b.ask('fixture-rng','rng') for b in bots]
       assert moves[0]==moves[1] and rng[0]==rng[1],(level,army,ply,moves,rng)
       assert bots[1].ask('template-prior','prior').split()[0]=='0'
       records.append(dict(kind='public-history',level=level,army=army,ply=ply,move=moves[0],rng=rng[0]))
       for b in bots:b.ask('played '+' '.join(event.split()[1:3]),'playedok')
      for b in bots:b.send(event)
    finally:
     for b in bots:b.close()
  # No initial-origin context: raw public root must conservatively use native counts.
  for level in ('easy','normal','hard'):
   for rules in (0,1):
    for army in (0,1):
     bots=[Engine(str(t/m)) for m in ('off','on')]
     try:
      state=states[40]
      view=bytes(254 if sq in (42,43,52,53,46,47,56,57) else 255 if c is None else c[0]*16+(c[1] if c[0]==army or c[3] else 12)+64*c[2]+32*c[3] for sq,c in enumerate(state)).hex()
      from feldmarschall import COUNTS
      lost=bytes(n-sum(c is not None and c[0]!=army and c[1]==r for c in state) for r,n in enumerate(COUNTS)).hex()
      results=[]
      for bot in bots:
       bot.send('difficulty '+level);bot.send('rules '+str(rules))
       results.append((bot.ask('think %d 32871 %s %s 3'%(army,lost,view),'best'),bot.ask('fixture-rng','rng')))
      assert results[0]==results[1],(level,rules,army,results)
      status=int(bots[1].ask('template-prior','prior').split()[0]);assert status in (0,1)
      records.append(dict(kind='missing-history',level=level,rules=rules,army=army,move=results[0][0],rng=results[0][1],status=status))
     finally:
      for b in bots:b.close()
  result=dict(success=True,records=records,checks=len(records),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/native/engine.c']+[ROOT/'src/core'/(f+'.c') for f in files]},note='RNG diagnostic injected only into private copied engine source; actual policy sources unmodified. Optional-rule cases are mechanical disabled-model fallback checks, not rule research.')
  (OUT/'fallback-parity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(success=True,checks=len(records))))
if __name__=='__main__':main()
