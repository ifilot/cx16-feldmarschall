"""Bounded public-material fork certificate; research only, no live policy."""
from feldmarschall import Position,LAKES,TWO_SQUARES,battle
from campaign_belief_values import worths

class Limit(Exception):pass

def own_moves(cells,army,shuttle):
 p=Position();p.shuttle=shuttle.copy()
 p.cells=[None if c>=254 else[int(bool(c&16)),c&15,bool(c&64),bool(c&32)]for c in cells]
 return p.moves(army)
def record(shuttle,army,source,target):
 result=shuttle.copy();a,b,n=result[army]
 result[army]=(source,target,n+1 if n and source==b and target==a else 1)
 return result

def feasible(cells,enemy,remaining):
 unknown=[c for c in cells if c<254 and bool(c&16)==bool(enemy)and not c&32]
 return(sum(remaining)==len(unknown)and min(remaining)>=0 and
        sum(not c&64 for c in unknown)>=sum(remaining[10:])and
        sum(bool(c&64)for c in unknown)<=sum(remaining[:10]))
def support(cells,enemy,remaining,source):
 cell=cells[source]
 if cell&32:return[cell&15]if cell&15<10 else[]
 ranks=[]
 for rank in range(10):
  if not remaining[rank]:continue
  rest=remaining[:];rest[rank]-=1;test=cells[:];test[source]=(cell&240)|32|rank
  if feasible(test,enemy,rest):ranks.append(rank)
 return ranks

def successors(cells,army,remaining,shuttle,worth,budget):
 """Enemy public observation successors; quiet hidden ranks stay grouped."""
 enemy=1-army;a,b,count=shuttle[enemy]
 for source,cell in enumerate(cells):
  if cell>=254 or bool(cell&16)!=bool(enemy):continue
  ranks=support(cells,enemy,remaining,source)
  if not ranks:continue
  row,col=divmod(source,10)
  for dr,dc in((-1,0),(0,1),(1,0),(0,-1)):
   r,c=row,col;distance=0
   while True:
    r+=dr;c+=dc;distance+=1
    if not(0<=r<10 and 0<=c<10):break
    target=10*r+c;victim=cells[target]
    if victim==254 or(victim<254 and bool(victim&16)==bool(enemy)):break
    choices=ranks if distance==1 else([8]if 8 in ranks else[])
    banned=count>=TWO_SQUARES and source==b and target==a
    if choices and not banned:
     quiet=victim==255
     branches=[None]if quiet and distance==1 else choices
     for rank in branches:
      after=cells[:];rest=remaining[:];moving=cell|64;balance=0;flag_loss=False
      if rank is not None:
       if not cell&32:rest[rank]-=1
       moving=(moving&240)|32|rank
      after[source]=255
      if quiet:after[target]=moving
      else:
       outcome=battle(rank,victim&15)
       if outcome in('attacker','both'):balance-=worth[victim&15];flag_loss=victim&15==11
       if outcome in('defender','both'):balance+=worth[rank]
       after[target]=moving if outcome=='attacker'else((victim|32|64)if outcome=='defender'else 255)
      if feasible(after,enemy,rest):
       budget[0]+=1
       if budget[0]>budget[1]:raise Limit()
       yield dict(cells=after,remaining=rest,shuttle=record(shuttle,enemy,source,target),balance=balance,
                  flag_loss=flag_loss,observation=dict(move=[source,target],rank=rank,quiet=quiet))
    if victim!=255 or 8 not in ranks:break

def certify(cells,army,lost,remaining,shuttle,move,victims,nodecap=20000):
 """AND enemy public replies, OR one public capture, AND next replies."""
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
   if board[target]<254 and bool(board[target]&16)==bool(army):
    for victim in victims:
     capture=(target,victim)
     if capture not in legal:continue
     enemycell=board[victim]
     if enemycell>=254 or bool(enemycell&16)==bool(army)or not enemycell&32 or battle(rank,enemycell&15)!='attacker':continue
     outcome=board[:];outcome[target]=255;outcome[victim]=board[target]|32|64
     updated=record(reply['shuttle'],army,target,victim)
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
