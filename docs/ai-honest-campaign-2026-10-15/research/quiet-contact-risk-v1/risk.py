"""Isolated research reconstruction of native MAX contact danger, Classic only."""
import math
from campaign_belief_values import worths
from feldmarschall import battle

ONE=4096


def integer_floor(value):
    nearest=round(value)
    return nearest if abs(value-nearest)<1e-9 else math.floor(value)


def threat(cells,army,lost,remaining,rank,square,mode='native',marginals=None,flag=None,bomb=None):
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


def quiet_corrections(cells,army,lost,remaining,marginals,flag,bomb,moves):
    """Return diagnostics for each legal quiet move; captures have delta zero."""
    rows=[];old={}
    for source,target in moves:
        if cells[target]!=255:
            rows.append(dict(move=[source,target],capture=True,occupancy_delta=0,mobile_delta=0))
            continue
        rank=cells[source]&15
        if source not in old:
            old[source]={mode:threat(cells,army,lost,remaining,rank,source,mode,marginals,flag,bomb)
                         for mode in('native','occupancy','mobile')}
        after=list(cells);after[source]=255;after[target]=cells[source]|64
        new={mode:threat(after,army,lost,remaining,rank,target,mode,marginals,flag,bomb)
             for mode in('native','occupancy','mobile')}
        pressure={mode:old[source][mode]-new[mode]for mode in old[source]}
        rows.append(dict(move=[source,target],capture=False,old=old[source],new=new,pressure=pressure,
                         occupancy_delta=pressure['occupancy']-pressure['native'],
                         mobile_delta=pressure['mobile']-pressure['native'],
                         mobile_vs_occupancy_delta=pressure['mobile']-pressure['occupancy']))
    return rows
