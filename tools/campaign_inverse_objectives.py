"""Own-objective features for honest, inverse-planning-inspired rank inference.

The opponent's observed motion is conditioned on OUR legitimately known Flag
and Spy locations. No concealed enemy rank, opponent setup or future event is
read. This is a bounded conditional feature model, not a full inverse planner.
Motivation: Baker, Saxe and Tenenbaum (2009), doi:10.1016/j.cognition.2009.07.005.
"""
from collections import deque
import math

from calibrated_beliefs import BeliefModel
from campaign_joint_beliefs import JointSetupBeliefs,SCHEMA as JOINT_SCHEMA
from feldmarschall import LAKES,parse_square,setup_squares

FEATURE_SIZES=(6,6,4,6,4)
FEATURE_NAMES=('own_flag_distance','net_flag_progress','last_flag_progress',
               'own_spy_distance','last_spy_progress')
SCHEMA='own-objective-conditional-beliefs-v1'
TRACKING_DOCUMENT=dict(schema=JOINT_SCHEMA,weights=[.5,.5],phi=[[.25]*4,[.25]*4],theta=[0.,0.])


def distances():
    result=[]
    for start in range(100):
        values=[100]*100
        if start not in LAKES:
            values[start]=0;queue=deque([start])
            while queue:
                square=queue.popleft();row,col=divmod(square,10)
                for r,c in ((row-1,col),(row+1,col),(row,col-1),(row,col+1)):
                    if 0<=r<10 and 0<=c<10:
                        nxt=r*10+c
                        if nxt not in LAKES and values[nxt]>values[square]+1:
                            values[nxt]=values[square]+1;queue.append(nxt)
        result.append(tuple(values))
    return tuple(result)


DISTANCES=distances()


def mirror(square):return square//10*10+9-square%10
def distance_bucket(value):return 0 if value<=1 else 1 if value<=3 else 2 if value<=5 else 3 if value<=8 else 4
def progress_bucket(value):return 0 if value<-3 else 1 if value<0 else 2 if value==0 else 3 if value<=3 else 4
def step_bucket(value):return 3 if value is None else 0 if value<0 else 1 if value==0 else 2


class ObjectiveMemory:
    def __init__(self):
        # Reuse only the strict public identity/event tracker. Its setup-style
        # parameters are uniform dummy values and never enter these features.
        self.public=JointSetupBeliefs(TRACKING_DOCUMENT)
        self.last={};self.last_mirrored={};self.own_setup_recorded=False

    def observe(self,words):
        if not words:return
        if words[0]=='new':
            self.public.observe(words);self.last={};self.last_mirrored={};self.own_setup_recorded=False;return
        if self.public.army is None:
            self.public.observe(words);return
        pending=None
        if words[0] in ('moved','battle') and len(words)>=3:
            src,dst=map(parse_square,words[1:3]);actor=self.public.tokens.get(src)
            if actor is not None and actor[0]!=self.public.army:
                objectives={rank:next((sq for sq,token in self.public.tokens.items()
                    if token[0]==self.public.army and self.public.known.get(token)==rank),None) for rank in (11,9)}
                def deltas(mirrored):
                    return tuple(None if target is None else DISTANCES[src][mirror(target) if mirrored else target]-
                                 DISTANCES[dst][mirror(target) if mirrored else target] for target in objectives.values())
                pending=(actor[1],deltas(False),deltas(True))
        self.public.observe(words) # Validate before recording any feature state.
        if words[0]=='setup' and len(words)==2:self.own_setup_recorded=True
        if pending is not None:
            origin,actual,control=pending;self.last[origin]=actual;self.last_mirrored[origin]=control

    def features(self,cells,army,square,history,mirrored=False):
        if self.public.army!=army:raise ValueError('objective history belongs to another side')
        objectives={rank:next((sq for sq,cell in enumerate(cells)
            if cell<254 and bool(cell&16)==bool(army) and cell&15==rank),None) for rank in (11,9)}
        if mirrored:objectives={rank:None if sq is None else mirror(sq) for rank,sq in objectives.items()}
        flag,spy=objectives[11],objectives[9]
        origins=setup_squares(1-army)
        if history[2] not in origins:raise ValueError('invalid public enemy origin')
        origin=origins.index(history[2]);last=(self.last_mirrored if mirrored else self.last).get(origin,(None,None))
        return (5 if flag is None else distance_bucket(DISTANCES[square][flag]),
                5 if flag is None else progress_bucket(DISTANCES[history[2]][flag]-DISTANCES[square][flag]),
                step_bucket(last[0]),
                5 if spy is None else distance_bucket(DISTANCES[square][spy]),step_bucket(last[1]))


