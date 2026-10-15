"""Public-only DOS Colonel opening-template mixture, with robust uniform support.

The prior is 80% equally over four public source templates and their horizontal
reflections, 20% uniform legal armies. The background deliberately approximates
rather than reproduces the original procedural generator. Only hard public rank
and movement constraints condition this prior; opponent action likelihood is
ignored. No referee army, private deployment seed or move seed is consumed.
"""
import math
from collections import Counter
from calibrated_beliefs import unknowns
from campaign_joint_beliefs import JointSetupBeliefs, weighted_choice
from feldmarschall import COUNTS, GLYPHS, setup_squares, valid_setup

SCHEMA='dos-colonel-template-mixture-v1'
# Canonical front-first rows4..1, columns1..10; every second entry reflected.
# Public resident DS:190E tables4..7, original rank mapping via FELD_RANK.
# Pinned resident SHA256 cd8c40e2f305f2bd3656b35aa31e7baa55535db19b745e307d98e43d7ca1904f.
TEMPLATES=(
 '45263497697BS78185B6B5969B593B99878498BF',
 '96794362546B58187SB7B395B9695BFB89487899',
 '45964392697B5918S876B596895B3B987894BFB7',
 '9629346954678S8195B7B3B598695B7BFB498789',
 '596943959473S7287869B765B4B15B98989BFB86',
 '49593496959687827S37B51B4B567B68BFB98989',
 '5969439594735B817S29B68697B58B98984BFB76',
 '495934969592S718B537B85B79686B67BFB48989',
)


def log_falling(n,k):
    if not 0<=k<=n:return -math.inf
    return sum(math.log(n-j) for j in range(k))


def background_log_evidence(known,moved,counts=COUNTS,mobile_types=10):
    """Uniform labeled-origin rank/mobility event probability, in log space.

    Captured publicly revealed identities remain in `known`. `moved` includes
    historically moved origins; only undisclosed origins contribute mobility.
    This is NOT a likelihood for the enemy's choice of actions.
    """
    size=sum(counts)
    if any(not 0<=origin<size or not 0<=rank<len(counts) for origin,rank in known.items()):
        raise ValueError('invalid public original identity')
    if any(not 0<=origin<size for origin in moved):raise ValueError('invalid moved origin')
    if any(known[o]>=mobile_types for o in moved if o in known):return -math.inf
    ranks=Counter(known.values());K=len(known);M=len(set(moved)-set(known))
    numerator=sum(log_falling(count,k) for count,k in zip(counts,(ranks[r] for r in range(len(counts)))))
    remaining_mobile=sum(counts[:mobile_types])-sum(k for r,k in ranks.items() if r<mobile_types)
    return numerator-log_falling(size,K)+log_falling(remaining_mobile,M)-log_falling(size-K,M)


def component_posterior(templates,known,moved,counts=COUNTS,mobile_types=10):
    """Exact discrete-mixture component posterior under hard public evidence.

    Last component is the uniform background. Generic counts support small exact
    enumeration tests; runtime uses precisely the eight fixed Classic templates.
    """
    if not templates:raise ValueError('templates required')
    log_bg=background_log_evidence(known,moved,counts,mobile_types)
    if not math.isfinite(log_bg):raise ValueError('impossible public evidence')
    compatible=[all(template[o]==r for o,r in known.items()) and
                all(template[o]<mobile_types for o in moved) for template in templates]
    logs=[math.log(.8/len(templates)) if ok else -math.inf for ok in compatible]+[math.log(.2)+log_bg]
    maximum=max(logs);weights=[math.exp(v-maximum) for v in logs];total=sum(weights)
    return [v/total for v in weights],log_bg


