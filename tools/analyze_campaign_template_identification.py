"""Proposal-only exact global-Flag identification diagnostics at public openings.

Eight fixed own armies are legitimate private input; enemy occupancy is public.
Every rank used in diagnostics comes from the frozen prior, never a generated or
saved opponent army. No policy, native score correction or match is implemented.
"""
import argparse
from collections import deque
import hashlib
import json
import math
from pathlib import Path

from campaign_template_beliefs import TEMPLATES
from feldmarschall import COUNTS,GLYPHS,Position,battle,setup_squares


def entropy(probabilities):
    return -sum(p*math.log2(p) for p in probabilities if p)


def experiment(origin):
    # Exact P(observed rank,Flag origin) under the unchanged opening mixture.
    joint=[[0.]*40 for _ in range(12)]
    for template in TEMPLATES:joint[GLYPHS.index(template[origin])][template.index('F')]+=.1
    joint[11][origin]+=.2/40
    for flag in range(40):
        if flag==origin:continue
        for rank,count in enumerate(COUNTS[:11]):joint[rank][flag]+=.2/40*count/39
    marginal=[sum(row[f] for row in joint) for f in range(40)]
    probability=[sum(row) for row in joint]
    expected_entropy=sum(p*entropy([v/p for v in row]) for row,p in zip(joint,probability) if p)
    return dict(flag_entropy_before_bits=entropy(marginal),expected_flag_entropy_after_bits=expected_entropy,
                expected_flag_information_bits=entropy(marginal)-expected_entropy,
                flag_identification_probability_gain=sum(max(row) for row in joint)-max(marginal),
                observed_rank_probabilities=probability,
                expected_scout_death_probability=sum(p for rank,p in enumerate(probability) if battle(8,rank)!='attacker'),
                immediate_flag_capture_probability=probability[11])


def route(position,source,goal,can_clear):
    rank=position.cells[source][1];army=position.cells[source][0];queue=deque([(source,0)]);seen={source}
    while queue:
        sq,d=queue.popleft()
        if sq==goal:return d
        for dc,dr in ((-1,0),(1,0),(0,-1),(0,1)):
            c,r=sq%10+dc,sq//10+dr;dst=r*10+c
            if not 0<=c<10 or not 0<=r<10 or dst in seen or dst in (42,43,52,53,46,47,56,57):continue
            target=position.cells[dst]
            if target is not None:
                if target[0]==army:continue
                if not can_clear and dst!=goal:continue
                if battle(rank,target[1])!='attacker':continue
            seen.add(dst);queue.append((dst,d+1))
    return None


def audit():
    experiments={str(origin):experiment(origin) for origin in range(10)}
    openings=[];count=0
    for own_index,own_setup in enumerate(TEMPLATES):
        public=Position();public.place(0,own_setup);public.place(1,TEMPLATES[0],known=False)
        probes=[(src,dst) for src,dst in public.moves(0) if public.cells[src][1]==8 and public.cells[dst] and public.cells[dst][0]==1]
        entries=[]
        for src,dst in probes:
            origin=setup_squares(1).index(dst);followups=[]
            for template_index,enemy in enumerate(TEMPLATES):
                world=Position();world.place(0,own_setup);world.place(1,enemy)
                outcome,_=world.fight(src,dst,8,world.cells[dst][1]);flag=next(s for s,c in enumerate(world.cells) if c and c[0]==1 and c[1]==11)
                miners=[s for s,c in enumerate(world.cells) if c and c[0]==0 and c[1]==7]
                strong=[s for s,c in enumerate(world.cells) if c and c[0]==0 and c[1]<7]
                miner_distances=[d for s in miners if (d:=route(world,s,flag,True)) is not None]
                counterdist=[]
                if world.cells[dst] is None or world.cells[dst][0]==1:
                    counterdist=[d for s in strong if (d:=route(world,s,dst,False)) is not None]
                followups.append(dict(template=template_index,observed_rank=GLYPHS.index(enemy[origin]),scout_outcome=outcome,
                                      shortest_frozen_miner_flag_capture_route=min(miner_distances,default=None),
                                      shortest_strict_winning_strong_frontier_followup=min(counterdist,default=None)))
            info=experiments[str(origin)]
            entries.append(dict(move=[src,dst],enemy_original_origin=origin,**info,template_followups=followups,
                                templates_with_any_frozen_miner_flag_route=sum(r['shortest_frozen_miner_flag_capture_route'] is not None for r in followups),
                                templates_with_any_strong_frontier_followup=sum(r['shortest_strict_winning_strong_frontier_followup'] is not None for r in followups)))
            count+=1
        openings.append(dict(own_template=own_index,legal_scout_captures=entries))
    return dict(kind='proposal-only-opening-template-identification',strength_evidence=False,policy_implemented=False,
                public_openings=8,legal_scout_capture_options=count,
                experiment='Initial all-unknown enemy occupancy, eight fixed legitimate own armies; every enemy hypothesis comes from the unchanged .8/.2 public source prior.',
                flag_information='Exact Flag-rank joint under8 templates plus uniform legal background; bits and probability gain are diagnostics, not native bonuses.',
                followup_limits=['Followups use each disclosed template hypothesis, never opponent truth.','Miner route permits repeated strict-winning captures by one Miner, with all other units stationary; enemy replies can invalidate it.','Strong followup is a reachable strict-winning frontier capture, no other enemy transit; enemy replies are ignored.','These diagnostics cannot justify paying material or prove a forced route/win.'],
                front_origin_experiments=experiments,openings=openings,
                source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('tools/analyze_campaign_template_identification.py','tools/campaign_template_beliefs.py')})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise FileExistsError('Preserve previous proposal evidence')
    args.out.write_text(json.dumps(audit(),indent=2)+'\n')
