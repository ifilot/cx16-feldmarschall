"""Public template capture expectations and opt-in quiet contact adjustments."""
import math
import json
from campaign_belief_values import gain,worths
from feldmarschall import battle,Position,LAKES,TWO_SQUARES,COUNTS

ONE=4096
VERSION='template-mobile-capture-v1'

def cdiv(numerator,denominator):
    if denominator<=0:raise ValueError('positive denominator required')
    return numerator//denominator if numerator>=0 else -((-numerator)//denominator)

def stable_trunc(value):
    nearest=round(value)
    return nearest if abs(value-nearest)<1e-9 else math.trunc(value)

def adjustments(cells,army,lost,remaining,marginals,flag,bomb,scores,credit):
    """Keep quantized immobile masses, native danger and all noncapture terms."""
    if len(cells)!=100 or army not in (0,1):raise ValueError('public Classic board required')
    worth=worths(lost);hidden_mobile=sum(remaining[:10])
    own_flags=[sq for sq,c in enumerate(cells) if c<254 and bool(c&16)==bool(army) and c&15==11]
    own_flag=own_flags[0] if len(own_flags)==1 else None
    delta=dict.fromkeys(scores,0);rows=[]
    for move,score in scores.items():
        source,target=move;actor=cells[source];cell=cells[target]
        if cell>=254 or bool(cell&16)==bool(army) or cell&32 or score>=30000:continue
        if actor>=254 or bool(actor&16)!=bool(army) or actor&15>=10:raise ValueError('own mobile capture actor required')
        if move not in credit:raise ValueError('native capture danger credit required')
        if not hidden_mobile:continue
        rank=actor&15;gains=[gain(rank,r,worth) for r in range(10)]
        mobile_sum=sum(count*g for count,g in zip(remaining[:10],gains))
        pf,pb=(0,0) if cell&64 else (flag[target],bomb[target]);pm=ONE-pf-pb
        immobile=pf*2000+pb*gain(rank,10,worth)
        original=cdiv(immobile*hidden_mobile+pm*mobile_sum,ONE*hidden_mobile)
        row=marginals[target];mass=sum(row[:10])
        conditional=sum(p*g for p,g in zip(row[:10],gains))/mass if mass>0 else mobile_sum/hidden_mobile
        replacement=(original if abs(conditional-mobile_sum/hidden_mobile)<1e-9 else
                     stable_trunc((immobile+pm*conditional)/ONE))
        bonus_before=bonus_after=0
        if own_flag is not None and abs(target//10-own_flag//10)+abs(target%10-own_flag%10)<=2:
            probe=10 if rank>=6 else 0
            bonus_before=40 if original-credit[move]+probe>=0 else 0
            bonus_after=40 if replacement-credit[move]+probe>=0 else 0
        delta[move]=replacement-original+bonus_after-bonus_before
        rows.append(dict(move=move,original_capture_gain=original,replacement_capture_gain=replacement,
                         danger_credit=credit[move],bonus_before=bonus_before,bonus_after=bonus_after,
                         mobile_mass=mass,adjustment=delta[move]))
    return delta,dict(version=VERSION,changed_captures=sum(bool(v) for v in delta.values()),captures=rows,
                      scope='Only conditional mobile capture expectation and its existing near-own-Flag threshold; native danger, routes, quiet scores and Q12 immobile masses retained.')


# Quiet scopes retain the legacy MAX aggregation, disclosed behavior and rays.
# The three modes differ only in adjacent concealed-piece contact losses.
def integer_floor(value):
    nearest=round(value)
    return nearest if abs(value-nearest)<1e-9 else math.floor(value)


def quiet_threat(cells,army,lost,remaining,rank,square,mode='native',marginals=None,flag=None,bomb=None):
    if mode not in ('native','occupancy','mobile'):raise ValueError(mode)
    worth=worths(lost);W=worth[rank];H=sum(remaining[:10])
    D=sum(n for r,n in enumerate(remaining[:10])if battle(r,rank)!='defender')
    conditional=W*D//H if H else 0
    worst=0;row,column=divmod(square,10)
    for dr,dc in((-1,0),(0,1),(1,0),(0,-1)):
        r,c=row,column;distance=0
        while True:
            r+=dr;c+=dc;distance+=1
            if not(0<=r<10 and 0<=c<10):break
            target=10*r+c;cell=cells[target]
            if cell==254:break
            if cell==255:continue
            if bool(cell&16)==bool(army):break
            loss=0
            if cell&32:
                enemy_rank=cell&15
                if enemy_rank<10 and(distance==1 or enemy_rank==8):
                    outcome=battle(enemy_rank,rank)
                    if outcome=='attacker':loss=W
                    elif outcome=='both':loss=W-worth[enemy_rank]
            elif distance==1:
                if mode=='native':loss=conditional if cell&64 else conditional//2
                else:
                    mobile=ONE-flag[target]-bomb[target]
                    risk=conditional
                    if mode=='mobile':
                        probs=marginals[target];mass=sum(probs[:10])
                        capability=sum(p for r,p in enumerate(probs[:10])if battle(r,rank)!='defender')/mass if mass else(D/H if H else 0)
                        if H and abs(capability-D/H)>=1e-9:risk=integer_floor(W*capability)
                    loss=risk*mobile//ONE
            worst=max(worst,loss)
            break
    return worst



def quiet_adjustments(cells,army,lost,remaining,marginals,flag,bomb,scores,scope):
    """Replace only quiet old-minus-new danger; preserve every capture score."""
    if scope not in ('quiet-occupancy','quiet-mobile'):raise ValueError('quiet scope required')
    if len(cells)!=100 or army not in (0,1):raise ValueError('public Classic board required')
    mode='occupancy' if scope=='quiet-occupancy' else 'mobile'
    delta=dict.fromkeys(scores,0);rows=[];old={}
    for move,score in scores.items():
        source,target=move
        if cells[target]!=255 or score>=30000:continue
        actor=cells[source];rank=actor&15
        if actor>=254 or bool(actor&16)!=bool(army) or rank>=10:raise ValueError('own mobile quiet actor required')
        if source not in old:
            old[source]={kind:quiet_threat(cells,army,lost,remaining,rank,source,kind,marginals,flag,bomb)
                         for kind in ('native',mode)}
        after=list(cells);after[source]=255;after[target]=actor|64
        new={kind:quiet_threat(after,army,lost,remaining,rank,target,kind,marginals,flag,bomb)
             for kind in ('native',mode)}
        delta[move]=(old[source][mode]-new[mode])-(old[source]['native']-new['native'])
        rows.append(dict(move=move,old=old[source],new=new,adjustment=delta[move]))
    return delta,dict(version='template-quiet-contact-v1',scope=scope,
                      changed_quiet_moves=sum(bool(v) for v in delta.values()),quiet=rows,
                      limitation='Legacy MAX contact loss with source-template marginals; not exact expected worst loss or a safety guarantee. Captures, goals, probes, tactical terms and RNG unchanged.')


# Bounded public fork conversion. These functions are isolated from all older
# capture/quiet scopes; existing policy IDs retain their frozen archives.
class _ForkLimit(Exception):pass

def _fork_own_moves(cells,army,shuttle):
 p=Position();p.shuttle=shuttle.copy()
 p.cells=[None if c>=254 else[int(bool(c&16)),c&15,bool(c&64),bool(c&32)]for c in cells]
 return p.moves(army)
def _fork_record(shuttle,army,source,target):
 result=shuttle.copy();a,b,n=result[army]
 result[army]=(source,target,n+1 if n and source==b and target==a else 1)
 return result

def _fork_feasible(cells,enemy,remaining):
 unknown=[c for c in cells if c<254 and bool(c&16)==bool(enemy)and not c&32]
 return(sum(remaining)==len(unknown)and min(remaining)>=0 and
        sum(not c&64 for c in unknown)>=sum(remaining[10:])and
        sum(bool(c&64)for c in unknown)<=sum(remaining[:10]))
def _fork_support(cells,enemy,remaining,source):
 """Exact rank support under only counts and moved/unmoved masks.

 Removing one hidden mobile from a moved slot preserves M<=H. Removing it
 from an unmoved slot is feasible exactly when U>I; all mobile ranks share
 that same slot constraint. This is the original per-rank feasibility test
 factored once per source, without changing any successor or node count.
 """
 cell=cells[source]
 if cell&32:return[cell&15]if cell&15<10 else[]
 if not _fork_feasible(cells,enemy,remaining):return[]
 if not cell&64:
  unmoved=sum(c<254 and bool(c&16)==bool(enemy)and not c&(32|64)for c in cells)
  if unmoved<=sum(remaining[10:]):return[]
 return [rank for rank in range(10)if remaining[rank]]


def _fork_successors(cells,army,remaining,shuttle,worth,budget):
 """Enemy public observation _fork_successors; quiet hidden ranks stay grouped."""
 enemy=1-army;a,b,count=shuttle[enemy]
 for source,cell in enumerate(cells):
  if cell>=254 or bool(cell&16)!=bool(enemy):continue
  ranks=_fork_support(cells,enemy,remaining,source)
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
      if quiet:
       if abs(source//10-target//10)+abs(source%10-target%10)>1:moving|=32
       after[target]=moving
      else:
       outcome=battle(rank,victim&15)
       if outcome in('attacker','both'):balance-=worth[victim&15];flag_loss=victim&15==11
       if outcome in('defender','both'):balance+=worth[rank]
       after[target]=moving if outcome=='attacker'else((victim|32)if outcome=='defender'else 255)
      if _fork_feasible(after,enemy,rest):
       budget[0]+=1
       if budget[0]>budget[1]:raise _ForkLimit()
       yield dict(cells=after,remaining=rest,shuttle=_fork_record(shuttle,enemy,source,target),balance=balance,
                  flag_loss=flag_loss,observation=dict(move=[source,target],rank=rank,quiet=quiet))
    if victim!=255 or 8 not in ranks:break

def _fork_certificate(cells,army,lost,remaining,shuttle,move,budget,victims=None):
 """Same enemy ANDs; OR every own disclosed surviving capture."""
 started_nodes=budget[0];worth=worths(lost);source,target=move
 if move not in _fork_own_moves(cells,army,shuttle)or cells[target]!=255:raise ValueError('legal quiet root required')
 after=cells[:];moving=after[source]|64
 if abs(source//10-target//10)+abs(source%10-target%10)>1:moving|=32
 after[target]=moving;after[source]=255
 after_shuttle=_fork_record(shuttle,army,source,target);rank=after[target]&15
 worst=float('inf');branches=0;responses=[]
 try:
  first=list(_fork_successors(after,army,remaining,after_shuttle,worth,budget))
  if not first:
   win=bool(_fork_own_moves(after,army,after_shuttle))
   return dict(certified=win,terminal_win=win,reason='enemy-no-moves' if win else 'neither-can-move',enemy_nodes=budget[0]-started_nodes,first_public_outcomes=0)
  for reply in first:
   branches+=1;board=reply['cells'];legal=_fork_own_moves(board,army,reply['shuttle'])
   if reply['flag_loss']or not legal:
    return dict(certified=False,reason='first-enemy-terminal-counterwin-or-own-immobility',counterexample=reply['observation'],enemy_nodes=budget[0]-started_nodes,first_public_outcomes=len(first))
   # A disclosed Flag capture ends the game before another enemy reply.
   immediate=[m for m in legal if board[m[1]]<254 and board[m[1]]&32 and board[m[1]]&15==11]
   if immediate:
    entry=dict(enemy=reply['observation'],response=list(immediate[0]),terminal_win=True)
    if victims is not None:entry['public_key']=_fork_public_key(board,army,_fork_enemy_lost(board,army,reply['remaining']),reply['remaining'],reply['shuttle'])
    responses.append(entry);continue
   best=-float('inf');best_response=None;failures=[]
   response_moves=legal if victims is None else [(target,victim)for victim in victims if(target,victim)in legal]
   for capture in response_moves:
    capture_source,victim=capture
    enemycell=board[victim];rank=board[capture_source]&15
    if enemycell>=254 or bool(enemycell&16)==bool(army)or not enemycell&32 or battle(rank,enemycell&15)!='attacker':continue
    outcome=board[:];outcome[capture_source]=255;outcome[victim]=board[capture_source]|32|64
    updated=_fork_record(reply['shuttle'],army,capture_source,victim)
    balance=reply['balance']+worth[enemycell&15]
    second=list(_fork_successors(outcome,army,reply['remaining'],updated,worth,budget))
    if not second:
     value=float('inf')if _fork_own_moves(outcome,army,updated)else-float('inf');failure=None
    else:
     value=float('inf');failure=None
     for response in second:
      val=balance+response['balance']
      if response['flag_loss']or not _fork_own_moves(response['cells'],army,response['shuttle']):val=-float('inf')
      if val<value:value=val;failure=response['observation']
    failures.append(dict(response=list(capture),minimum_net_material=None if abs(value)==float('inf')else value,terminal_refutation=value==-float('inf'),enemy_response=failure))
    if value>best:best=value;best_response=list(capture)
   if best<=0:
    return dict(certified=False,reason='no-positive-bounded-conversion',counterexample=reply['observation'],responses=failures,enemy_nodes=budget[0]-started_nodes,first_public_outcomes=len(first))
   entry=dict(enemy=reply['observation'],response=best_response,minimum_net_material=None if best==float('inf')else best,terminal_win=best==float('inf'))
   if victims is not None:entry['public_key']=_fork_public_key(board,army,_fork_enemy_lost(board,army,reply['remaining']),reply['remaining'],reply['shuttle'])
   responses.append(entry)
   worst=min(worst,best)
  return dict(certified=True,minimum_net_material=None if worst==float('inf')else worst,terminal_win=worst==float('inf'),first_public_outcomes=len(first),enemy_nodes=budget[0]-started_nodes,responses=responses)
 except _ForkLimit:
  return dict(certified=False,inconclusive=True,reason='prespecified-node-cap',enemy_nodes=budget[0]-started_nodes,processed_first_outcomes=branches)



def _fork_enemy_lost(cells,army,remaining):
    seen=[0]*12
    for cell in cells:
        if cell<254 and bool(cell&16)!=bool(army)and cell&32:seen[cell&15]+=1
    lost=[count-hidden-known for count,hidden,known in zip(COUNTS,remaining,seen)]
    if any(not 0<=n<=count for n,count in zip(lost,COUNTS)):raise ValueError('inconsistent public successor inventory')
    return lost


def _fork_public_key(cells,army,lost,remaining,shuttle):
    """Complete public successor; no concealed-rank or seed dependence."""
    masked=[(c&240)|12 if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in cells]
    state=_fork_shuttle(shuttle)
    return json.dumps([army,masked,list(lost),list(remaining),list(state[0]),list(state[1])],separators=(',',':'))


def _fork_adjacent(square):
    row,col=divmod(square,10)
    return [10*r+c for r,c in ((row-1,col),(row,col-1),(row+1,col),(row,col+1))
            if 0<=r<10 and 0<=c<10 and 10*r+c not in LAKES]


def _fork_danger(cells,army,remaining,square,rank,shuttle,flag_filter=False):
    """Legal first-contact removal, with exact hidden support for Flag filter."""
    last_src,last_dst,count=shuttle;row,col=divmod(square,10)
    for dr,dc in ((-1,0),(0,1),(1,0),(0,-1)):
        r,c=row,col;distance=0
        while True:
            r+=dr;c+=dc;distance+=1
            if not(0<=r<10 and 0<=c<10):break
            source=10*r+c;cell=cells[source]
            if cell==255:continue
            if cell==254 or bool(cell&16)==bool(army):break
            if count>=TWO_SQUARES and source==last_dst and square==last_src:break
            ranks=([cell&15] if cell&32 else
                   _fork_support(cells,1-army,remaining,source) if flag_filter else
                   [r for r,n in enumerate(remaining[:10])if n])
            if any(enemy_rank<10 and(distance==1 or enemy_rank==8)and
                   battle(enemy_rank,rank)!='defender'for enemy_rank in ranks):return True
            break
    return False


def _fork_shuttle(value):
    """Decode native public last-from,last-to,count arrays (six bytes)."""
    if isinstance(value,dict):
        return {army:tuple(value[army])for army in (0,1)}
    data=bytes.fromhex(value) if isinstance(value,str)else bytes(value)
    if len(data)!=6:raise ValueError('public six-byte shuttle required')
    return {army:(None if data[army]==255 else data[army],
                  None if data[army+2]==255 else data[army+2],data[army+4])for army in (0,1)}


def fork_selection(cells,army,lost,remaining,scores,parent,shuttle):
    """Select a bounded quiet fork by proof bound, without changing scores."""
    if len(cells)!=100 or army not in (0,1):raise ValueError('public Classic board required')
    report=dict(version='public-quiet-fork-v1',overridden=False,enemy_nodes=0,
                scope='Bounded material conversion with one-turn public witness followup; not game value or a global safety guarantee.')
    def fallback(reason):
        report['reason']=reason
        return parent,report
    if parent is None:return fallback('no-native-move')
    if parent not in scores:raise ValueError('native move missing from legal candidates')
    if cells[parent[1]]!=255 or scores[parent]>=30000:return fallback('preserve-native-capture-or-terminal')
    if any(score>=30000 for score in scores.values()):return fallback('preserve-terminal-win')
    state=_fork_shuttle(shuttle);candidates=[]
    for source,target in sorted(scores):
        if cells[target]!=255:continue
        rank=cells[source]&15
        victims=[sq for sq in _fork_adjacent(target)if cells[sq]<254 and
                 bool(cells[sq]&16)!=bool(army)and cells[sq]&32 and cells[sq]&15<10 and
                 battle(rank,cells[sq]&15)=='attacker']
        if len(victims)<2:continue
        after=list(cells);after[target]=after[source]|64;after[source]=255
        if not _fork_danger(after,army,remaining,target,rank,state[1-army]):
            candidates.append(dict(move=(source,target),victims=victims))
    report['eligible_forks']=len(candidates)
    if not candidates:return fallback('no-public-fork')
    flags=[sq for sq,c in enumerate(cells)if c<254 and bool(c&16)==bool(army)and c&15==11]
    if len(flags)!=1:return fallback('missing-own-flag')
    if _fork_danger(cells,army,remaining,flags[0],11,state[1-army],True):
        return fallback('current-count-possible-flag-attack')
    budget=[0,20000]
    native=_fork_certificate(cells,army,lost,remaining,state,parent,budget)
    report['native_certificate']=native;report['enemy_nodes']=budget[0]
    if native.get('inconclusive'):return fallback('global-node-cap')
    def bound(proof):
        if not proof['certified']:return 0
        return float('inf')if proof.get('terminal_win')else proof['minimum_net_material']
    native_bound=bound(native);report['native_bound']=None if native_bound==float('inf')else native_bound
    if native_bound==float('inf'):return fallback('native-terminal-certificate')
    best=parent;best_bound=native_bound;best_proof=None;proofs=[]
    for candidate in candidates:
        move=candidate['move']
        proof=_fork_certificate(cells,army,lost,remaining,state,move,budget,candidate['victims'])
        proofs.append(dict(move=move,proof=proof));report['enemy_nodes']=budget[0]
        if proof.get('inconclusive'):
            report['fork_certificates']=proofs
            return fallback('global-node-cap')
        value=bound(proof)
        if value>native_bound and(value>best_bound or
           (value==best_bound and (scores[move],move==parent)>(scores[best],best==parent))):
            best=move;best_bound=value;best_proof=proof
    report['fork_certificates']=proofs;report['selected_bound']=None if best_bound==float('inf')else best_bound
    report['overridden']=best!=parent
    if best_proof is not None:
        report['witness_plan']={entry['public_key']:tuple(entry['response'])for entry in best_proof.get('responses',[])}
    report['reason']='higher-certified-material-bound' if best!=parent else 'no-higher-certificate'
    return best,report