class ObjectiveBeliefs(BeliefModel):
    """Frozen old likelihoods plus bounded extra factors on public moved ranks."""
    def __init__(self,document):
        if document.get('schema')!=SCHEMA or document['feature_sizes']!=list(FEATURE_SIZES):
            raise ValueError('invalid own-objective belief document')
        super().__init__(document['base_document'])
        self.factor_document=document;self.factor_strength=document['factor_strength']
        self.selected=tuple(document['selected_features']);self.extra=document['extra_log_likelihood_ratios']
        if not 0<=self.factor_strength<=1 or not math.isfinite(self.factor_strength):raise ValueError('invalid factor strength')
        if not self.selected or any(type(i) is not int or not 0<=i<5 for i in self.selected):raise ValueError('invalid feature group')
        if len(self.extra)!=10:raise ValueError('mobile rank factors required')
        for table in self.extra:
            if len(table)!=5:raise ValueError('invalid extra feature tables')
            for row,size in zip(table,FEATURE_SIZES):
                if len(row)!=size or any(not math.isfinite(v) for v in row):raise ValueError('invalid extra likelihood')
        self.context={}

    def likelihoods(self,cells,army,square,history):
        baseline=super().likelihoods(cells,army,square,history)
        if not history[5] or self.factor_strength==0:return baseline
        values=self.context[square]
        for rank in range(10):
            extra=max(-.75,min(.75,self.factor_strength*sum(self.extra[rank][i][values[i]] for i in self.selected)))
            baseline[rank]=math.exp(max(-2.,min(2.,math.log(baseline[rank])+extra)))
        return baseline


class ObjectiveSampler(ObjectiveBeliefs):
    """Teacher-compatible sampler, with actual-input public memory ownership.

    Feed every actual protocol input to observe(), including the generated own
    setup after a bare setup request. Never observe speculative rollout events.
    The inherited sequential proposal and importance correction target the
    product of frozen base likelihoods and bounded extra conditional factors.
    Eight draws are a finite importance approximation, not exact marginals.
    """
    def __init__(self,document):
        super().__init__(document)
        self.memory=ObjectiveMemory()

    def observe(self,words):
        if words and words[0] in ('moved','battle') and self.factor_strength and not self.memory.own_setup_recorded:
            raise ValueError('own setup must be recorded before actual public events')
        self.memory.observe(words)

    def prepare(self,cells,lost,histories,army):
        if self.factor_strength==0:
            return super().prepare(cells,lost,histories,army)
        public=self.memory.public
        if not self.memory.own_setup_recorded:raise ValueError('own setup must be recorded before objective inference')
        if public.army!=army:raise ValueError('objective history belongs to another side')
        if list(lost)!=public.lost:raise ValueError('public captured inventory differs from event history')
        self.context={}
        for square,cell in enumerate(cells):
            token=public.tokens.get(square)
            if cell>=254:
                if token is not None:raise ValueError('public occupancy differs from event history')
                continue
            if token is None or token[0]!=int(bool(cell&16)):raise ValueError('public owner differs from event history')
            known=public.known.get(token)
            if token[0]==army:
                if known!=cell&15:raise ValueError('own rank differs from recorded own setup')
            elif cell&32:
                if known!=cell&15:raise ValueError('public known rank differs from event history')
            else:
                if known is not None:raise ValueError('disclosed enemy incorrectly concealed')
                history=histories[square]
                if setup_squares(1-army)[token[1]]!=history[2]:raise ValueError('public origin differs from event history')
                if bool(history[5])!=(token in public.moved):raise ValueError('public movement differs from event history')
                self.context[square]=self.memory.features(cells,army,square,history,
                    self.factor_document.get('mirrored_control',False))
        return super().prepare(cells,lost,histories,army)
