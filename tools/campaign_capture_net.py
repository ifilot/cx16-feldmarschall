"""Frozen public capture-net gate and conservative bounded conversion proof."""
from feldmarschall import battle,TWO_SQUARES
from campaign_belief_values import worths
from campaign_mobile_capture import (_fork_adjacent,_fork_danger,_fork_record,
 _fork_own_moves,_fork_successors,_fork_public_key,_fork_enemy_lost,
 _fork_valid_inventory,_fork_feasible,_fork_shuttle,_ForkLimit)

def capture(cells,army,source,target,shuttle):
 """Exact legal own surviving capture geometry; target is disclosed."""
 cell=cells[source];victim=cells[target]
 if cell>=254 or bool(cell&16)!=bool(army)or victim>=254 or bool(victim&16)==bool(army)or not victim&32:return False
 rank=cell&15
 if rank>=10 or battle(rank,victim&15)!='attacker':return False
 last_source,last_target,count=shuttle
 if count>=TWO_SQUARES and source==last_target and target==last_source:return False
 distance=abs(source//10-target//10)+abs(source%10-target%10)
 if distance==1:return True
 if rank!=8 or(source//10!=target//10 and source%10!=target%10):return False
 step=(1 if target>source else -1)if source//10==target//10 else(10 if target>source else -10)
 return all(cells[square]==255 for square in range(source+step,target,step))

def candidates(cells,army,lost,remaining,moves,parent,shuttle):
 if not _fork_valid_inventory(cells,army,lost,remaining):raise ValueError('inconsistent public state')
 if parent is None or cells[parent[1]]!=255:return []
 flags=[s for s,c in enumerate(cells)if c<254 and bool(c&16)==bool(army)and c&15==11]
 if len(flags)!=1 or _fork_danger(cells,army,remaining,flags[0],11,shuttle[1-army],True):return []
 result=[]
 for source,target in sorted(moves):
  if cells[target]!=255:continue
  rank=cells[source]&15
  victims=[v for v in _fork_adjacent(target)if cells[v]<254 and bool(cells[v]&16)!=bool(army)and cells[v]&32 and cells[v]&15<10 and cells[v]&15!=8 and battle(rank,cells[v]&15)=='attacker']
  if not victims:continue
  after=cells[:];after[target]=after[source]|64;after[source]=255
  if _fork_danger(after,army,remaining,target,rank,shuttle[1-army]):continue
  updated=_fork_record(shuttle,army,source,target)
  for victim in victims:
   quiet=[v for v in _fork_adjacent(victim)if after[v]==255 and not(shuttle[1-army][2]>=TWO_SQUARES and victim==shuttle[1-army][1]and v==shuttle[1-army][0])]
   if not quiet:continue
   coverage={}
   for destination in [victim]+quiet:
    board=after[:]
    if destination!=victim:board[destination]=board[victim]|64;board[victim]=255
    coverage[destination]={s for s,c in enumerate(board)if c<254 and bool(c&16)==bool(army)and capture(board,army,s,destination,updated[army])}
   if target not in coverage[victim]:continue
   allies=sorted(set.union(*coverage.values())-{target})
   for ally in allies:
    pair={target,ally}
    if all(pair&covered for covered in coverage.values())and any(pair&covered=={target}for covered in coverage.values())and any(pair&covered=={ally}for covered in coverage.values()):
     result.append(dict(move=[source,target],victim=victim,victim_rank=cells[victim]&15,ally=ally,continuations={str(v):sorted(pair&covered)for v,covered in coverage.items()}))
 return sorted(result,key=lambda row:(row['move'],row['victim'],row['ally']))

def own_outcomes(cells,army,remaining,shuttle,move,worth):
 """Same own action in every count-feasible hidden defender branch."""
 source,target=move;actor=cells[source];defender=cells[target]
 if defender==255:
  after=cells[:];after[target]=actor|64;after[source]=255
  if abs(source//10-target//10)+abs(source%10-target%10)>1:after[target]|=32
  yield dict(cells=after,remaining=remaining[:],balance=0,terminal_win=False)
  return
 ranks=[defender&15]if defender&32 else[r for r,n in enumerate(remaining)if n and(not defender&64 or r<10)]
 for rank in ranks:
  rest=remaining[:];known=cells[:];known[target]=(defender&240)|32|rank
  if not defender&32:rest[rank]-=1
  if not _fork_feasible(known,1-army,rest):continue
  after=known[:];after[source]=255;outcome=battle(actor&15,rank)
  balance=(worth[rank]if outcome!='defender'else 0)-(worth[actor&15]if outcome!='attacker'else 0)
  after[target]=(actor|32|64)if outcome=='attacker'else known[target]if outcome=='defender'else 255
  yield dict(cells=after,remaining=rest,balance=balance,terminal_win=rank==11)

def certificate(cells,army,lost,remaining,shuttle,move,budget,candidate=None):
 """Enemy AND / one common public own action OR / outcome+enemy AND."""
 started=budget[0]
 if not _fork_valid_inventory(cells,army,lost,remaining):return dict(certified=False,reason='inconsistent-public-inventory',enemy_nodes=0)
 source,target=move;worth=worths(lost)
 if move not in _fork_own_moves(cells,army,shuttle)or cells[target]!=255:raise ValueError('legal quiet root required')
 actors={target,candidate['ally']}if candidate is not None else None
 victim=candidate['victim']if candidate is not None else None
 after=cells[:];after[target]=after[source]|64;after[source]=255
 if abs(source//10-target//10)+abs(source%10-target%10)>1:after[target]|=32
 updated=_fork_record(shuttle,army,source,target);worst=float('inf');responses=[]
 try:
  first=list(_fork_successors(after,army,remaining,updated,worth,budget))
  if not first:
   win=bool(_fork_own_moves(after,army,updated))
   return dict(certified=win,terminal_win=win,reason='enemy-no-moves'if win else'neither-can-move',enemy_nodes=budget[0]-started,first_public_outcomes=0)
  for reply in first:
   board=reply['cells'];legal=_fork_own_moves(board,army,reply['shuttle'])
   def reject(reason,**extra):return dict(certified=False,reason=reason,counterexample=reply['observation'],enemy_nodes=budget[0]-started,first_public_outcomes=len(first),**extra)
   if reply['flag_loss']or not legal:return reject('first-enemy-terminal-counterwin-or-own-immobility')
   immediate=[m for m in legal if board[m[1]]<254 and board[m[1]]&32 and board[m[1]]&15==11]
   key=_fork_public_key(board,army,_fork_enemy_lost(board,army,reply['remaining']),reply['remaining'],reply['shuttle'])
   if immediate:responses.append(dict(enemy=reply['observation'],response=list(immediate[0]),terminal_win=True,public_key=key));continue
   victim_alive=False;destination=None
   if candidate is not None:
    enemy_source,enemy_target=reply['observation']['move'];destination=enemy_target if enemy_source==victim else victim
    victim_alive=board[destination]<254 and bool(board[destination]&16)!=bool(army)
   response_moves=legal if not victim_alive else[(actor,destination)for actor in sorted(actors)if(actor,destination)in legal and capture(board,army,actor,destination,reply['shuttle'][army])]
   best=-float('inf');best_response=None;failures=[]
   for action in response_moves:
    outcomes=list(own_outcomes(board,army,reply['remaining'],reply['shuttle'],action,worth))
    if not outcomes:raise AssertionError('valid public action has no possible outcome')
    value=float('inf');failure=None
    state=_fork_record(reply['shuttle'],army,*action)
    for outcome in outcomes:
     if outcome['terminal_win']:continue
     balance=reply['balance']+outcome['balance']
     second=list(_fork_successors(outcome['cells'],army,outcome['remaining'],state,worth,budget))
     if not second:
      val=float('inf')if _fork_own_moves(outcome['cells'],army,state)else-float('inf')
      if val<value:value=val;failure=dict(reason='neither-can-move')
     for enemy in second:
      val=balance+enemy['balance']
      if enemy['flag_loss']or not _fork_own_moves(enemy['cells'],army,enemy['shuttle']):val=-float('inf')
      if val<value:value=val;failure=enemy['observation']
    failures.append(dict(response=list(action),minimum_net_material=None if abs(value)==float('inf')else value,terminal_refutation=value==-float('inf'),enemy_response=failure))
    if value>best:best=value;best_response=list(action)
   if best<=0:return reject('no-positive-net-conversion',responses=failures)
   responses.append(dict(enemy=reply['observation'],response=best_response,minimum_net_material=None if best==float('inf')else best,terminal_win=best==float('inf'),public_key=key,victim_alive=victim_alive if candidate is not None else None));worst=min(worst,best)
  if len({row['public_key']for row in responses})!=len(responses):return dict(certified=False,inconclusive=True,reason='ambiguous-public-witness',enemy_nodes=budget[0]-started)
  return dict(certified=True,minimum_net_material=None if worst==float('inf')else worst,terminal_win=worst==float('inf'),enemy_nodes=budget[0]-started,first_public_outcomes=len(first),responses=responses)
 except _ForkLimit:return dict(certified=False,inconclusive=True,reason='prespecified-node-cap',enemy_nodes=budget[0]-started)


def net_selection(cells,army,lost,remaining,scores,parent,shuttle):
 """First public gate candidate only, with generalized optimistic control."""
 report=dict(version='public-quiet-net-v1',overridden=False,enemy_nodes=0,
             scope='Bounded material conversion with one-turn exact-public witness; not game value or global safety.')
 def fallback(reason):
  report['reason']=reason
  return parent,report
 if parent is None:return fallback('no-native-move')
 if parent not in scores:raise ValueError('native move missing from legal candidates')
 if cells[parent[1]]!=255 or scores[parent]>=30000:return fallback('preserve-native-capture-or-terminal')
 if any(score>=30000 for score in scores.values()):return fallback('preserve-terminal-win')
 if not _fork_valid_inventory(cells,army,lost,remaining):return fallback('inconsistent-public-inventory')
 state=_fork_shuttle(shuttle);legal=_fork_own_moves(cells,army,state)
 found=candidates(cells,army,lost,remaining,legal,parent,state)
 report['eligible_candidates']=len(found)
 if not found:return fallback('no-public-net')
 first=found[0];move=tuple(first['move']);report['first_candidate']=first
 if move not in scores:return fallback('first-candidate-absent-native-scores')
 budget=[0,20000]
 control=certificate(cells,army,lost,remaining,state,parent,budget)
 report['native_certificate']=control;report['enemy_nodes']=budget[0]
 if control.get('inconclusive'):return fallback('global-node-cap')
 proof=certificate(cells,army,lost,remaining,state,move,budget,first)
 report['net_certificate']=proof;report['enemy_nodes']=budget[0]
 if proof.get('inconclusive'):return fallback('global-node-cap')
 def bound(p):return(float('inf')if p.get('terminal_win')else p['minimum_net_material'])if p['certified']else 0
 baseline=bound(control);value=bound(proof)
 report['native_bound']=None if baseline==float('inf')else baseline
 report['selected_bound']=None if value==float('inf')else value
 if value<=baseline:return fallback('no-higher-certificate')
 report['overridden']=True;report['reason']='higher-certified-net-material-bound'
 report['witness_plan']={r['public_key']:tuple(r['response'])for r in proof.get('responses',[])}
 return move,report
