"""Fixed-budget swap-chain diagnosis on historical calibration public views."""
from collections import defaultdict
import json
import math
from pathlib import Path
import random
import time

from ai_registry import ROOT
from belief_experiment import rows,metric_summary
from calibrated_beliefs import BeliefModel
from campaign_swap_beliefs import SwapBeliefs
from information_strategy_cycle import bootstrap,digest

SWEEPS=(0,1,4,16,64)
SEED=2125001


def probabilities(row,draws):
    cells=list(bytes.fromhex(row['board']));lost=list(bytes.fromhex(row['lost']))
    from calibrated_beliefs import unknowns
    slots,remaining=unknowns(cells,lost,row['histories'],row['army'])
    counts={sq:[0.]*12 for sq in slots};total=sum(w for _,w in draws)
    for world,weight in draws:
        for sq in slots:counts[sq][world[sq]&15]+=weight
    result={}
    for sq in slots:
        prior=[n if row['histories'][sq][-1]&(1<<rank) else 0 for rank,n in enumerate(remaining)]
        mass=sum(prior)
        result[sq]=[.95*v/total+.05*prior[rank]/mass for rank,v in enumerate(counts[sq])]
    return result


def audit():
    corpus=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    model_path=ROOT/'ai/models/public-history-beliefs-v1.json'
    model=BeliefModel.load(model_path);grouped=defaultdict(list)
    for row in rows(corpus):
        assert row['partition'] in ('train','calibration')
        if row['partition']=='calibration':grouped[row['game'],row['army']].append(row)
    selected=[]
    for views in grouped.values():
        views.sort(key=lambda row:row['ply'])
        selected.extend(views[i] for i in sorted({len(views)//3,2*len(views)//3}))
    methods=[('learned-is-8',8,None),('learned-is-256',256,None)]+[(f'swap-{sweeps}-8',8,sweeps) for sweeps in SWEEPS]
    predictions={};summaries={};timing={};weight_ess={};acceptance={};metadata={}
    for label,samples,sweeps in methods:
        records=[];elapsed=0.;ess=[];accepted=attempted=0
        sampler=model if sweeps is None else SwapBeliefs(model,sweeps)
        for row in selected:
            seed=SEED+row['game']*1009+row['ply']*2+row['army']
            if samples==256:seed^=0x52454645 # independent reference RNG domain
            before=time.perf_counter()
            draws=sampler.sample_worlds(list(bytes.fromhex(row['board'])),list(bytes.fromhex(row['lost'])),
                row['histories'],random.Random(seed),row['army'],samples)
            elapsed+=time.perf_counter()-before
            total=sum(w for _,w in draws);ess.append(total**2/sum(w*w for _,w in draws))
            if sweeps is not None:
                accepted+=sampler.last_report['accepted_rank_changes'];attempted+=sampler.last_report['attempted_swaps']
            records.append((row,probabilities(row,draws)));metadata[row['game']]=(row['pair'],row['family'])
        predictions[label]=records;summaries[label]=metric_summary(records)
        timing[label]=dict(seconds=elapsed,mean_milliseconds_per_root=1000*elapsed/len(selected))
        weight_ess[label]=dict(mean=sum(ess)/len(ess),minimum=min(ess),
            warning='Equal MCMC weights do not establish convergence or statistical effective sample size.' if sweeps is not None else '')
        if attempted:acceptance[label]=dict(attempted=attempted,accepted=accepted,fraction=accepted/attempted)
        print(label,summaries[label]['all'],timing[label],flush=True)
    pergame={};reference=predictions['learned-is-256'];reference_mse={}
    for label,records in predictions.items():
        bygame=defaultdict(list);errors=[]
        for (row,probs),(refrow,ref) in zip(records,reference):
            assert (row['game'],row['ply'],row['army'])==(refrow['game'],refrow['ply'],refrow['army'])
            values=[]
            for sq,rank in row['labels'].items():
                values.append((-math.log(probs[sq][rank]),sum((v-int(r==rank))**2 for r,v in enumerate(probs[sq]))))
                errors.append(sum((v-ref[sq][r])**2 for r,v in enumerate(probs[sq])))
            bygame[row['game']].extend(values)
        pergame[label]={game:[sum(v[k] for v in values)/len(values) for k in range(2)] for game,values in bygame.items()}
        reference_mse[label]=sum(errors)/len(errors)
    contrasts={}
    baseline=pergame['learned-is-8']
    for label in pergame:
        if label=='learned-is-8':continue
        pairs=defaultdict(list)
        for game,values in pergame[label].items():
            pairs[metadata[game]].append([values[k]-baseline[game][k] for k in range(2)])
        blocks=[(family,dict(log_loss_delta=sum(v[0] for v in values)/len(values),
                            brier_delta=sum(v[1] for v in values)/len(values)))
                for (_,family),values in pairs.items()]
        contrasts[label+' minus learned-is-8']=bootstrap(blocks)
    # Fixed before observing the grid: choose cheapest burn-in within0.01nats
    # of best positive-budget calibration log loss. No strength scores enter.
    best=min(summaries[f'swap-{s}-8']['all']['log_loss'] for s in SWEEPS if s>0)
    chosen=next(s for s in SWEEPS if s>0 and summaries[f'swap-{s}-8']['all']['log_loss']<=best+.01)
    return dict(scope='Historical calibration public views only. No campaign or validation cohort read; frozen learned model never refitted.',
        mechanism='Independent chains; count-preserving symmetric lazy swaps; product-likelihood target invariant but finite burn-in approximate.',
        snapshots=len(selected),games=len(metadata),seed=SEED,sweeps_grid=list(SWEEPS),
        selection_rule='Smallest positive sweep count within0.01nats of the best calibration all-rank logloss; no wins used.',
        selected_sweeps=chosen,metrics=summaries,timing=timing,weight_ess=weight_ess,
        proposal_acceptance=acceptance,probability_squared_error_to_256_reference=reference_mse,
        comparisons=contrasts,model_sha256=digest(model_path),corpus_sha256=digest(corpus),
        sampler_sha256=digest(ROOT/'tools/campaign_swap_beliefs.py'),analysis_sha256=digest(Path(__file__)),
        limitations='The256sample IS reference has Monte Carlo noise and finite-sample bias. Independent chain endpoints can remain biased before mixing. Calibration grid selection is exploratory; only fresh strength tests can establish gains.',
        primary_sources=['https://www.osti.gov/biblio/4390578','https://academic.oup.com/jrsssb/article-abstract/63/1/127/7083331'])


if __name__=='__main__':
    report=audit()
    path=ROOT/'docs/ai-honest-campaign-2026-10-15/research/swap-belief-diagnosis.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    print('Selected',report['selected_sweeps'],'sweeps',flush=True)
