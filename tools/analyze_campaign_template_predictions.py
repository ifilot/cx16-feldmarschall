"""Fixed-prior predictive audit on fresh original DOS Colonel deployments.

Synthetic random non-Flag disclosures are NOT legal game prefixes. The predictor
receives only original-origin/rank disclosures. Full armies and private original
RNG states remain exclusively in this offline generation/scoring harness.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import secrets
import sqlite3
import subprocess
import time

from campaign_dos_deployment import EXPECTED,SOURCE_COMMIT,generate_setup
from campaign_template_beliefs import TemplateMixtureBeliefs,TEMPLATES
from feldmarschall import COUNTS,GLYPHS,setup_squares

ROOT=Path(__file__).resolve().parents[1]
DISCLOSURES=(0,1,3,5,10)


def predict_public(disclosures):
    """Predict without access to actual army, original RNG state or branch."""
    model=TemplateMixtureBeliefs();model.observe(['new','red'])
    own=''.join(g*n for g,n in zip(GLYPHS,COUNTS));model.observe(['setup',own])
    # Explicit synthetic public rank constraints, not a fabricated game trace.
    model.known.update({(1,origin):rank for origin,rank in disclosures})
    cells=[255]*100;histories={}
    for sq,(owner,origin) in model.tokens.items():
        rank=model.known.get((owner,origin));cells[sq]=owner*16|(rank if rank is not None else 12)|(32 if owner and rank is not None else 0)
        if owner and rank is None:
            h=[0]*11;h[2]=setup_squares(1)[origin];h[-1]=4095;histories[sq]=h
    start=time.perf_counter();marginals,remaining=model.rank_marginals(cells,0,[0]*12,histories)
    seconds=time.perf_counter()-start
    posterior,report=model.posterior();flag=[];bomb=[];uniform_flag=[];uniform_bomb=[]
    disclosed=dict(disclosures);unknown=40-len(disclosed)
    for origin,sq in enumerate(setup_squares(1)):
        if origin in disclosed:
            f=float(disclosed[origin]==11);b=float(disclosed[origin]==10)
            flag.append(f);bomb.append(b);uniform_flag.append(f);uniform_bomb.append(b)
        else:
            flag.append(marginals[sq][11]);bomb.append(marginals[sq][10])
            uniform_flag.append(remaining[11]/unknown);uniform_bomb.append(remaining[10]/unknown)
    return dict(template=dict(flag=flag,bomb=bomb),uniform=dict(flag=uniform_flag,bomb=uniform_bomb),
                component_posterior=posterior,posterior_report=report,marginal_seconds=seconds)


def scores(prediction,truth):
    flag=truth.index(11);p=prediction['flag'];b=prediction['bomb'];epsilon=1e-300
    chosen=max(range(40),key=lambda o:(p[o],-o));maximum=max(p)
    ties=[o for o in range(40) if abs(p[o]-maximum)<1e-14]
    bomb_logloss=-sum(math.log(max(epsilon,b[o] if truth[o]==10 else 1-b[o])) for o in range(40))/40
    return dict(flag_logloss=-math.log(max(epsilon,p[flag])),
                flag_brier=sum((q-float(o==flag))**2 for o,q in enumerate(p)),
                flag_top_accuracy=float(chosen==flag),flag_top_tie_adjusted_accuracy=(1/len(ties) if flag in ties else 0.),
                bomb_logloss_per_original_slot=bomb_logloss,
                bomb_brier_per_original_slot=sum((q-float(truth[o]==10))**2 for o,q in enumerate(b))/40,
                true_flag_probability=p[flag],top_flag_probability=maximum)


def saved_seeds():
    files=subprocess.run(['rg','--files','-g','*.fmtour'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.splitlines()
    excluded=set()
    for name in files:
        connection=sqlite3.connect((ROOT/name).resolve().as_uri()+'?mode=ro',uri=True)
        try:excluded.update(row[0] for row in connection.execute('SELECT DISTINCT seed FROM games'))
        finally:connection.close()
    return excluded,len(files)


def audit(count=256):
    excluded,files=saved_seeds();seeds=[]
    while len(seeds)<count:
        seed=secrets.randbits(32)
        if seed not in excluded and seed not in seeds:seeds.append(seed)
    sources=ROOT/'ai/msdos1990';assets=ROOT/'docs/ai-honest-campaign-2026-10-15/research/dos-deployment-original-v1'
    disclosure_rng=random.Random(0x51990c011e);rows=[];generation_seconds=[];branches=Counter()
    for index,seed in enumerate(seeds):
        start=time.perf_counter();army,receipt=generate_setup(sources,seed,level=3,setup_assets=assets)
        generation_seconds.append(time.perf_counter()-start);truth=[GLYPHS.index(g) for g in army]
        branch=receipt['branch'];branches[branch]+=1
        candidates=[o for o,r in enumerate(truth) if r!=11];disclosure_rng.shuffle(candidates)
        for K in DISCLOSURES:
            disclosed=[(o,truth[o]) for o in candidates[:K]]
            result=predict_public(disclosed);posterior=result['component_posterior'];compatible=[i for i,p in enumerate(posterior[:-1]) if p]
            mass_correct_flag=sum(posterior[i] for i in compatible if TEMPLATES[i].index('F')==truth.index(11))
            mass_wrong_flag=sum(posterior[:-1])-mass_correct_flag
            rows.append(dict(army_index=index,branch=branch,disclosures=K,public_disclosures=disclosed,
                             template=scores(result['template'],truth),uniform=scores(result['uniform'],truth),
                             posterior=result['posterior_report'],
                             background_only=not compatible,
                             template_dominant_wrong_flag=mass_wrong_flag>.5,
                             wrong_flag_template_mass=mass_wrong_flag,
                             marginal_seconds=result['marginal_seconds']))
    grouped=defaultdict(list)
    for row in rows:
        grouped['all',row['disclosures']].append(row);grouped[row['branch'],row['disclosures']].append(row)
    aggregates=[]
    for (branch,K),group in sorted(grouped.items()):
        metrics={name:{key:sum(row[name][key] for row in group)/len(group) for key in group[0][name]} for name in ('template','uniform')}
        delta={key:metrics['template'][key]-metrics['uniform'][key] for key in metrics['template']}
        aggregates.append(dict(branch=branch,disclosures=K,armies=len(group),metrics=metrics,template_minus_uniform=delta,
                               background_only_rate=sum(r['background_only'] for r in group)/len(group),
                               template_dominant_wrong_flag_rate=sum(r['template_dominant_wrong_flag'] for r in group)/len(group),
                               mean_template_mass=sum(1-r['posterior']['background_probability'] for r in group)/len(group)))
    timing=[r['marginal_seconds'] for r in rows]
    return dict(kind='fixed-template-prior-predictive-audit-original-colonel',strength_evidence=False,model_tuned=False,
                original_source_commit=SOURCE_COMMIT,original_assets_sha256=EXPECTED,armies=count,branches=dict(branches),
                excluded_saved_tournament_files=files,excluded_saved_seed_count=len(excluded),private_research_seeds=seeds,
                seed_contract='Fresh secrets.randbits(32), explicitly excluded from every currently saved fmtour game seed. Private seed used only by offline original generator; predictor receives disclosure tuples only.',
                synthetic_observation_protocol='Per army choose one random permutation of39 non-Flag origins and reveal nested prefixes0/1/3/5/10; observations are rank constraints, NOT legal game prefixes. Full army is used only by generation/scoring harness.',
                metrics='Natural-log Flag categorical loss and summed categorical Brier; Bomb Bernoulli logloss/Brier mean over40 original slots. Known disclosed ranks have deterministic correct predictions. Top Flag ties choose lowest original index; tie-adjusted accuracy also reported.',
                calibration_warning='Original procedural20% is Flag-screened and nonuniform; our fixed20% uniform legal-army background is deliberately misspecified. Posterior omits action-choice likelihood. These predictive scores establish neither move strength nor causal game value.',
                timings=dict(generator_total_seconds=sum(generation_seconds),generator_mean_seconds=sum(generation_seconds)/count,
                             marginal_mean_seconds=sum(timing)/len(timing),marginal_max_seconds=max(timing),
                             warning='Offline Python timings exclude observer IPC, packet rounding and native evaluation; not realtime performance.'),
                aggregates=aggregates,rows=rows,
                source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                               ('tools/analyze_campaign_template_predictions.py','tools/campaign_template_beliefs.py','tools/campaign_dos_deployment.py')})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--armies',type=int,choices=(128,256),default=256)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise FileExistsError('Preserve the previous evidence; choose a new output path')
    args.out.write_text(json.dumps(audit(args.armies),indent=2)+'\n')
