"""Honest joint setup-style posterior with an exact Flag/Bomb subset draw.

P(z,F,B) = pi[z] * phi[z,row(F)]/10 * exp(theta[z]*adjacent(F,B))
           / Z(F,theta[z]), with exactly six Bombs and one Flag.
The two latent styles are fitted on historical development setups. Public
movement excludes immobile ranks; public Bomb disclosures are retained even
after capture. No opponent setup, referee board, or concealed rank is accepted.

Conditional subset sums are tiny hypergeometric sums, so joint setup draws
need neither MCMC nor importance correction. Existing approach/retreat factors
are returned separately, preserving the teacher's behavioral target and its
usual finite-batch self-normalized importance approximation.
"""
import json
import math
from pathlib import Path

from calibrated_beliefs import unknowns
from feldmarschall import COUNTS, GLYPHS, LAKES, battle, parse_square, setup_squares, valid_setup

SCHEMA='joint-flag-bomb-setup-styles-v1'


def neighbors(square):
    row,col=divmod(square,10)
    return frozenset(r*10+c for r,c in ((row-1,col),(row+1,col),(row,col-1),(row,col+1))
                     if 0<=r<4 and 0<=c<10)


def subset_sum(adjacent,total,count,theta):
    """Sum exp(theta * number adjacent) over count-subsets of total sites."""
    if not 0<=adjacent<=total or count<0 or count>total:return 0.
    return sum(math.comb(adjacent,j)*math.comb(total-adjacent,count-j)*math.exp(theta*j)
               for j in range(max(0,count-(total-adjacent)),min(adjacent,count)+1))


def weighted_choice(items,weights,rng):
    total=sum(weights)
    if total<=0 or not math.isfinite(total):raise ValueError('empty joint posterior')
    value=rng.random()*total
    for item,weight in zip(items,weights):
        value-=weight
        if value<0:return item
    return items[-1]


