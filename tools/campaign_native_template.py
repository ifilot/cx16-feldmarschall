"""One native Classic move using honest source-informed opening marginals.

Only Flag/Bomb marginals reach the native evaluator. Enemy mobile ranks remain
exchangeable under public counts: this deliberately discards the full template
mobile-rank correlations preserved by the separate teacher world sampler.
"""
import argparse
import hashlib
from pathlib import Path
import shlex
import time

from campaign_native_beliefs import NativeBeliefBot,quantize
from campaign_template_beliefs import TemplateMixtureBeliefs
from feldmarschall import Engine,parse_square,square_name


class NativeTemplateBot(NativeBeliefBot):
    def __init__(self,observer,difficulty='normal'):
        if difficulty not in ('easy','normal','hard'):raise ValueError('valid Classic difficulty required')
        self.mode='template';self.model=TemplateMixtureBeliefs()
        self.observer=observer if hasattr(observer,'ask') else Engine(shlex.quote(str(observer)))
        self.observer.send('difficulty '+difficulty);self.last_report=None

    def choose(self):
        started=time.perf_counter()
        army_text,board,lost,shuttle=self.observer.ask('public','public').split()
        army=int(army_text);cells=list(bytes.fromhex(board));lost_counts=list(bytes.fromhex(lost))
        if self.model.army!=army:raise ValueError('native observer differs from public model side')
        cells=[(c&240)|12 if c<254 and bool(c&16)!=bool(army) and not c&32 else c for c in cells]
        histories={sq:list(map(int,self.observer.ask('memory '+square_name(sq),'history').split()))
                   for sq,c in enumerate(cells) if c<254 and bool(c&16)!=bool(army) and not c&32}
        marginals,remaining=self.model.rank_marginals(cells,army,lost_counts,histories)
        flag,bomb,mobile,packet=quantize(marginals,remaining)
        self.observer.ask('belief-priors '+packet,'belief-priorsok')
        selected=self.observer.ask('go','move')
        move=None if selected=='none' else tuple(map(parse_square,selected.split()))
        _,posterior=self.model.posterior()
        self.last_report=dict(mode=self.mode,army=army,public_board_hex=bytes(cells).hex(),lost_hex=lost,
            remaining=remaining,marginals=marginals,q12=dict(flag=flag,bomb=bomb,mobile=mobile),
            component_posterior=posterior,
            native_approximation='Only Flag/Bomb marginals; exchangeable mobile ranks discard template mobile-rank correlations.',
            packet_sha256=hashlib.sha256(packet.encode()).hexdigest(),selected=move,
            elapsed_seconds=time.perf_counter()-started)
        return move


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--difficulty',choices=('easy','normal','hard'),default='normal')
    args=parser.parse_args();NativeTemplateBot(args.observer,args.difficulty).run()

if __name__=='__main__':main()
