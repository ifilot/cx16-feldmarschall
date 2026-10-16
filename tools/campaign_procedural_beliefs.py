"""Analytic source-informed procedural background for honest native priors.

The fixed model marginalizes all compatible immobile subsets. It consumes only
public original-token facts and legitimate own ranks, never an enemy army or RNG.
"""
from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import json
from feldmarschall import COUNTS
from campaign_template_beliefs import TemplateMixtureBeliefs,background_log_evidence


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



class BackrowModel:
    """Uniform legal army conditioned on Flag in a specified original row set."""
    def __init__(self,counts=COUNTS,flag_sites=range(30,40)):
        self.counts=tuple(counts);self.size=sum(counts);self.bomb=len(counts)-2;self.flag=len(counts)-1
        self.flag_sites=frozenset(flag_sites)
        if not self.flag_sites or not self.flag_sites<=set(range(self.size))or counts[-1]!=1:
            raise ValueError('valid singleFlag location set required')

    def predict(self,known,moved,with_bombs=True):
        known={int(o):r for o,r in known.items()};moved=set(moved)
        uniform=background_log_evidence(known,moved,counts=self.counts,mobile_types=self.bomb)
        if not math.isfinite(uniform):return dict(log_evidence=-math.inf,flag=None,bomb=None)
        known_flags={o for o,r in known.items()if r==self.flag}
        unknown=set(range(self.size))-set(known)-moved
        flags=[0.]*self.size;bombs=[0.]*self.size
        prior_backrow=len(self.flag_sites)/self.size
        if known_flags:
            flag=next(iter(known_flags))
            if flag not in self.flag_sites:return dict(log_evidence=-math.inf,flag=None,bomb=None)
            flags[flag]=1.;ratio=1/prior_backrow
        else:
            sites=unknown&self.flag_sites
            if not sites:return dict(log_evidence=-math.inf,flag=None,bomb=None)
            for o in sites:flags[o]=1/len(sites)
            ratio=len(sites)/(len(unknown)*prior_backrow)
        if with_bombs:
            remaining=self.counts[self.bomb]-sum(r==self.bomb for r in known.values())
            for o,r in known.items():bombs[o]=float(r==self.bomb)
            for o in unknown:
                denominator=len(unknown)if known_flags else len(unknown)-1
                bombs[o]=remaining*(1-flags[o])/denominator if denominator else 0.
            if abs(sum(bombs)-self.counts[self.bomb])>1e-8:raise ValueError('backrow Bomb inventory mismatch')
        return dict(log_evidence=uniform+math.log(ratio),flag=flags,bomb=bombs if with_bombs else None)