class TemplateMixtureBeliefs(JointSetupBeliefs):
    """Reuse ONLY the existing validated public token-origin event tracker."""
    def __init__(self):
        if len(TEMPLATES)!=8 or any(not valid_setup(t) for t in TEMPLATES):
            raise ValueError('invalid pinned original template inventory')
        self.templates=tuple(tuple(GLYPHS.index(g) for g in t) for t in TEMPLATES)
        self.army=None

    def posterior(self):
        if self.army is None:raise ValueError('new game required')
        known={origin:rank for (owner,origin),rank in self.known.items() if owner!=self.army}
        moved={origin for owner,origin in self.moved if owner!=self.army}
        weights,log_bg=component_posterior(self.templates,known,moved)
        return weights,dict(template_probabilities=weights[:-1],background_probability=weights[-1],
                            background_log_evidence=log_bg,known_origins=len(known),
                            moved_unknown_origins=len(moved-set(known)))

    def _prepare(self,cells,lost,histories,army):
        if army not in (0,1) or len(cells)!=100 or len(lost)!=12:raise ValueError('invalid public board/inventory')
        if self.army!=army:raise ValueError('public history belongs to another army')
        if list(lost)!=self.lost:raise ValueError('captured inventory differs from public history')
        slots,remaining=unknowns(cells,lost,histories,army)
        origins={}
        for sq,cell in enumerate(cells):
            token=self.tokens.get(sq)
            if cell>=254:
                if token is not None:raise ValueError('public occupancy differs from history')
                continue
            if token is None or token[0]!=int(bool(cell&16)):raise ValueError('public owner differs from history')
            if token[0]==army:continue
            rank=self.known.get(token)
            if cell&32:
                if rank!=cell&15:raise ValueError('disclosed rank differs from history')
            else:
                if rank is not None:raise ValueError('disclosed enemy incorrectly concealed')
                h=histories[sq]
                if h[2]!=setup_squares(1-army)[token[1]]:raise ValueError('public origin differs from history')
                moved=token in self.moved
                if bool(cell&64)!=moved or h[-1]!=(1023 if moved else 4095):
                    raise ValueError('unsupported public movement mask')
                origins[token[1]]=sq
        return slots,remaining,origins

    @staticmethod
    def draw_background(cells,histories,rng,slots,remaining):
        """Exact uniform count-consistent assignment conditional on mobile masks."""
        world=list(cells);unmoved=[sq for sq in slots if histories[sq][-1]==4095]
        immobiles=[r for r in (10,11) for _ in range(remaining[r])]
        if len(immobiles)>len(unmoved):raise ValueError('inconsistent mobile evidence')
        assigned=rng.sample(unmoved,len(immobiles));rng.shuffle(immobiles)
        for sq,rank in zip(assigned,immobiles):world[sq]=(world[sq]&240)|rank
        mobile=[rank for rank,n in enumerate(remaining[:10]) for _ in range(n)];rng.shuffle(mobile)
        assigned_set=set(assigned)
        targets=[sq for sq in slots if sq not in assigned_set]
        if len(targets)!=len(mobile):raise ValueError('inconsistent mobile inventory')
        for sq,rank in zip(targets,mobile):world[sq]=(world[sq]&240)|rank
        return world

    def rank_marginals(self,cells,army,lost,histories):
        """Exact unknown-slot marginals; full template correlations are omitted.

        Native F/B consumers can use these marginals, while the teacher sampler
        retains complete correlated template assignments. Returned inventory is
        the remaining hidden-rank multiset, excluding captured/disclosed ranks.
        """
        slots,remaining,origins=self._prepare(cells,lost,histories,army)
        weights,_=self.posterior()
        U=sum(histories[sq][-1]==4095 for sq in slots)
        H=sum(remaining[:10]);I=sum(remaining[10:])
        if I>U:raise ValueError('inconsistent immobile slots')
        result={sq:[0.]*12 for sq in slots}
        for origin,sq in origins.items():
            moved=histories[sq][-1]==1023
            for rank,count in enumerate(remaining):
                if rank>=10:probability=count/U if U and not moved else 0.
                elif not H:probability=0.
                elif moved:probability=count/H
                else:probability=count*(U-I)/(U*H) if U else 0.
                result[sq][rank]=weights[-1]*probability
            for template,weight in zip(self.templates,weights[:-1]):
                result[sq][template[origin]]+=weight
        return result,remaining

    def sample_worlds(self,cells,lost,histories,rng,army,samples):
        if not isinstance(samples,int) or isinstance(samples,bool) or samples<1:raise ValueError('positive sample count required')
        slots,remaining,origins=self._prepare(cells,lost,histories,army)
        weights,_=self.posterior();draws=[]
        for _ in range(samples):
            selected=weighted_choice(list(range(9)),weights,rng)
            if selected==8:world=self.draw_background(cells,histories,rng,slots,remaining)
            else:
                world=list(cells);template=self.templates[selected]
                for origin,sq in origins.items():world[sq]=(world[sq]&240)|template[origin]
            draws.append((world,1.))
        return draws
