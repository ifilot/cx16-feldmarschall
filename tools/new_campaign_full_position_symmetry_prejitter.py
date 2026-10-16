"""Prospectively fixed, fresh-memory public-position reflection component."""
import copy,difflib,hashlib,importlib.util,json,shlex,sys,tempfile,time,subprocess,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
HERE=ROOT/'docs/ai-honest-campaign-2026-10-16/research/full-position-symmetry-prejitter'
spec=importlib.util.spec_from_file_location('old_runtime_audit',HERE.parent/'objectives/audit_runtime.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
from ai_registry import build_policy,get_policy
from campaign_native_template import NativeTemplateBot
from feldmarschall import Engine,Position,parse_square,square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

def mirror(s):return s//10*10+9-s%10 if 0<=s<100 else s

def action(a):return None if a is None else tuple(map(mirror,a))

def reflect(values):return [values[mirror(s)] for s in range(100)]

def mirrored_position(p):
 q=Position();q.cells=copy.deepcopy(reflect(p.cells));q.shuttle={a:(mirror(s)if s is not None else None,mirror(t)if t is not None else None,n)for a,(s,t,n)in p.shuttle.items()};return q

def public_position(board,shuttle):
 p=Position();p.cells=[None if c>=254 else [int(bool(c&16)),c&15,bool(c&64),bool(c&32)]for c in board]
 for a in (0,1):p.shuttle[a]=(shuttle[a],shuttle[a+2],shuttle[a+4])
 return p

def referee_tests():
 n=0
 for army in (0,1):
  for attacker in range(10):
   for defender in range(12):
    p=Position();p.cells[44]=[army,attacker,False,True];p.cells[45]=[1-army,defender,False,True];q=mirrored_position(p)
    assert (44,45)in p.moves(army)and(45,44)in q.moves(army)
    result=p.fight(44,45,attacker,defender);other=q.fight(45,44,attacker,defender)
    assert result==other and mirrored_position(p).cells==q.cells and mirrored_position(p).shuttle==q.shuttle;n+=1
 return n

def build_base_trace(directory,policy):
 source=directory/'source';source.mkdir();archive=ROOT/policy['archive'];assert helper.sha(archive)==policy['source_sha256']
 with zipfile.ZipFile(archive)as bundle:bundle.extractall(source)
 patches=[];bindings={}
 for relative in ('src/core/ai.c','src/native/engine.c'):
  path=source/relative;old=path.read_text()
  if relative.endswith('/ai.c'):
   target='    return s + (random_next() & (ai_difficulty == AI_EASY ? 31 : 7));'
   assert old.count(target)==1
   new=old.replace(target,'    { extern void ai_trace_base(uint8_t from, uint8_t to, int16_t score); ai_trace_base(from,to,s); }\n'+target)
  else:
   target='void ai_trace(uint8_t from, uint8_t to, int16_t score) {';assert old.count(target)==1
   new=old.replace(target,'void ai_trace_base(uint8_t from,uint8_t to,int16_t score) { if(tracing == 1) printf("base %u %u %d\\n",from,to,score); }\n'+target)
  path.write_text(new);patches.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative));bindings[relative]=dict(original_sha256=hashlib.sha256(old.encode()).hexdigest(),instrumented_sha256=helper.sha(path))
 (HERE/'trace-only.patch').write_text(''.join(patches))
 observer=directory/'base-trace-observer';command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow','-Isrc/core',*['-D'+d for d in policy['defines']],'-DAI_TRACE','-o',str(observer),*policy['sources']]
 subprocess.run(command,cwd=source,check=True,capture_output=True,text=True)
 return observer,dict(archive_sha256=helper.sha(archive),observer_sha256=helper.sha(observer),command=command,trace_only_patch_sha256=helper.sha(HERE/'trace-only.patch'),changed_files=bindings,random_return_expression_unchanged=True)

def evaluate(engine,army,board,lost,shuttle,packet,seed,ranked):
 engine.send('rules 0');engine.send('difficulty normal')
 engine.ask(f'position {army} {lost} {bytes(board).hex()} {bytes(shuttle).hex()}','positionok')
 engine.send('seed '+str(seed));engine.ask('belief-priors '+packet,'belief-priorsok')
 scores={};base={}
 if ranked:
  engine.send('ranked')
  while True:
   words=engine.read().split()
   if words[0]=='base':base[tuple(map(int,words[1:3]))]=int(words[3])
   elif words[0]=='candidate':scores[tuple(map(int,words[1:3]))]=int(words[3])
   elif words[0]=='move':move=helper.parse(' '.join(words[1:]));break
   elif words[0]=='error':raise AssertionError(words)
 else:move=helper.parse(engine.ask('go','move'))
 return move,scores,base

