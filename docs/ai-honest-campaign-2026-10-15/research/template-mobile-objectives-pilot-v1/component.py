"""Public goal-expectation and exact native route component oracles."""
import sys
from pathlib import Path
from collections import deque
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_belief_values import gain,worths,native_expected
from campaign_mobile_capture import cdiv,stable_trunc
from feldmarschall import LAKES

def route(cells,army,goal,source):
 distance=[255]*100
 if goal==255:return distance
 distance[goal]=0;queue=deque([goal])
 def enemy(c):return c<254 and bool(c&16)!=bool(army)
 while queue:
  square=queue.popleft()
  if square!=goal and enemy(cells[square]):continue
  row,col=divmod(square,10)
  for dr,dc in((-1,0),(0,1),(1,0),(0,-1)):
   r,c=row+dr,col+dc
   if not(0<=r<10 and 0<=c<10):continue
   nb=10*r+c
   if nb in LAKES or distance[nb]!=255:continue
   if cells[nb]!=255 and not enemy(cells[nb])and nb!=source:continue
   distance[nb]=distance[square]+1;queue.append(nb)
 return distance

def expected(actor,square,cells,remaining,worth,marginals,flag,bomb,full=False):
 cell=cells[square]
 if cell&32:return gain(actor,cell&15,worth)
 h=sum(remaining[:10]);f=flag[square];b=bomb[square];m=4096-f-b
 mobile_sum=sum(n*gain(actor,r,worth)for r,n in enumerate(remaining[:10]))
 if full and h:
  probabilities=marginals[square][:10];mass=sum(probabilities)
  if mass:return stable_trunc((f*2000+b*gain(actor,10,worth)+m*sum(p*gain(actor,r,worth)for r,p in enumerate(probabilities))/mass)/4096)
 if cell&64:return native_expected(actor,True,remaining,worth)
 immobile=f*2000+b*gain(actor,10,worth)
 if not h:return cdiv(immobile,4096)if not m else native_expected(actor,False,remaining,worth)
 return cdiv(immobile*h+m*mobile_sum,4096*h)

def analyze(cells,army,lost,remaining,marginals,flag,bomb,goalrows,plans,scores,selected):
 worth=worths(lost);byactor={};diagnostics=[];opportunities=[]
 ownflag=next((s for s,c in enumerate(cells)if c<254 and bool(c&16)==bool(army)and c&15==11),255)
 for row in goalrows:
  source,target,g,steps,previous,utility,accepted=row;rank=cells[source]&15
  assert expected(rank,target,cells,remaining,worth,marginals,flag,bomb)==g,('gain',source,target,g)
  distance=route(cells,army,source,source);assert distance[target]==steps
  base=24+cdiv(g,4)+(12 if not cells[target]&32 and rank>=6 else 0)
  if ownflag!=255 and abs(target//10-ownflag//10)+abs(target%10-ownflag%10)<=2 and(not cells[target]&32 or cells[target]&15<10):base+=40
  base-=3*steps;base+=8 if target==previous else 0
  assert utility==base and bool(accepted)==(g>=-cdiv(worth[rank],2)),('utility',row,base)
  newg=expected(rank,target,cells,remaining,worth,marginals,flag,bomb,True)
  item=dict(target=target,g=g,newg=newg,steps=steps,previous=previous,oldutility=utility,newutility=utility+cdiv(newg,4)-cdiv(g,4),oldaccepted=bool(accepted),newaccepted=newg>=-cdiv(worth[rank],2))
  byactor.setdefault(source,[]).append(item)
 for source,rows in byactor.items():
  old=max((r for r in rows if r['oldaccepted']),key=lambda r:(r['oldutility'],-r['target']),default=None)
  new=max((r for r in rows if r['newaccepted']),key=lambda r:(r['newutility'],-r['target']),default=None)
  oldgoal=255 if old is None else old['target'];newgoal=255 if new is None else new['target'];trace=plans[source]
  assert trace[0]==oldgoal and trace[1]==rows[0]['previous']and trace[3]==(-32767 if old is None else old['oldutility']),('goal',source,trace,old)
  oldroute=route(cells,army,oldgoal,source);assert oldroute[source]==trace[2]
  changed=sum(r['g']!=r['newg']for r in rows);rejections=sum(r['oldaccepted']!=r['newaccepted']for r in rows)
  quiet={move:value for move,value in scores.items()if move[0]==source and cells[move[1]]==255}
  detail=dict(source=source,rank=cells[source]&15,previous=trace[1],oldgoal=oldgoal,newgoal=newgoal,changed_expectations=changed,rejection_changes=rejections,rows=rows,quiet_options=len(quiet))
  diagnostics.append(detail)
  if old is None or new is None or oldgoal==newgoal or cells[oldgoal]&32 or cells[newgoal]&32 or not quiet:continue
  oldrow=next(r for r in rows if r['target']==oldgoal);newrow=next(r for r in rows if r['target']==newgoal)
  reversal=oldrow['oldutility']>newrow['oldutility']and oldrow['newutility']<newrow['newutility'];rejected=oldrow['oldaccepted']!=oldrow['newaccepted']or newrow['oldaccepted']!=newrow['newaccepted']
  if not(reversal or rejected):continue
  newroute=route(cells,army,newgoal,source)
  assert oldroute[source]!=255 and newroute[source]!=255
  corrected={move:value+6*((newroute[source]-newroute[move[1]])if newroute[move[1]]!=255 else 0)-6*((oldroute[source]-oldroute[move[1]])if oldroute[move[1]]!=255 else 0)for move,value in quiet.items()}
  oldbest=max(quiet,key=quiet.get);newbest=max(corrected,key=corrected.get)
  strictold=sum(v==quiet[oldbest]for v in quiet.values())==1;strictnew=sum(v==corrected[newbest]for v in corrected.values())==1
  detail.update(strict_order_reversal=reversal,rejection_gate_change=rejected,oldbestquiet=list(oldbest),newbestquiet=list(newbest),strictquiet_choices=strictold and strictnew)
  if oldbest!=newbest and strictold and strictnew:opportunities.append(dict(**detail,actual_native_quiet=tuple(selected)==oldbest,quiet_scores=[dict(move=list(m),old=v,new=corrected[m])for m,v in quiet.items()]))
 return diagnostics,opportunities
