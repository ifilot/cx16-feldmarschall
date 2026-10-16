"""Source-vacancy-corrected public missed-capture background policy, v2.

Only the eligibility geometry differs from v1: test recapture rays after the
specific hypothetical enemy attacker has vacated its source. Uniform posterior
conditioning, event lifetime, factor strength and all native consumers are
inherited unchanged.
"""
import argparse
from pathlib import Path

from campaign_native_template import NativeTemplateBot
from new_campaign_information import adjacent,attacks
from new_campaign_information_background import MissedCaptureRankBeliefs


class SourceVacancyMissedCaptureBeliefs(MissedCaptureRankBeliefs):
    def opportunities(self,actor):
        candidates=[]
        for target,victim in self.tokens.items():
            if victim[0]!=self.army or victim not in self.disclosed:continue
            rank=self.known[victim]
            if rank>6:continue
            for source in adjacent(target):
                token=self.tokens.get(source)
                if token is None or token[0]==self.army or token==actor or token in self.known:continue
                if self.enemy_shuttle is not None:
                    old_source,old_target,count=self.enemy_shuttle
                    if count>=5 and source==old_target and target==old_source:continue
                after=self.tokens.copy();after.pop(source);after[target]=token
                if any(ally[0]==self.army and sq!=target and
                       attacks(sq,target,self.known[ally],after)
                       for sq,ally in self.tokens.items()):continue
                candidates.append((rank,token[1],source,target))
        return sorted(candidates)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--difficulty',choices=('normal',),default='normal')
    parser.add_argument('--missed-background-captures',action='store_true',required=True)
    args=parser.parse_args()
    NativeTemplateBot(args.observer,args.difficulty,model=SourceVacancyMissedCaptureBeliefs()).run()


if __name__=='__main__':main()
