"""Public-only marginal mixing check from two dispersed chain initializers."""
from collections import defaultdict
import json
from pathlib import Path
import random
import time

from ai_registry import ROOT
from belief_experiment import rows
from calibrated_beliefs import BeliefModel
from campaign_swap_beliefs import rejuvenate
from information_strategy_cycle import digest
from train_ai_student import sample_world


def marginals(draws,slots):
    total=sum(w for _,w in draws);result={sq:[0.]*12 for sq in slots}
    for world,weight in draws:
        for sq in slots:result[sq][world[sq]&15]+=weight/total
    return result


def audit():
    corpus=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    model_path=ROOT/'ai/models/public-history-beliefs-v1.json';model=BeliefModel.load(model_path)
    grouped=defaultdict(list)
    for row in rows(corpus):
        assert row['partition'] in ('train','calibration')
        if row['partition']=='calibration':grouped[row['game'],row['army']].append(row)
    selected={}
    for (game,army),views in sorted(grouped.items()):
        views.sort(key=lambda row:row['ply'])
        row=views[len(views)//3]
        selected.setdefault((row['family'],army),row)
    reports=[];start=time.perf_counter();chains=256
    for key,row in sorted(selected.items()):
        cells=list(bytes.fromhex(row['board']));lost=list(bytes.fromhex(row['lost']));histories=row['histories']
        slots,counts,likelihoods=model.prepare(cells,lost,histories,row['army'])
        reference_draws=model.sample_worlds(cells,lost,histories,random.Random(2145001+row['game']*101+row['army']),row['army'],4096)
        reference=marginals(reference_draws,slots)
        ess=sum(w for _,w in reference_draws)**2/sum(w*w for _,w in reference_draws)
        expected_noise=sum(sum(p*(1-p) for p in ps) for ps in reference.values())/len(slots)*(1/chains+1/ess)
        result={}
        for initializer in ('learned-proposal','uniform-counts'):
            for sweeps in (0,1,4,16,64):
                seedrng=random.Random(2146001+row['game']*101+row['army']);draws=[]
                for _ in range(chains):
                    rng=random.Random(seedrng.getrandbits(64))
                    if initializer=='learned-proposal':world,_=model.draw(cells,histories,rng,slots,counts,likelihoods)
                    else:world,_=sample_world(cells,lost,histories,rng,row['army'])
                    rejuvenate(world,slots,histories,likelihoods,rng,sweeps*len(slots))
                    draws.append((world,1.))
                actual=marginals(draws,slots)
                mse=sum(sum((p-reference[sq][r])**2 for r,p in enumerate(ps)) for sq,ps in actual.items())/len(slots)
                result[initializer+'-'+str(sweeps)]=dict(squared_error=mse,ratio_to_approximate_sampling_noise=mse/expected_noise)
        reports.append(dict(family=key[0],army=key[1],game=row['game'],ply=row['ply'],unknowns=len(slots),
                            reference_ess=ess,approximate_sampling_noise=expected_noise,results=result))
        print(key,'complete',flush=True)
    keys=list(reports[0]['results'])
    summary={key:dict(mean_squared_error=sum(r['results'][key]['squared_error'] for r in reports)/len(reports),
                     mean_ratio_to_sampling_noise=sum(r['results'][key]['ratio_to_approximate_sampling_noise'] for r in reports)/len(reports))
             for key in keys}
    return dict(scope='Fourteen fixed historical calibration public views: one per family and observer side, first game and one-third snapshot. No rank labels or wins enter this mixing audit.',
        chains=chains,reference='4096 independent learned importance proposals, separate RNG domain.',roots=reports,summary=summary,
        seconds=time.perf_counter()-start,corpus_sha256=digest(corpus),model_sha256=digest(model_path),
        sampler_sha256=digest(ROOT/'tools/campaign_swap_beliefs.py'),analysis_sha256=digest(Path(__file__)),
        limitation='Marginal agreement from two initializers is evidence, not a convergence proof for the full joint posterior. Reference has Monte Carlo error. Noise ratios use multinomial endpoint and weighted-reference ESS approximations.')


if __name__=='__main__':
    report=audit()
    out=ROOT/'docs/ai-honest-campaign-2026-10-15/research/swap-marginal-mixing.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2))
