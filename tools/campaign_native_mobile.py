"""One native move with public per-piece mobile capture expectations."""
import argparse
import hashlib
from pathlib import Path
import time
from campaign_native_template import NativeTemplateBot
from campaign_native_beliefs import quantize
from campaign_mobile_capture import adjustments
from feldmarschall import parse_square,square_name

class MobileCaptureBot(NativeTemplateBot):
    def __init__(self,observer,difficulty='normal'):
        if difficulty!='normal':raise ValueError('mobile capture experiment requires Classic Normal')
        super().__init__(observer,difficulty)
    def observe(self,words):
        if words and words[0]=='rules' and words[1:]!=['0']:raise ValueError('Classic rules required')
        return super().observe(words)
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
        self.observer.send('ranked');scores={};credit={}
        while True:
            line=self.observer.read();words=line.split()
            if words and words[0]=='error':raise RuntimeError(line)
            if words and words[0] in ('candidate','credit'):
                if len(words)!=4:raise ValueError('invalid scored trace')
                source,target,value=map(int,words[1:]);column=scores if words[0]=='candidate' else credit
                if (source,target) in column:raise ValueError('duplicate trace')
                column[source,target]=value
            elif words and words[0]=='move':
                parent=None if words[1:]==['none'] else tuple(map(parse_square,words[1:]));break
        if parent is None:
            if scores:raise ValueError('no move with nonempty native scores')
            self.last_report=dict(mode='template-mobile-captures',selected=None);return None
        if parent not in scores or any(move not in credit and score<30000 for move,score in scores.items()):
            raise ValueError('complete native scores and nonterminal danger credits required')
        delta,report=adjustments(cells,army,lost_counts,remaining,marginals,flag,bomb,scores,credit)
        selected=max(scores,key=lambda move:(scores[move]+delta[move],move==parent))
        if selected!=parent:self.observer.ask('played '+' '.join(map(square_name,selected)),'playedok')
        _,posterior=self.model.posterior()
        self.last_report=dict(mode='template-mobile-captures',army=army,public_board_hex=bytes(cells).hex(),lost_hex=lost,
            remaining=remaining,marginals=marginals,q12=dict(flag=flag,bomb=bomb,mobile=mobile),component_posterior=posterior,
            packet_sha256=hashlib.sha256(packet.encode()).hexdigest(),native_selected=parent,selected=selected,
            overridden=selected!=parent,capture_adjustment=report,elapsed_seconds=time.perf_counter()-started)
        return selected

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--difficulty',choices=['normal'],default='normal')
    parser.add_argument('--mobile-captures',action='store_true',required=True)
    args=parser.parse_args();MobileCaptureBot(args.observer,args.difficulty).run()

if __name__=='__main__':main()
