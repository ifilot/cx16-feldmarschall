"""Research-only analytic source-screen prior; no engine/runtime integration."""
from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from feldmarschall import COUNTS


def elementary(weights,k):
    if k<0:return 0.
    values=[1.]+[0.]*k
    for w in weights:
        for j in range(k,0,-1):values[j]+=w*values[j-1]
    return values[k]


def log_falling(n,k):
    if not 0<=k<=n:return -math.inf
    return sum(math.log(n-j)for j in range(k))


@dataclass(frozen=True)
class Geometry:
    flag:int
    bombs:frozenset
    mobiles:frozenset
    prior:float
    label:str=''


def source_geometries():
    def origin(row,col):return(4-row)*10+col-1
    result=[]
    for c in range(1,11):
        flag=origin(1,c)
        if c not in(1,10):
            result.append(Geometry(flag,frozenset(origin(r,q)for r,q in((2,c),(1,c-1),(1,c+1))),
                frozenset(origin(2,q)for q in(c-1,c+1)),.1,'interior'))
        else:
            d=1 if c==1 else-1
            result.append(Geometry(flag,frozenset(origin(r,q)for r,q in((2,c),(1,c+d))),
                frozenset(origin(r,q)for r,q in((2,c+d),(1,c+2*d))),.02,'corner-adjacent'))
            result.append(Geometry(flag,frozenset(origin(r,q)for r,q in((3,c),(2,c+d),(1,c+2*d))),
                frozenset(origin(r,q)for r,q in((2,c),(1,c+d))),.08,'corner-outer'))
    assert len(result)==12 and abs(sum(g.prior for g in result)-1)<1e-10
    return result


class StructuralModel:
    def __init__(self,counts=COUNTS,geometries=None,weights=None):
        self.counts=tuple(counts);self.size=sum(counts);self.bomb=len(counts)-2;self.flag=len(counts)-1
        self.geometries=tuple(source_geometries()if geometries is None else geometries)
        self.weights=tuple([1.]*self.size if weights is None else weights)
        assert len(self.weights)==self.size and all(w>0 and math.isfinite(w)for w in self.weights)
        total=sum(g.prior for g in self.geometries);assert total>0
        self.prepared=[]
        for g in self.geometries:
            assert 0<=g.flag<self.size and not(g.bombs&g.mobiles)and g.flag not in g.bombs|g.mobiles
            assert len(g.bombs)<=self.counts[self.bomb]
            eligible=set(range(self.size))-{g.flag}-set(g.bombs)-set(g.mobiles)
            k=self.counts[self.bomb]-len(g.bombs);z=elementary((self.weights[s]for s in eligible),k)
            assert z>0
            self.prepared.append((g,g.prior/total,eligible,k,z))

    def predict(self,known,moved,with_bombs=True):
        known={int(o):r for o,r in known.items()};moved=set(moved)
        assert all(0<=o<self.size and 0<=r<len(self.counts)for o,r in known.items())
        assert all(0<=o<self.size for o in moved)
        rankcounts=Counter(known.values())
        if any(rankcounts[r]>n for r,n in enumerate(self.counts))or any(known.get(o,-1)>=self.bomb for o in moved):
            return dict(log_evidence=-math.inf,flag=None,bomb=None)
        kmobile=sum(n for r,n in rankcounts.items()if r<self.bomb)
        logmobile=sum(log_falling(n,rankcounts[r])for r,n in enumerate(self.counts[:self.bomb]))-log_falling(sum(self.counts[:self.bomb]),kmobile)
        known_bombs={o for o,r in known.items()if r==self.bomb}
        known_flags={o for o,r in known.items()if r==self.flag}
        surviving=[]
        for g,prior,eligible,k,z in self.prepared:
            if known_flags-{g.flag}or known.get(g.flag,self.flag)!=self.flag or g.flag in moved:continue
            if any(o in moved or known.get(o,self.bomb)!=self.bomb for o in g.bombs):continue
            if any(known.get(o,-1)>=self.bomb for o in g.mobiles):continue
            required=known_bombs-set(g.bombs)
            if not required<=eligible:continue
            available=eligible-set(known)-moved
            remaining=k-len(required);e=elementary((self.weights[s]for s in available),remaining)
            if not e:continue
            probability=prior*math.prod(self.weights[s]for s in required)*e/z
            surviving.append((g,required,available,remaining,e,probability))
        evidence=sum(row[-1]for row in surviving)
        if not evidence:return dict(log_evidence=-math.inf,flag=None,bomb=None)
        flags=[0.]*self.size;bombs=[0.]*self.size
        for g,required,available,k,e,probability in surviving:
            mass=probability/evidence;flags[g.flag]+=mass
            if with_bombs:
                for s in g.bombs|required:bombs[s]+=mass
                if k:
                    for s in available:
                        bombs[s]+=mass*self.weights[s]*elementary((self.weights[q]for q in available if q!=s),k-1)/e
        assert abs(sum(flags)-self.counts[self.flag])<1e-8
        if with_bombs:assert abs(sum(bombs)-self.counts[self.bomb])<1e-8
        return dict(log_evidence=math.log(evidence)+logmobile,flag=flags,bomb=bombs if with_bombs else None)


def fit_row_odds(armies):
    """Fixed smoothed residual-Bomb odds; full truth is training-only input."""
    eligible_counts=[0]*4;bomb_counts=[0]*4;labels=Counter()
    for ranks in armies:
        candidates=[g for g in source_geometries()if ranks[g.flag]==11 and
                    all(ranks[s]==10 for s in g.bombs)and all(ranks[s]<10 for s in g.mobiles)]
        assert len(candidates)==1,'Source structural constraints contradicted or shell ambiguous'
        g=candidates[0];labels[g.label]+=1
        eligible=set(range(40))-{g.flag}-set(g.bombs)-set(g.mobiles)
        for s in eligible:
            eligible_counts[s//10]+=1;bomb_counts[s//10]+=ranks[s]==10
    odds=[(b+1)/(n-b+1)for b,n in zip(bomb_counts,eligible_counts)]
    weights=[odds[s//10]for s in range(40)]
    return weights,dict(eligible_by_canonical_row=eligible_counts,residual_Bombs_by_row=bomb_counts,
        smoothed_row_odds=odds,geometry_counts=dict(labels),fit='Fixed Beta(1,1) odds, not exact maximum conditional likelihood.')
