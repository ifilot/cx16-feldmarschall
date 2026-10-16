"""Public template capture expectations and opt-in quiet contact adjustments."""
import math
from campaign_belief_values import gain,worths
from feldmarschall import battle

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
