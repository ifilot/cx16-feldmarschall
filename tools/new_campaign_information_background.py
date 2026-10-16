"""Exact uniform-background conditioning for one public missed-capture clue.

Extends the separately retained template-only preflight. One soft likelihood
can change contact risk even after public disclosures rule out every template.
"""
import argparse
from collections import Counter
from pathlib import Path

from campaign_native_template import NativeTemplateBot
from campaign_template_beliefs import TemplateMixtureBeliefs
from feldmarschall import COUNTS,battle
from new_campaign_information import MissedCaptureBeliefs


def background_row(remaining,U,moved):
    H=sum(remaining[:10]);I=sum(remaining[10:])
    return [n/H if moved and r<10 and H else
            n*(U-I)/(U*H) if not moved and r<10 and U and H else
            n/U if not moved and r>=10 and U else 0.
            for r,n in enumerate(remaining)]


def condition_background(remaining,U,clue_moved,likelihood):
    row=background_row(remaining,U,clue_moved)
    mass=[p*likelihood(r) for r,p in enumerate(row)];Z=sum(mass)
    conditioned=[p/Z for p in mass]
    other={False:[0.]*12,True:[0.]*12}
    for rank,p in enumerate(conditioned):
        if not p:continue
        rest=remaining[:];rest[rank]-=1
        for is_moved in (False,True):
            values=background_row(rest,U-(not clue_moved),is_moved)
            for r,value in enumerate(values):other[is_moved][r]+=p*value
    return conditioned,other,Z


class MissedCaptureRankBeliefs(MissedCaptureBeliefs):
    def context(self):
        known=Counter(rank for (owner,origin),rank in self.known.items() if owner!=self.army)
        remaining=[n-known[r] for r,n in enumerate(COUNTS)]
        moved={origin for owner,origin in self.moved if owner!=self.army and (owner,origin) not in self.known}
        return remaining,sum(remaining)-len(moved),moved

    def likelihood(self,rank):
        return .5 if rank<10 and battle(rank,self.miss['victim_rank'])=='attacker' else 1.

    def posterior(self):
        weights,report=TemplateMixtureBeliefs.posterior(self)
        if self.miss is not None:
            remaining,U,moved=self.context();origin=self.miss['origin']
            base=background_row(remaining,U,origin in moved)
            normalizer=sum(p*self.likelihood(r) for r,p in enumerate(base))
            factors=[self.likelihood(t[origin]) for t in self.templates]+[normalizer]
            weighted=[w*f for w,f in zip(weights,factors)];total=sum(weighted)
            weights=[w/total for w in weighted]
            report.update(template_probabilities=weights[:-1],background_probability=weights[-1],
                          background_miss_normalizer=normalizer)
        report.update(missed_free_capture=self.miss,miss_events=self.miss_events)
        return weights,report

    def rank_marginals(self,cells,army,lost,histories):
        if self.miss is None:return TemplateMixtureBeliefs.rank_marginals(self,cells,army,lost,histories)
        slots,remaining,origins=self._prepare(cells,lost,histories,army)
        weights,_=self.posterior();_,U,moved=self.context();clue=self.miss['origin']
        if clue not in origins:raise ValueError('missed-opportunity clue has no hidden public token')
        conditioned,other,Z=condition_background(remaining,U,clue in moved,self.likelihood)
        result={}
        for origin,square in origins.items():
            background=conditioned if origin==clue else other[origin in moved]
            values=[weights[-1]*p for p in background]
            for template,weight in zip(self.templates,weights[:-1]):values[template[origin]]+=weight
            result[square]=values
        return result,remaining


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--difficulty',choices=('normal',),default='normal')
    parser.add_argument('--missed-background-captures',action='store_true',required=True)
    args=parser.parse_args()
    NativeTemplateBot(args.observer,args.difficulty,model=MissedCaptureRankBeliefs()).run()


if __name__=='__main__':main()
