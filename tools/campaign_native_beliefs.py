"""Lightweight honest Classic opponent: analytic public priors, one native move.

No rollout engine, enemy setup, referee state or concealed rank is accepted.
Counts and joint modes use identical native code and exact count-conditioned
rank marginals; only the frozen Flag/Bomb setup prior differs.
"""
import argparse
import hashlib
import math
from pathlib import Path
import shlex
import sys
import time

from campaign_belief_values import root_marginals
from campaign_joint_beliefs import JointSetupBeliefs
from feldmarschall import Engine,parse_square,square_name

ONE=4096


def quantize(marginals,remaining):
    """Controlled two-column rounding: exact inventory totals, bounded rows.

    Floor/ceiling rounding is solved as a tiny bipartite allocation. Fractional
    Flag/Bomb entries each receive at most one extra unit. An augmenting path
    can relocate the other rank's unit when a fully immobile row is occupied.
    Thus each probability changes by less than one Q12 unit while every row's
    implied mobile+Bomb+Flag mass is exactly4096 and column inventories agree.
    """
    values=[[0]*100 for _ in (0,1)];fractions=[{},{}]
    for square,probabilities in marginals.items():
        if type(square) is not int or not 0<=square<100 or len(probabilities)!=12:
            raise ValueError('valid public rank marginals required')
        flag,bomb=probabilities[11],probabilities[10]
        if any(not math.isfinite(p) or p<0 or p>1+1e-8 for p in (flag,bomb)) or flag+bomb>1+1e-8:
            raise ValueError('invalid immobile probability')
        for rank,probability in enumerate((flag,bomb)):
            scaled=max(0.,min(float(ONE),probability*ONE))
            if abs(scaled-round(scaled))<1e-8:scaled=float(round(scaled))
            floor=math.floor(scaled);values[rank][square]=floor
            if scaled>floor:fractions[rank][square]=scaled-floor
    targets=[remaining[11]*ONE,remaining[10]*ONE]
    deficits=[targets[rank]-sum(values[rank]) for rank in (0,1)]
    if any(type(n) is not int or n<0 or n>len(fractions[rank]) for rank,n in enumerate(deficits)):
        raise ValueError('marginals do not match public immobile inventory')
    capacity=[min(2,ONE-values[0][sq]-values[1][sq]) for sq in range(100)]
    assigned=[set(),set()]
    ordered=[sorted(row,key=lambda sq:(-row[sq],sq)) for row in fractions]
    def allocate(rank,seen):
        if rank in seen:return False
        seen=seen|{rank}
        for square in ordered[rank]:
            if square in assigned[rank]:continue
            occupied=sum(square in row for row in assigned)
            if occupied<capacity[square]:assigned[rank].add(square);return True
            other=1-rank
            if square in assigned[other] and allocate(other,seen):
                assigned[other].remove(square);assigned[rank].add(square);return True
        return False
    for rank in (0,1):
        for _ in range(deficits[rank]):
            if not allocate(rank,set()):raise ValueError('cannot round public immobile marginals consistently')
    for rank in (0,1):
        for square in assigned[rank]:values[rank][square]+=1
        if sum(values[rank])!=targets[rank]:raise ValueError('rounded inventory mismatch')
    flag,bomb=values;mobile=[ONE-f-b for f,b in zip(flag,bomb)]
    if min(mobile)<0:raise ValueError('rounded immobile mass exceeds one')
    packet=''.join(f'{value:04x}' for column in values for value in column)
    if len(packet)!=800:raise ValueError('invalid Q12 prior packet')
    return flag,bomb,mobile,packet


class NativeBeliefBot:
    def __init__(self,observer,model,mode='joint',difficulty='normal'):
        if mode not in ('counts','joint') or difficulty not in ('easy','normal','hard'):
            raise ValueError('valid Classic mode and difficulty required')
        self.mode=mode
        self.model=model if isinstance(model,JointSetupBeliefs) else JointSetupBeliefs.load(model)
        self.observer=observer if hasattr(observer,'ask') else Engine(shlex.quote(str(observer)))
        self.observer.send('difficulty '+difficulty)
        self.last_report=None

    def observe(self,words):
        """Forward actual input only, retaining public initial-origin memory."""
        if not words:return None
        self.model.observe(words)
        command=' '.join(words)
        if words[0]=='new':self.last_report=None
        if words==['setup']:
            setup=self.observer.ask('setup','setup')
            self.model.observe(['setup',setup])
            return setup
        if words[0]=='played':return self.observer.ask(command,'playedok')
        self.observer.send(command)
        return None

    def choose(self):
        started=time.perf_counter()
        army_text,board,lost,shuttle=self.observer.ask('public','public').split()
        army=int(army_text);cells=list(bytes.fromhex(board));lost_counts=list(bytes.fromhex(lost))
        if self.model.army!=army:raise ValueError('native observer differs from public model side')
        cells=[(cell&240)|12 if cell<254 and bool(cell&16)!=bool(army) and not cell&32 else cell for cell in cells]
        board=bytes(cells).hex()
        histories={sq:list(map(int,self.observer.ask('memory '+square_name(sq),'history').split()))
                   for sq,cell in enumerate(cells) if cell<254 and bool(cell&16)!=bool(army) and not cell&32}
        marginals,remaining=root_marginals(cells,army,lost_counts,histories,self.model,self.mode)
        flag,bomb,mobile,packet=quantize(marginals,remaining)
        self.observer.ask('belief-priors '+packet,'belief-priorsok')
        selected=self.observer.ask('go','move')
        move=None if selected=='none' else tuple(map(parse_square,selected.split()))
        self.last_report=dict(mode=self.mode,army=army,public_board_hex=board,lost_hex=lost,
            remaining=remaining,marginals=marginals,q12=dict(flag=flag,bomb=bomb,mobile=mobile),
            packet_sha256=hashlib.sha256(packet.encode()).hexdigest(),selected=move,
            elapsed_seconds=time.perf_counter()-started)
        return move

    def close(self):self.observer.close()

    def run(self):
        try:
            for line in sys.stdin:
                words=line.split()
                if not words:continue
                command=words[0]
                if command=='feldmarschall':
                    self.model.observe(words)
                    print('id name public-native-beliefs\nid author cx16-feldmarschall tools\nok',flush=True)
                elif command=='isready':
                    self.model.observe(words);self.observer.ask('isready','readyok');print('readyok',flush=True)
                elif command=='go':
                    self.model.observe(words);move=self.choose()
                    print('move '+' '.join(map(square_name,move)) if move else 'move none',flush=True)
                elif command=='public':
                    self.model.observe(words);print('public '+self.observer.ask('public','public'),flush=True)
                elif command=='quit':self.model.observe(words);break
                else:
                    response=self.observe(words)
                    if words==['setup']:print('setup '+response,flush=True)
                    elif command=='played':print('playedok',flush=True)
        finally:self.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--mode',choices=('counts','joint'),required=True)
    parser.add_argument('--difficulty',choices=('easy','normal','hard'),default='normal')
    args=parser.parse_args()
    NativeBeliefBot(args.observer,args.model,args.mode,args.difficulty).run()


if __name__=='__main__':main()
