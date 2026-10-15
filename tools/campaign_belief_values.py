"""Bridge honest setup beliefs to immediate root capture gains.

The existing teacher subtracts sampled immediate material from its correction.
This isolated adjustment replaces the native count-based hidden-capture gain
component with a count-conditioned or analytic joint-setup expectation. It does
not recompute native goals, danger, mission/student terms, or the conditional
near-Flag bonus, and is therefore not a complete native-score replacement.

Analytic marginals integrate the frozen setup-style/Flag/Bomb posterior exactly.
Remaining mobile ranks are exchangeable. Behavioral encounter factors used by
the world sampler are deliberately omitted here, identically in both controls.
Only own ranks, public events/counts and frozen model parameters are accepted.
"""
import math

from calibrated_beliefs import unknowns
from campaign_joint_beliefs import neighbors,subset_sum
from feldmarschall import COUNTS,battle,setup_squares

VALUES=(400,200,100,75,45,30,15,25,10,100,20,1000)


def worths(lost):
    if len(lost)!=12 or any(type(n) is not int or not 0<=n<=count for n,count in zip(lost,COUNTS)):
        raise ValueError('valid public captured inventory required')
    result=list(VALUES)
    if lost[10]<COUNTS[10]:result[7]=40
    if lost[0]==COUNTS[0]:result[9]=15
    return result


def gain(attacker,defender,worth):
    if not 0<=attacker<10 or not 0<=defender<12:raise ValueError('valid Classic capture ranks required')
    if defender==11:return 2000
    outcome=battle(attacker,defender)
    return worth[defender] if outcome=='attacker' else -worth[attacker] if outcome=='defender' else worth[defender]-worth[attacker]


def native_expected(attacker,moved,remaining,worth):
    ranks=range(10 if moved else 12)
    total=sum(remaining[rank] for rank in ranks)
    numerator=sum(remaining[rank]*gain(attacker,rank,worth) for rank in ranks)
    # C integer division truncates toward zero, including negative expectations.
    return (numerator//total if numerator>=0 else -((-numerator)//total)) if total else 0


def immobile_marginals(model,flag_sites,bomb_sites,fixed_bombs):
    """Exact original-square Flag/Bomb marginals under the frozen joint prior."""
    items,weights=model.conditional(flag_sites,bomb_sites,fixed_bombs)
    mass=sum(weights)
    result={site:[0.,0.] for site in set(flag_sites)|set(bomb_sites)}
    count=6-len(fixed_bombs)
    for (style,flag),weight in zip(items,weights):
        probability=weight/mass
        result[flag][0]+=probability
        available=set(bomb_sites)-{flag};adjacent=neighbors(flag)&available
        theta=model.theta[style]
        normalizer=subset_sum(len(adjacent),len(available),count,theta)
        if count:
            for site in available:
                is_adjacent=int(site in adjacent)
                inclusion=(math.exp(theta*is_adjacent)*
                    subset_sum(len(adjacent)-is_adjacent,len(available)-1,count-1,theta)/normalizer)
                result[site][1]+=probability*inclusion
    return result


def root_marginals(cells,army,lost,histories,model=None,mode='joint'):
    if mode not in ('counts','joint'):raise ValueError('unknown root capture belief mode')
    if army not in (0,1) or len(cells)!=100:raise ValueError('public Classic root required')
    worths(lost)
    slots,remaining=unknowns(cells,lost,histories,army)
    if any(histories[square][-1] not in (1023,4095) for square in slots):
        raise ValueError('root capture marginals require mobile/unmoved public masks')
    mobile=sum(remaining[:10]);unmoved=[sq for sq in slots if histories[sq][-1]==4095]
    immobiles={}
    if mode=='counts':
        if remaining[10]+remaining[11]>len(unmoved):raise ValueError('immobiles exceed unmoved public slots')
        for square in slots:
            immobiles[square]=([remaining[11]/len(unmoved),remaining[10]/len(unmoved)]
                               if square in unmoved else [0.,0.])
    else:
        if model is None or model.army!=army or model.lost!=lost:
            raise ValueError('joint model must match public side and lost inventory')
        origins={};flag_sites=set();bomb_sites=set();known_flag=None
        for square,cell in enumerate(cells):
            token=model.tokens.get(square)
            if cell>=254:
                if token is not None:raise ValueError('public occupancy differs from joint history')
                continue
            if token is None or token[0]!=int(bool(cell&16)):raise ValueError('public owner differs from joint history')
            if token[0]==army:continue
            known=model.known.get(token)
            if cell&32:
                if known!=cell&15:raise ValueError('public disclosure differs from joint history')
                if known==11:known_flag=token[1]
            else:
                if known is not None:raise ValueError('publicly disclosed enemy incorrectly concealed')
                history=histories[square]
                if setup_squares(1-army)[token[1]]!=history[2]:raise ValueError('public origin differs from joint history')
                origins[token[1]]=square
                if history[-1]&(1<<11):flag_sites.add(token[1])
                if history[-1]&(1<<10):bomb_sites.add(token[1])
        if known_flag is not None:flag_sites={known_flag}
        fixed_bombs={origin for (owner,origin),rank in model.known.items() if owner!=army and rank==10}
        marginals=immobile_marginals(model,flag_sites,bomb_sites,fixed_bombs)
        immobiles={square:marginals.get(origin,[0.,0.]) for origin,square in origins.items()}
    result={}
    for square in slots:
        flag,bomb=immobiles[square]
        p_mobile=1-flag-bomb
        if p_mobile < -1e-8 or (not mobile and p_mobile>1e-8):raise ValueError('invalid mobile posterior mass')
        p_mobile=max(0.,p_mobile)
        row=[p_mobile*count/mobile if mobile else 0. for count in remaining[:10]]+[bomb,flag]
        if abs(sum(row)-1)>1e-8:raise ValueError('rank posterior is not normalized')
        result[square]=row
    for rank in range(12):
        if abs(sum(row[rank] for row in result.values())-remaining[rank])>1e-7:
            raise ValueError('rank marginals violate public remaining inventory')
    return result,remaining


def adjustments(cells,army,lost,histories,scores,model=None,mode='joint'):
    marginals,remaining=root_marginals(cells,army,lost,histories,model,mode)
    worth=worths(lost);result={};details=[]
    for move,native_score in scores.items():
        src,dst=move;actor,target=cells[src],cells[dst]
        if target>=254 or bool(target&16)==bool(army) or target&32 or native_score>=30000:
            continue
        if actor>=254 or bool(actor&16)!=bool(army) or (actor&15)>=10:
            raise ValueError('capture actor must be our public mobile rank')
        expected=sum(p*gain(actor&15,rank,worth) for rank,p in enumerate(marginals[dst]))
        # Match native quantization, guarding floating noise at exact integers.
        nearest=round(expected)
        posterior=math.trunc(nearest if abs(expected-nearest)<1e-9 else expected)
        original=native_expected(actor&15,bool(target&64),remaining,worth)
        result[move]=posterior-original
        details.append(dict(move=move,native_expected=original,posterior_expected=posterior,
                            posterior_unrounded=expected,adjustment=result[move],
                            flag_probability=marginals[dst][11],bomb_probability=marginals[dst][10]))
    return result,dict(mode=mode,behavioral_reweighting=False,changed_captures=sum(bool(v) for v in result.values()),
                       hidden_capture_actions=len(details),values=details)
