"""Research-only common response control; original certificate remains unchanged."""
from certificate import *
def certify_common(cells,army,lost,remaining,shuttle,move,nodecap=20000):
 """Same enemy ANDs; OR every own disclosed surviving capture."""
 budget=[0,nodecap];worth=worths(lost);source,target=move
 if move not in own_moves(cells,army,shuttle)or cells[target]!=255:raise ValueError('legal quiet root required')
 after=cells[:];after[target]=after[source]|64;after[source]=255
 after_shuttle=record(shuttle,army,source,target);rank=after[target]&15
 worst=float('inf');branches=0;responses=[]
 try:
  first=list(successors(after,army,remaining,after_shuttle,worth,budget))
  if not first:
   win=bool(own_moves(after,army,after_shuttle))
   return dict(certified=win,terminal_win=win,reason='enemy-no-moves' if win else 'neither-can-move',enemy_nodes=budget[0],first_public_outcomes=0)
  for reply in first:
   branches+=1;board=reply['cells'];legal=own_moves(board,army,reply['shuttle'])
   if reply['flag_loss']or not legal:
    return dict(certified=False,reason='first-enemy-terminal-counterwin-or-own-immobility',counterexample=reply['observation'],enemy_nodes=budget[0],first_public_outcomes=len(first))
   # A disclosed Flag capture ends the game before another enemy reply.
   immediate=[m for m in legal if board[m[1]]<254 and board[m[1]]&32 and board[m[1]]&15==11]
   if immediate:
    responses.append(dict(enemy=reply['observation'],response=list(immediate[0]),terminal_win=True));continue
   best=-float('inf');best_response=None;failures=[]
   for capture in legal:
    capture_source,victim=capture
    enemycell=board[victim];rank=board[capture_source]&15
    if enemycell>=254 or bool(enemycell&16)==bool(army)or not enemycell&32 or battle(rank,enemycell&15)!='attacker':continue
    outcome=board[:];outcome[capture_source]=255;outcome[victim]=board[capture_source]|32|64
    updated=record(reply['shuttle'],army,capture_source,victim)
    balance=reply['balance']+worth[enemycell&15]
    second=list(successors(outcome,army,reply['remaining'],updated,worth,budget))
    if not second:
     value=float('inf')if own_moves(outcome,army,updated)else-float('inf');failure=None
    else:
     value=float('inf');failure=None
     for response in second:
      val=balance+response['balance']
      if response['flag_loss']or not own_moves(response['cells'],army,response['shuttle']):val=-float('inf')
      if val<value:value=val;failure=response['observation']
    failures.append(dict(response=list(capture),minimum_net_material=None if abs(value)==float('inf')else value,terminal_refutation=value==-float('inf'),enemy_response=failure))
    if value>best:best=value;best_response=list(capture)
   if best<=0:
    return dict(certified=False,reason='no-positive-bounded-conversion',counterexample=reply['observation'],responses=failures,enemy_nodes=budget[0],first_public_outcomes=len(first))
   responses.append(dict(enemy=reply['observation'],response=best_response,minimum_net_material=None if best==float('inf')else best,terminal_win=best==float('inf')))
   worst=min(worst,best)
  return dict(certified=True,minimum_net_material=None if worst==float('inf')else worst,terminal_win=worst==float('inf'),first_public_outcomes=len(first),enemy_nodes=budget[0],responses=responses)
 except Limit:
  return dict(certified=False,inconclusive=True,reason='prespecified-node-cap',enemy_nodes=budget[0],processed_first_outcomes=branches)
