"""Post-hoc public guard/breach encounters; no causal trajectory alignment."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import battle,setup_squares,GLYPHS
from tournament_store import Tournament,replay
BASE=ROOT/'docs/ai-honest-campaign-2026-10-16'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def score(game,identity):return None if game['result']=='error'else .5 if game['result']=='draw'else float(game[game['result']]==identity)

def activity(game,identity,guard_origin):
 army=int(game['blue']==identity);own=game[('red_setup','blue_setup')[army]];squares=setup_squares(army);guard_square=squares[guard_origin];flag_square=squares[own.index('F')]
 inner={squares[i]for i,g in enumerate(own)if g=='B'and abs(squares[i]//10-flag_square//10)+abs(squares[i]%10-flag_square%10)==1}
 states,_=replay(game)
 # Only owners/occupancy identify tokens initially. Enemy rank bits have no
 # authority until an actual recorded battle makes BOTH ranks public.
 tokens={square:(piece[0],square)for square,piece in enumerate(states[0])if piece is not None};guard=tokens[guard_square];flag=tokens[flag_square];breacher_history={};breaches=[];engagements=[];combats=[];first_move=None;flag_loss=None
 for ply,(source,target)in enumerate(game['moves']):
  attacker=tokens.pop(source);defender=tokens.get(target)
  if attacker==guard and first_move is None:first_move=ply+1
  if defender is None:tokens[target]=attacker;continue
  # These are publicly disclosed combat ranks, not inferred concealed types.
  attacker_rank=states[ply][source][1];defender_rank=states[ply][target][1];outcome=battle(attacker_rank,defender_rank)
  if defender[0]==army and target in inner and defender_rank==10 and attacker_rank==7 and outcome=='attacker':
   location=next((sq for sq,token in tokens.items()if token==guard),None)
   event=dict(ply=ply+1,gate_square=target,enemy_rank=7,guard_alive=location is not None,guard_at_original_post=location==guard_square,guard_adjacent_to_gate=location is not None and abs(location//10-target//10)+abs(location%10-target%10)==1);breaches.append(event);breacher_history[attacker]=event
  if guard in(attacker,defender):
   attacking=guard==attacker;enemy=defender if attacking else attacker;enemy_rank=defender_rank if attacking else attacker_rank;survives=outcome==('attacker'if attacking else'defender')
   event=dict(ply=ply+1,guard_role='attacker'if attacking else'defender',enemy_rank=enemy_rank,guard_survives=survives,outcome=outcome)
   combats.append(event)
   if enemy in breacher_history:
    breach=breacher_history[enemy];engagements.append(dict(**event,breach_ply=breach['ply'],breached_gate=breach['gate_square'],plies_after_breach=ply+1-breach['ply'],at_original_gate=(target if attacking else source)==breach['gate_square']))
  if defender==flag and outcome=='attacker':flag_loss=dict(ply=ply+1,public_attacker_rank=attacker_rank,guard_still_alive_before_flag_capture=guard in tokens.values())
  if outcome=='attacker':tokens[target]=attacker
  elif outcome=='both':tokens.pop(target)
 return dict(game=game['id'],pair_id=game['pair_id'],army=army,score=score(game,identity),result=game['result'],reason=game['reason'],plies=len(game['moves']),error_prefix=game['result']=='error',guard_origin=guard_origin,guard_rank=GLYPHS.index(own[guard_origin]),guard_first_move_ply=first_move,guard_combats=combats,inner_breaches=breaches,guard_breacher_engagements=engagements,own_flag_loss=flag_loss)

def summarize(rows):
 engagements=[event for row in rows for event in row['guard_breacher_engagements']];combats=[event for row in rows for event in row['guard_combats']];flaglosses=[row['own_flag_loss']for row in rows if row['own_flag_loss']]
 return dict(attempts=len(rows),error_prefixes=sum(r['error_prefix']for r in rows),games_guard_moved=sum(r['guard_first_move_ply']is not None for r in rows),games_guard_had_public_combat=sum(bool(r['guard_combats'])for r in rows),
  inner_breach_events=sum(len(r['inner_breaches'])for r in rows),breaches_guard_alive=sum(e['guard_alive']for r in rows for e in r['inner_breaches']),breaches_guard_at_original_post=sum(e['guard_at_original_post']for r in rows for e in r['inner_breaches']),breaches_guard_adjacent_to_gate=sum(e['guard_adjacent_to_gate']for r in rows for e in r['inner_breaches']),games_with_inner_breach=sum(bool(r['inner_breaches'])for r in rows),guard_breacher_engagements=len(engagements),guard_survives_breacher_engagement=sum(e['guard_survives']for e in engagements),
  immediate_guard_replies_at_breached_gate=sum(e['guard_role']=='attacker'and e['plies_after_breach']==1 and e['at_original_gate']for e in engagements),
  public_enemy_ranks_in_guard_combats=dict(Counter(e['enemy_rank']for e in combats)),own_flag_capture_losses=len(flaglosses),public_flag_capturer_ranks=dict(Counter(e['public_attacker_rank']for e in flaglosses)))

def run():
 allresults={};sourcepins={}
 for cycle in(110,114):
  directory=next(BASE.glob('cycle-'+str(cycle)+'*'));plan=json.loads((directory/'plan.json').read_text());baseline,candidate=plan['baseline'],plan['contrasts'][0][0];games={}
  for identity in(baseline,candidate):
   path=directory/(identity+'.fmtour');sourcepins[str(path.relative_to(ROOT))]=sha(path)
   with Tournament(path)as store:games[identity]={row['id']:store.game(row['id'])for row in store.games()}
  records={baseline:[],candidate:[]};changed=[]
  for game_id in sorted(games[baseline]):
   a,b=games[baseline][game_id],games[candidate][game_id];army=int(a['blue']==baseline);own_key=('red_setup','blue_setup')[army];owna,ownb=a[own_key],b[own_key];difference=[i for i in range(40)if owna[i]!=ownb[i]];assert len(difference)==2
   guard=[i for i in difference if owna[i]=='8'and ownb[i]=='7'];assert len(guard)==1
   rows={identity:activity(games[identity][game_id],identity,guard[0])for identity in(baseline,candidate)}
   for identity,row in rows.items():records[identity].append(row)
   if rows[baseline]['score']is not None and rows[candidate]['score']is not None and rows[baseline]['score']!=rows[candidate]['score']:
    changed.append(dict(game=game_id,baseline=rows[baseline],candidate=rows[candidate]))
  allresults[cycle]=dict(arms={identity:summarize(rows)for identity,rows in records.items()},score_changed_matched_games=len(changed),
   score_changed_game_loss_endings={identity:summarize([r[('baseline'if identity==baseline else'candidate')]for r in changed if r[('baseline'if identity==baseline else'candidate')]['score']==0])for identity in(baseline,candidate)},records=records)
 result=dict(kind='posthoc-public-inner-guard-breach-activity',strength_evidence=False,causal_mechanism_attribution=False,source_pins=sourcepins,cycles=allresults,
  limits='Own initial formations differ; no same-root trajectory or first-divergent-choice attribution is made. Counts are descriptive, include legal error prefixes, and are correlated within games. Enemy ranks are consulted only at actual public battles. Initial token tracking uses owner/occupancy only. No placement tuning or new policy.')
 out=BASE/'research/evaluation/inner-guard-public-activity.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({n:{k:v for k,v in row.items()if k!='records'}for n,row in allresults.items()},indent=2))
if __name__=='__main__':run()
