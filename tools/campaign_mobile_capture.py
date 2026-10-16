"""Replace only exchangeable mobile capture gain by public template marginals."""
import math
from campaign_belief_values import gain,worths

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
