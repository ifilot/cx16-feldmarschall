"""Bounded public missed-free-capture evidence for source-template inference.

The model retains one soft observation, not one factor per repeated idle turn.
Only the eight source-template components have an action model. The procedural
background deliberately receives likelihood one and remains uniform conditional
on hard rank/movement evidence. This is a declared misspecified population model,
not a logical rank deduction or calibrated likelihood.
"""
import argparse
from pathlib import Path

from campaign_native_template import NativeTemplateBot
from campaign_template_beliefs import TemplateMixtureBeliefs
from feldmarschall import LAKES, battle, parse_square


def adjacent(square):
    row,col=divmod(square,10)
    return [r*10+c for r,c in ((row-1,col),(row+1,col),(row,col-1),(row,col+1))
            if 0<=r<10 and 0<=c<10 and r*10+c not in LAKES]


def attacks(source,target,rank,tokens):
    if target in adjacent(source):return rank<10
    if rank!=8 or source//10!=target//10 and source%10!=target%10:return False
    step=(1 if target>source else -1) if source//10==target//10 else (10 if target>source else -10)
    return all(s not in tokens and s not in LAKES for s in range(source+step,target,step))


class MissedCaptureBeliefs(TemplateMixtureBeliefs):
    """One half-likelihood on a foregone, unprotected, disclosed capture."""
    def __init__(self):
        super().__init__()
        self.disclosed=set();self.miss=None;self.enemy_shuttle=None
        self.miss_events=0

    def opportunities(self,actor):
        candidates=[]
        for target,victim in self.tokens.items():
            if victim[0]!=self.army or victim not in self.disclosed:continue
            rank=self.known[victim]
            if rank>6:continue  # Only clearly valuable disclosed soldiers.
            # Geometry-only protection test. Any own mobile recapture ray is
            # enough to reject the opportunity, regardless of hidden rank.
            if any(token[0]==self.army and sq!=target and
                   attacks(sq,target,self.known[token],self.tokens)
                   for sq,token in self.tokens.items()):continue
            for source in adjacent(target):
                token=self.tokens.get(source)
                if token is None or token[0]==self.army or token==actor or token in self.known:continue
                if self.enemy_shuttle is not None:
                    old_source,old_target,count=self.enemy_shuttle
                    if count>=5 and source==old_target and target==old_source:continue
                candidates.append((rank,token[1],source,target))
        return sorted(candidates)

    def observe(self,words):
        if not words:return
        command=words[0]
        if command=='new':
            super().observe(words)
            self.disclosed=set();self.miss=None;self.enemy_shuttle=None;self.miss_events=0
            return
        pending=None;disclosed=set();actor=None;src=dst=None
        if command in ('moved','battle'):
            src,dst=map(parse_square,words[1:3]);actor=self.tokens.get(src)
            if command=='battle':disclosed={actor,self.tokens.get(dst)}
            elif abs(src//10-dst//10)+abs(src%10-dst%10)>1:disclosed={actor}
            if command=='moved' and actor is not None and actor[0]!=self.army and self.miss is None:
                choices=self.opportunities(actor)
                if choices:
                    rank,origin,source,target=choices[0]
                    pending=dict(origin=origin,victim_rank=rank,source=source,target=target,ply=self.plies)
        super().observe(words)  # Validate entire event before committing evidence.
        self.disclosed.update(disclosed-{None})
        if actor is not None and actor[0]!=self.army:
            previous=self.enemy_shuttle
            count=previous[2]+1 if previous and previous[0]==dst and previous[1]==src else 1
            self.enemy_shuttle=(src,dst,count)
        if pending is not None:self.miss=pending;self.miss_events+=1
        if self.miss is not None and (1-self.army,self.miss['origin']) in self.known:self.miss=None

    def posterior(self):
        weights,report=super().posterior()
        if self.miss is not None:
            origin=self.miss['origin'];victim=self.miss['victim_rank']
            factors=[.5 if battle(t[origin],victim)=='attacker' else 1. for t in self.templates]+[1.]
            values=[w*f for w,f in zip(weights,factors)];total=sum(values)
            weights=[v/total for v in values]
            report.update(template_probabilities=weights[:-1],background_probability=weights[-1])
        report['missed_free_capture']=self.miss
        report['miss_events']=self.miss_events
        return weights,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--difficulty',choices=('normal',),default='normal')
    parser.add_argument('--missed-captures',action='store_true',required=True,
                        help='explicit activation of the bounded missed-capture model')
    args=parser.parse_args()
    NativeTemplateBot(args.observer,args.difficulty,model=MissedCaptureBeliefs()).run()


if __name__=='__main__':main()