def run():
 protocol=json.loads((HERE/'PROTOCOL.json').read_text());policy=get_policy(protocol['reference']);launcher,receipt=build_policy(policy['id']);counts=Counter();rows=[];started=time.monotonic()
 counts['synthetic_disclosed_combat_pairs']=referee_tests()
 with tempfile.TemporaryDirectory(prefix='public-symmetry-')as tmp:
  trace,binding=build_base_trace(Path(tmp),policy)
  diagnostic=Engine(shlex.quote(str(trace)));frozen=Engine(shlex.quote(str(launcher.parent/'observer')))
  try:
   with Tournament(ROOT/protocol['history'])as store:
    for identity in protocol['game_ids']:
     game=store.game(identity);army=int(game['blue']=='student-template-flag-bomb-v1-normal');states,_=replay(game);events=public_events(game,states);bot=NativeTemplateBot(launcher.parent/'observer');ordinal=0
     try:
      for line in ('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),'setup '+game[('red_setup','blue_setup')[army]]):bot.observe(line.split())
      for ply,event in enumerate(events):
       if ply%2==army:
        ordinal+=1
        public=bot.observer.ask('public','public').split();selected=bot.choose()
        if ordinal in protocol['sample_own_ordinals']:
         report=bot.last_report;board=list(bytes.fromhex(report['public_board_hex']));shuttle=list(bytes.fromhex(public[3]));lost=report['lost_hex'];packet=''.join(f'{v:04x}'for key in ('flag','bomb')for v in report['q12'][key]);assert hashlib.sha256(packet.encode()).hexdigest()==report['packet_sha256']
         assert all(c>=254 or bool(c&16)==bool(army)or c&32 or c&15==12 for c in board)
         mirrored_board=reflect(board);mirrored_shuttle=[mirror(s)for s in shuttle[:4]]+shuttle[4:];mirrored_packet=''.join(f'{v:04x}'for key in ('flag','bomb')for v in reflect(report['q12'][key]))
         p=public_position(board,shuttle);q=public_position(mirrored_board,mirrored_shuttle);legal=set(p.moves(army));assert {action(a)for a in legal}==set(q.moves(army));counts['legal_set_symmetry']+=1
         for move in legal:
          if p.cells[move[1]] is None:
           x=copy.deepcopy(p);y=copy.deepcopy(q);x.move(*move);y.move(*action(move));assert mirrored_position(x).cells==y.cells and mirrored_position(x).shuttle==y.shuttle;counts['quiet_transition_symmetry']+=1
         choices=[];scores=[];bases=[]
         for b,s,packet_this in ((board,shuttle,packet),(mirrored_board,mirrored_shuttle,mirrored_packet)):
          choice,score,base=evaluate(diagnostic,army,b,lost,s,packet_this,game['seed'],True)
          control,_,_=evaluate(frozen,army,b,lost,s,packet_this,game['seed'],False);assert choice==control;counts['trace_frozen_choice_parity']+=1
          assert set(score)==set(public_position(b,s).moves(army));assert choice is None or choice in score
          assert set(base)==set(score);assert all(0<=score[a]-base[a]<=7 for a in score)
          choices.append(choice);scores.append(score);bases.append(base)
         counterpart=action(choices[0]);changed=counterpart!=choices[1];mapped={action(a):value for a,value in scores[0].items()};different=sum(value!=scores[1][a]for a,value in mapped.items());counts['roots']+=1;counts['army_'+str(army)]+=1;counts['changed_choices']+=changed;counts['roots_with_changed_candidate_scores']+=bool(different);counts['candidate_scores']+=len(mapped);counts['changed_candidate_scores']+=different
         base_changed=sum(value!=bases[1][action(a)]for a,value in bases[0].items());counts['changed_base_scores']+=base_changed;counts['roots_with_changed_base_scores']+=bool(base_changed);counts['changed_choices_with_equivalent_base_map']+=bool(changed and not base_changed)
         base_tie=bool(changed and bases[1][counterpart]==bases[1][choices[1]]);counts['changed_choice_equal_base_in_mirrored_frame']+=base_tie
         tie=bool(changed and scores[1][counterpart]==scores[1][choices[1]]);counts['changed_choice_equal_score_in_mirrored_frame']+=tie
         rows.append(dict(game=identity,army=army,ply=ply,ordinal=ordinal,original_choice=choices[0],reflected_counterpart=counterpart,mirrored_choice=choices[1],changed_choice=changed,candidates=len(mapped),different_candidate_scores=different,different_base_scores=base_changed,mirrored_counterpart_base=bases[1].get(counterpart),mirrored_selected_base=bases[1].get(choices[1]),equal_base_in_mirrored_frame=base_tie,mirrored_counterpart_score=scores[1].get(counterpart),mirrored_selected_score=scores[1].get(choices[1]),equal_score_in_mirrored_frame=tie,public_packet_sha256=report['packet_sha256']))
        actual=tuple(game['moves'][ply])
        if selected!=actual:bot.observe(('played '+' '.join(map(square_name,actual))).split())
        if ordinal>=protocol['maximum_own_decisions']:break
       bot.observe(event.split())
     finally:bot.close()
     counts['games']+=1
     if counts['games']%8==0:print(json.dumps(dict(counts)),flush=True)
  finally:diagnostic.close();frozen.close()
 result=dict(kind='fresh-public-full-position-horizontal-prejitter',strength_evidence=False,persistent_symmetry_evidence=False,counts=dict(counts),protocol_sha256=helper.sha(HERE/'PROTOCOL.json'),cohort_sha256=helper.sha(ROOT/protocol['history']),source_binding=binding,policy=policy,build_receipt=receipt,elapsed_seconds=time.monotonic()-started,records=rows)
 (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(counts),indent=2))
if __name__=='__main__':run()
