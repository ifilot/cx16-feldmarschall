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


def goal_values(cells,army,lost,remaining,marginals,flag,bomb):
    import math
    from campaign_belief_values import gain,worths,native_expected
    worth=worths(lost);h=sum(remaining[:10]);values=[[0]*100 for _ in range(10)]
    def trunc(value):
        nearest=round(value)
        return nearest if abs(value-nearest)<1e-9 else math.trunc(value)
    for rank in range(10):
        mobile_sum=sum(n*gain(rank,r,worth) for r,n in enumerate(remaining[:10]))
        for sq,row in marginals.items():
            cell=cells[sq]
            if cell>=254 or bool(cell&16)==bool(army) or cell&32:
                raise ValueError('only public concealed enemy marginals accepted')
            f,b=(0,0) if cell&64 else (flag[sq],bomb[sq]);m=4096-f-b
            immobile=f*2000+b*gain(rank,10,worth)
            baseline=(native_expected(rank,True,remaining,worth) if cell&64 else
                      ((immobile*h+m*mobile_sum)//(4096*h) if immobile*h+m*mobile_sum>=0 else
                       -(-(immobile*h+m*mobile_sum)//(4096*h))) if h else
                      trunc(immobile/4096) if not m else native_expected(rank,False,remaining,worth))
            mass=sum(row[:10]);conditional=sum(p*gain(rank,r,worth)for r,p in enumerate(row[:10]))/mass if mass else mobile_sum/h if h else 0
            # Preserve exact integer baseline when the conditional reduces to
            # exchangeability; floating cancellation must not invent a change.
            replacement=baseline if not h or abs(conditional-mobile_sum/h)<1e-9 else trunc((immobile+m*conditional)/4096)
            if not -400<=replacement<=2000:raise ValueError('goal expectation outside combat range')
            values[rank][sq]=replacement
    return values


def goal_packet(values):
    if len(values)!=10 or any(len(row)!=100 for row in values):raise ValueError('ten full actor rows required')
    if any(type(v)is not int or not -400<=v<=2000 for row in values for v in row):raise ValueError('bounded signed expectations required')
    return ''.join(f'{v&65535:04x}'for row in values for v in row)


class NativeTemplateBot(NativeBeliefBot):
    def __init__(self,observer,difficulty='normal',model=None,home_interceptor=False):
        if difficulty not in ('easy','normal','hard'):raise ValueError('valid Classic difficulty required')
        if home_interceptor and difficulty!='normal':raise ValueError('home interceptor requires Classic Normal')
        self.home_interceptor=home_interceptor
        self.mode='template';self.model=TemplateMixtureBeliefs() if model is None else model
        self.observer=observer if hasattr(observer,'ask') else Engine(shlex.quote(str(observer)))
        self.observer.send('difficulty '+difficulty);self.last_report=None

    def observe(self,words):
        if self.home_interceptor and words and words[0]=='rules' and words[1:]!=['0']:
            raise ValueError('home interceptor requires Classic rules')
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
        goals=goal_values(cells,army,lost_counts,remaining,marginals,flag,bomb)
        self.observer.ask('goal-priors '+goal_packet(goals),'goal-priorsok')
        strategy=None
        if self.home_interceptor:
            move,strategy=self.select_home_interceptor(cells,army,lost_counts,histories,shuttle)
        else:
            selected=self.observer.ask('go','move')
            move=None if selected=='none' else tuple(map(parse_square,selected.split()))
        _,posterior=self.model.posterior()
        self.last_report=dict(mode=self.mode,army=army,public_board_hex=bytes(cells).hex(),lost_hex=lost,
            remaining=remaining,marginals=marginals,q12=dict(flag=flag,bomb=bomb,mobile=mobile),
            component_posterior=posterior,
            native_approximation='Full conditional mobile beliefs in plan only; original capture expectations and danger retained.',
            packet_sha256=hashlib.sha256(packet.encode()).hexdigest(),selected=move,
            elapsed_seconds=time.perf_counter()-started)
        if strategy is not None:self.last_report['home_interceptor']=strategy
        return move

    def select_home_interceptor(self,cells,army,lost,histories,shuttle):
        """Consume one native decision and correct only a failed home schedule."""
        from campaign_home_reserve import evaluate
        self.observer.send('ranked')
        scores={}
        while True:
            line=self.observer.read()
            if line.startswith('error'):raise RuntimeError('ranked native decision: '+line)
            words=line.split()
            if words and words[0]=='candidate':
                if len(words)!=4:raise ValueError('invalid native candidate trace')
                source,target,score=map(int,words[1:])
                if (source,target) in scores:raise ValueError('duplicate native move trace')
                scores[source,target]=score
            elif words and words[0]=='move':
                move=None if words[1:]==['none'] else tuple(map(parse_square,words[1:]))
                break
        if move is None:
            if scores:raise ValueError('native reports no move with legal candidates')
            return None,dict(active=False,reason='no-moves',overridden=False)
        if move not in scores:raise ValueError('native selected move is absent from candidate trace')
        adjustments,report=evaluate(cells,army,lost,histories,scores,shuttle)
        selected=move
        if adjustments[move]<0:
            selected=max(scores,key=lambda action:(scores[action]+adjustments[action],action==move))
        if selected!=move:
            self.observer.ask('played '+' '.join(map(square_name,selected)),'playedok')
        report.update(native_selected=move,selected=selected,overridden=selected!=move)
        return selected,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--difficulty',choices=('easy','normal','hard'),default='normal')
    parser.add_argument('--procedural-model',type=Path)
    parser.add_argument('--home-interceptor',action='store_true')
    parser.add_argument('--mobile-goals',action='store_true',required=True)
    args=parser.parse_args()
    model=None
    if args.procedural_model is not None:
        from campaign_procedural_beliefs import ProceduralTemplateBeliefs
        model=ProceduralTemplateBeliefs.load(args.procedural_model)
    NativeTemplateBot(args.observer,args.difficulty,model=model,home_interceptor=args.home_interceptor).run()

if __name__=='__main__':main()