class ProceduralTemplateBeliefs(TemplateMixtureBeliefs):
    """Native-only source prior with a fixed positive uniform legal-army tail.

    Component order is8templates, structural background, uniform background.
    The native consumer receives Flag/Bomb marginals; full template mobile
    correlations are therefore dropped by that consumer, as in its predecessor.
    """
    def __init__(self,parameters):
        super().__init__()
        if parameters.get('schema')!='dos-procedural-background-v1':raise ValueError('unsupported procedural model schema')
        mass=parameters.get('template_mass')
        if isinstance(mass,bool)or mass not in(0.,.8):raise ValueError('v1 supports the fixed0.8 mixture or explicit0.0 template ablation')
        self.template_mass=mass
        self.background_mass=.2 if mass==.8 else 1.
        epsilon=parameters.get('epsilon');rows=parameters.get('row_weights')
        kind=parameters.get('background_kind','structured')
        if kind not in('structured','backrow'):raise ValueError('valid procedural background kind required')
        if isinstance(epsilon,bool)or not isinstance(epsilon,(float,int))or not math.isfinite(epsilon)or not 0<epsilon<=1:
            raise ValueError('positive uniform support required')
        if kind=='structured'and(not isinstance(rows,list)or len(rows)!=4 or any(isinstance(w,bool)or not isinstance(w,(float,int))or not math.isfinite(w)or w<=0 for w in rows)):
            raise ValueError('four positive finite row weights required')
        self.epsilon=float(epsilon)
        self.background_kind=kind
        self.structural=StructuralModel(weights=[rows[s//10]for s in range(40)])if kind=='structured'else BackrowModel()
        self._cache_key=None;self._cache=None
        self.cache_hits=0;self.cache_misses=0

    @classmethod
    def load(cls,path):return cls(json.loads(Path(path).read_text()))

    def observe(self,words):
        result=super().observe(words)
        if words and words[0]=='new':
            self._cache_key=None;self._cache=None;self.cache_hits=self.cache_misses=0
        return result

    def _posterior_cached(self):
        if self.army is None:raise ValueError('new game required')
        known={o:r for(owner,o),r in self.known.items()if owner!=self.army}
        moved={o for owner,o in self.moved if owner!=self.army}
        key=(self.army,tuple(sorted(known.items())),tuple(sorted(moved)))
        if key==self._cache_key:
            self.cache_hits+=1
            return self._cache
        self.cache_misses+=1
        structural=self.structural.predict(known,moved,with_bombs=True)
        uniform=background_log_evidence(known,moved)
        if not math.isfinite(uniform):raise ValueError('impossible public evidence')
        compatible=[all(template[o]==r for o,r in known.items())and all(template[o]<10 for o in moved)for template in self.templates]
        logs=[math.log(.1)if allowed and self.template_mass else-math.inf for allowed in compatible]
        source_log=math.log(self.background_mass*(1-self.epsilon))+structural['log_evidence']if self.epsilon<1 else-math.inf
        uniform_log=math.log(self.background_mass*self.epsilon)+uniform
        logs.extend((source_log,uniform_log));maximum=max(logs)
        weights=[math.exp(value-maximum)for value in logs];total=sum(weights);weights=[value/total for value in weights]
        bgmax=max(source_log,uniform_log)
        bglog=bgmax+math.log(math.exp(source_log-bgmax)+math.exp(uniform_log-bgmax))-math.log(self.background_mass)
        report=dict(schema='dos-procedural-background-v1',epsilon=self.epsilon,background_kind=self.background_kind,template_mass=self.template_mass,
            template_probabilities=weights[:8],component_probabilities=weights[:],
            background_probability=sum(weights[8:]),structural_background_probability=weights[8],uniform_background_probability=weights[9],
            background_log_evidence=bglog,uniform_log_evidence=uniform,
            structural_log_evidence=structural['log_evidence']if math.isfinite(structural['log_evidence'])else None,
            known_origins=len(known),moved_unknown_origins=len(moved-set(known)),
            approximation=('Source Flag/screen geometry and residual Bomb row weights; exchangeable mobile ranks and approximate original RNG priors.'
                if self.background_kind=='structured' else
                'Uniform legal armies conditioned on a back-row Flag; exchangeable mobile ranks, with a positive uniform legal-army tail.'))
        self._cache_key=key;self._cache=(weights,report,structural)
        return self._cache

    def posterior(self):
        weights,report,_=self._posterior_cached()
        report=dict(report);report['template_probabilities']=report['template_probabilities'][:]
        report['component_probabilities']=report['component_probabilities'][:]
        return weights[:],report

    def rank_marginals(self,cells,army,lost,histories):
        slots,remaining,origins=self._prepare(cells,lost,histories,army)
        weights,_,structural=self._posterior_cached()
        U=sum(histories[sq][-1]==4095 for sq in slots)
        H=sum(remaining[:10]);I=sum(remaining[10:])
        if I>U:raise ValueError('inconsistent immobile slots')
        result={sq:[0.]*12 for sq in slots}
        for origin,sq in origins.items():
            moved=histories[sq][-1]==1023
            uf=remaining[11]/U if U and not moved else 0.
            ub=remaining[10]/U if U and not moved else 0.
            sf=structural['flag'][origin]if weights[8]else 0.
            sb=structural['bomb'][origin]if weights[8]else 0.
            um=max(0.,1-uf-ub);sm=max(0.,1-sf-sb)
            for rank,count in enumerate(remaining[:10]):
                result[sq][rank]=(weights[9]*um+weights[8]*sm)*count/H if H else 0.
            result[sq][10]=weights[9]*ub+weights[8]*sb
            result[sq][11]=weights[9]*uf+weights[8]*sf
            for template,weight in zip(self.templates,weights[:8]):result[sq][template[origin]]+=weight
        for probabilities in result.values():
            if abs(sum(probabilities)-1)>1e-8:raise ValueError('procedural marginal row does not sum to1')
        for rank,count in enumerate(remaining):
            if abs(sum(p[rank]for p in result.values())-count)>1e-7:raise ValueError('procedural marginals violate public inventory')
        return result,remaining

    def sample_worlds(self,*args,**kwargs):
        raise NotImplementedError('ProceduralTemplateBeliefs v1 supports native marginals only')
