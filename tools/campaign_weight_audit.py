"""Fixed, development-only paired audit of existing behavioral world weights."""
from collections import defaultdict
import json
import math
from pathlib import Path
import random

from ai_registry import ROOT
from belief_experiment import rows
from feldmarschall import COUNTS
from information_strategy_cycle import bootstrap,digest
from train_ai_student import sample_world
from tournament_store import Tournament,replay


def revelations(game):
    states,_=replay(game)
    identities={sq:(cell[0],sq) for sq,cell in enumerate(states[0]) if cell is not None}
    first={}
    for ply,(src,dst) in enumerate(game['moves']):
        actor,target=identities[src],identities.get(dst)
        if target is not None:
            first.setdefault(actor,ply+1);first.setdefault(target,ply+1)
        elif abs(src//10-dst//10)+abs(src%10-dst%10)>1:
            first.setdefault(actor,ply+1)
        identities.pop(src)
        if states[ply+1][dst] is None:identities.pop(dst,None)
        elif states[ply+1][dst][0]==actor[0]:identities[dst]=actor
    return first


def audit(destination,samples=256):
    corpus=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    tournament=corpus.with_name('development.fmtour')
    grouped=defaultdict(list)
    for row in rows(corpus):
        assert row['partition'] in ('train','calibration'), 'development only'
        grouped[row['game'],row['army']].append(row)
    selected=[]
    for key,views in sorted(grouped.items()):
        own=sorted(views,key=lambda row:row['ply'])
        selected.extend(own[i] for i in sorted({len(own)//3,2*len(own)//3}))
    with Tournament(tournament) as saved:
        revealed={game:revelations(saved.game(game)) for game in {r['game'] for r in selected}}
    bygame=defaultdict(lambda:defaultdict(list));metadata={};effective=[];observations=defaultdict(int)
    masks=defaultdict(int)
    for row in selected:
        cells=list(bytes.fromhex(row['board']));lost=list(bytes.fromhex(row['lost']))
        rng=random.Random(2105001+row['game']*1009+row['ply']*2+row['army'])
        draws=[sample_world(cells,lost,row['histories'],rng,row['army']) for _ in range(samples)]
        total=sum(w for _,w in draws);effective.append(total**2/sum(w*w for _,w in draws))
        remaining=[n-lost[r] for r,n in enumerate(COUNTS)]
        for cell in cells:
            if cell<254 and bool(cell&16)!=bool(row['army']) and cell&32:remaining[cell&15]-=1
        counts=[[0.]*12 for _ in range(100)];weighted=[[0.]*12 for _ in range(100)]
        for world,weight in draws:
            for sq in row['histories']:
                rank=world[sq]&15;counts[sq][rank]+=1;weighted[sq][rank]+=weight
        metadata[row['game']]=(row['pair'],row['family'])
        for sq,rank in row['labels'].items():
            h=row['histories'][sq];masks[h[-1]]+=1
            # Fixed same 5% smoothed convention as the earlier belief audit.
            prior=[remaining[r] if h[-1]&(1<<r) else 0 for r in range(12)]
            mass=sum(prior)
            uniform=[.95*n/samples+.05*prior[r]/mass for r,n in enumerate(counts[sq])]
            behavior=[.95*n/total+.05*prior[r]/mass for r,n in enumerate(weighted[sq])]
            groups=['all']
            if h[8]<12 or h[9]<12:groups.append('behavior_evidence')
            if revealed[row['game']].get((1-row['army'],h[2]),-1)>row['ply']:groups.append('later_publicly_revealed')
            for group in groups:
                observations[group]+=1
                bygame[row['game']][group].append((
                    -math.log(uniform[rank]),-math.log(behavior[rank]),
                    sum((v-int(r==rank))**2 for r,v in enumerate(uniform)),
                    sum((v-int(r==rank))**2 for r,v in enumerate(behavior))))
    report={}
    for group in observations:
        pairrows=defaultdict(list);means=[]
        for game,groups in bygame.items():
            if group not in groups:continue
            mean=[sum(row[k] for row in groups[group])/len(groups[group]) for k in range(4)]
            means.append(mean);pair,family=metadata[game]
            pairrows[pair,family].append(mean)
        blocks=[(family,dict(log_loss_delta=sum(r[1]-r[0] for r in rs)/len(rs),
                             brier_delta=sum(r[3]-r[2] for r in rs)/len(rs)))
                for (_,family),rs in pairrows.items()]
        report[group]=dict(piece_observations=observations[group],games=len(means),
             uniform_log_loss=sum(r[0] for r in means)/len(means),
             behavioral_log_loss=sum(r[1] for r in means)/len(means),
             uniform_brier=sum(r[2] for r in means)/len(means),
             behavioral_brier=sum(r[3] for r in means)/len(means),
             paired=bootstrap(blocks))
    result=dict(scope='Historical development only; no campaign or validation cohorts inspected.',
        hypothesis='Ablate uncalibrated approach/retreat weights; same IID worlds, no tuning.',
        samples=samples,snapshots=len(selected),seed=2105001,
        corpus_sha256=digest(corpus),tournament_sha256=digest(tournament),
        analysis_sha256=digest(Path(__file__)),mask_observations=dict(masks),
        effective_samples=dict(mean=sum(effective)/len(effective),minimum=min(effective)),
        results=report,interpretation='Negative behavioral-minus-uniform deltas favor existing weights. '
        'Rank calibration is not playing strength. Later-revealed subset has disclosure selection bias. '
        'Intervals cluster both game orientations by setup pair, stratified by family; unequal subset game availability is retained.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    out=ROOT/'docs/ai-honest-campaign-2026-10-15/research/behavioral-weight-audit.json'
    print(json.dumps(audit(out),indent=2))