class JointSetupBeliefs:
    def __init__(self,document):
        if document.get('schema')!=SCHEMA:raise ValueError('unsupported joint setup model')
        self.document=document
        self.weights=document['weights'];self.phi=document['phi'];self.theta=document['theta']
        if len(self.weights)!=2 or len(self.phi)!=2 or len(self.theta)!=2:raise ValueError('two setup styles required')
        if any(not math.isfinite(v) or v<=0 for v in self.weights) or abs(sum(self.weights)-1)>1e-9:
            raise ValueError('invalid style probabilities')
        if any(not math.isfinite(v) or abs(v)>8 for v in self.theta):raise ValueError('invalid setup interaction')
        for row in self.phi:
            if len(row)!=4 or any(not math.isfinite(v) or v<=0 for v in row) or abs(sum(row)-1)>1e-9:
                raise ValueError('invalid Flag row probabilities')
        self.army=None

    @classmethod
    def load(cls,path):return cls(json.loads(Path(path).read_text()))

    def reset(self,army):
        if army not in (0,1):raise ValueError('invalid army')
        self.army=army;self.plies=0
        self.tokens={sq:(owner,origin) for owner in (0,1) for origin,sq in enumerate(setup_squares(owner))}
        self.known={};self.moved=set();self.lost=[0]*12

    def observe(self,words):
        """Consume protocol tokens; own setup plus public events only.

        Unknown enemy origins start with no rank. Both armies' physical tokens
        are tracked only so battle ownership, move paths and disclosed ranks can
        be checked. Irreversible Bomb disclosures survive removal of the token.
        """
        if not words:return
        command=words[0]
        if command=='opponent-setup':raise ValueError('joint public model rejects opponent setup')
        if command=='new':
            if len(words)!=2 or words[1] not in ('red','blue'):raise ValueError('invalid new game')
            self.reset(int(words[1]=='blue'));return
        if command=='rules' and words[1:]!=['0']:raise ValueError('joint model supports Classic only')
        if command not in ('setup','moved','battle'):return
        if self.army is None:raise ValueError('new game required before public history')
        if command=='setup':
            if len(words)==1:return # native chooses own army; no enemy information
            if len(words)!=2 or self.plies or not valid_setup(words[1]):raise ValueError('invalid own setup')
            for origin,glyph in enumerate(words[1]):self.known[self.army,origin]=GLYPHS.index(glyph)
            return
        if len(words)!=(3 if command=='moved' else 5):raise ValueError('invalid public event')
        src,dst=map(parse_square,words[1:3]);actor=self.tokens.get(src);target=self.tokens.get(dst)
        if actor is None or src==dst or dst in LAKES or actor[0]!=self.plies%2:
            raise ValueError('invalid public actor or turn')
        dr,dc=dst//10-src//10,dst%10-src%10
        if dr and dc:raise ValueError('public move must be orthogonal')
        distance=abs(dr)+abs(dc)
        step=(10 if dr>0 else -10) if dr else (1 if dc>0 else -1)
        if any(sq in self.tokens or sq in LAKES for sq in range(src+step,dst,step)):
            raise ValueError('blocked public path')
        known=self.known.copy();lost=self.lost[:]
        def disclose(token,rank):
            if token in known and known[token]!=rank:raise ValueError('contradictory public disclosure')
            if token in self.moved and rank>=10:raise ValueError('moved piece cannot be immobile')
            known[token]=rank
        if command=='moved':
            if target is not None:raise ValueError('occupied quiet destination')
            rank=known.get(actor)
            if rank is not None and (rank>=10 or distance>1 and rank!=8):raise ValueError('invalid disclosed move')
            if distance>1:disclose(actor,8)
            outcome='attacker'
        else:
            if target is None or target[0]==actor[0] or any(len(g)!=1 or g not in GLYPHS for g in words[3:]):
                raise ValueError('invalid public battle')
            attacker,defender=(GLYPHS.index(g) for g in words[3:])
            if attacker>=10 or distance>1 and attacker!=8:raise ValueError('invalid battle movement')
            disclose(actor,attacker);disclose(target,defender)
            outcome=battle(attacker,defender)
            for token,rank,falls in ((actor,attacker,outcome!='attacker'),(target,defender,outcome!='defender')):
                if falls and token[0]!=self.army:lost[rank]+=1
        for rank,count in enumerate(COUNTS):
            if sum(owner!=self.army and value==rank for (owner,_),value in known.items())>count:
                raise ValueError('public disclosures exceed rank inventory')
        # Commit only after every public-event invariant has been checked.
        self.known=known;self.lost=lost;self.moved.add(actor);self.tokens.pop(src)
        if outcome=='attacker':self.tokens[dst]=actor
        elif outcome=='both':self.tokens.pop(dst)
        self.plies+=1

    def conditional(self,flag_sites,bomb_sites,fixed_bombs):
        """Exact unnormalized (style, Flag-origin) posterior, conditional on clues."""
        flag_sites=set(flag_sites);bomb_sites=set(bomb_sites);fixed_bombs=set(fixed_bombs)
        if any(not isinstance(s,int) or not 0<=s<40 for s in flag_sites|bomb_sites|fixed_bombs):
            raise ValueError('invalid original setup square')
        if bomb_sites&fixed_bombs or flag_sites&fixed_bombs:raise ValueError('inconsistent public Bomb identities')
        count=6-len(fixed_bombs);items=[];weights=[]
        for flag in sorted(flag_sites):
            available=bomb_sites-{flag};adj=neighbors(flag)
            for style in range(2):
                theta=self.theta[style]
                evidence=subset_sum(len(adj&available),len(available),count,theta)
                weight=(self.weights[style]*self.phi[style][flag//10]/10*
                        math.exp(theta*len(adj&fixed_bombs))*evidence/
                        subset_sum(len(adj),39,6,theta))
                if weight>0:items.append((style,flag));weights.append(weight)
        if not items:raise ValueError('public history has no compatible joint setup')
        return items,weights

    def draw_immobiles(self,flag_sites,bomb_sites,fixed_bombs,rng,prepared=None):
        items,weights=prepared or self.conditional(flag_sites,bomb_sites,fixed_bombs)
        style,flag=weighted_choice(items,weights,rng)
        available=set(bomb_sites)-{flag};adj=sorted(available&neighbors(flag));other=sorted(available-set(adj))
        count=6-len(fixed_bombs);theta=self.theta[style]
        choices=list(range(max(0,count-len(other)),min(len(adj),count)+1))
        probabilities=[math.comb(len(adj),n)*math.comb(len(other),count-n)*math.exp(theta*n) for n in choices]
        n=weighted_choice(choices,probabilities,rng)
        bombs=set(rng.sample(adj,n)+rng.sample(other,count-n))
        return style,flag,bombs

    def sample_worlds(self,cells,lost,histories,rng,army,samples):
        if self.army!=army:raise ValueError('joint public history belongs to another side')
        if not isinstance(samples,int) or isinstance(samples,bool) or samples<1:raise ValueError('positive samples required')
        if lost!=self.lost:raise ValueError('public captured inventory differs from event history')
        slots,remaining=unknowns(cells,lost,histories,army)
        origins={};flag_sites=set();bomb_sites=set();known_flag=None
        for square,cell in enumerate(cells):
            token=self.tokens.get(square)
            if cell>=254:
                if token is not None:raise ValueError('public occupancy differs from event history')
                continue
            if token is None or token[0]!=int(bool(cell&16)):raise ValueError('public owner differs from event history')
            if token[0]==army:continue
            known=self.known.get(token)
            if cell&32:
                if known!=cell&15:raise ValueError('public known rank differs from event history')
                if known==11:known_flag=token[1]
            else:
                if known is not None:raise ValueError('disclosed enemy incorrectly concealed')
                h=histories[square]
                if setup_squares(1-army)[token[1]]!=h[2]:raise ValueError('public origin differs from event history')
                if h[-1] not in (1023,4095):raise ValueError('unsupported narrow public mask')
                origins[token[1]]=square
                if h[-1]&(1<<11):flag_sites.add(token[1])
                if h[-1]&(1<<10):bomb_sites.add(token[1])
        if known_flag is not None:flag_sites={known_flag}
        fixed_bombs={origin for (owner,origin),rank in self.known.items() if owner!=army and rank==10}
        prepared=self.conditional(flag_sites,bomb_sites,fixed_bombs)
        draws=[]
        for _ in range(samples):
            _,flag,bombs=self.draw_immobiles(flag_sites,bomb_sites,fixed_bombs,rng,prepared)
            world=cells[:];counts=remaining[:]
            assigned={origin:10 for origin in bombs}
            if flag in origins:assigned[flag]=11
            for origin,rank in assigned.items():
                square=origins[origin];world[square]=(world[square]&240)|rank;counts[rank]-=1
            if min(counts)<0 or counts[10:]!=[0,0]:raise ValueError('joint sample violates immobile inventory')
            mobile=[rank for rank,count in enumerate(counts[:10]) for _ in range(count)]
            rng.shuffle(mobile)
            targets=[sq for sq in slots if sq not in {origins[o] for o in assigned}]
            if len(targets)!=len(mobile):raise ValueError('joint sample violates remaining inventory')
            for sq,rank in zip(targets,mobile):world[sq]=(world[sq]&240)|rank
            weight=1.
            for sq,h in histories.items():
                rank=world[sq]&15
                if not h[-1]&(1<<rank):raise ValueError('joint sample violates public mask')
                weight*=1+int(h[8]<12 and battle(rank,h[8])=='attacker')+int(h[9]<12 and battle(h[9],rank)=='attacker')
            draws.append((world,weight))
        return draws
