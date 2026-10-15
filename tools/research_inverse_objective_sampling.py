"""Check selected own-Flag features with actual finite-world samplers, development only."""
from collections import defaultdict
import copy
import gzip
import json
import math
from pathlib import Path
import random
import time

from ai_registry import ROOT
from belief_experiment import metric_summary
from calibrated_beliefs import BeliefModel
from campaign_inverse_objectives import ObjectiveBeliefs
from campaign_swap_beliefs import SwapBeliefs
from campaign_swap_diagnosis import probabilities
from information_strategy_cycle import digest
from research_inverse_objectives import enrich,game_metrics,contrast,DIRECTORY


def main():
    corpus=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    base_path=ROOT/'ai/models/public-history-beliefs-v1.json'
    candidates=json.loads((DIRECTORY/'model-candidates.json').read_text())
    chosen=candidates['flag'];assert chosen['factor_strength']>0
    assert chosen['base_model_sha256']==digest(base_path)
    mirrored=copy.deepcopy(candidates['mirrored-control'])
    mirrored['selected_features']=chosen['selected_features']
    mirrored['factor_strength']=chosen['factor_strength']
    data=enrich(corpus);calibration=[row for row in data if row['partition']=='calibration']
    metadata={row['game']:(row['pair'],row['family']) for row in calibration}
    baseline=BeliefModel(json.loads(base_path.read_text()))
    flag=ObjectiveBeliefs(chosen);sham=ObjectiveBeliefs(mirrored)
    raw=[]
    for group,model,context in [('base',baseline,None),('flag',flag,'objective_features'),('mirrored-flag',sham,'mirrored_features')]:
        for mode,samples in [('IS8',8),('swap4-8',8),('IS256',256)]:raw.append((group+'-'+mode,model,context,mode,samples))
    predictions={};metrics={};timing={};weight_ess={}
    started=time.perf_counter()
    with gzip.open(DIRECTORY/'sampling-predictions.jsonl.gz','wt') as output:
        for name,model,context,mode,samples in raw:
            sampler=SwapBeliefs(model,4) if mode=='swap4-8' else model
            records=[];elapsed=0.;ess=[]
            for row in calibration:
                if context is not None:model.context=row[context]
                seed=2175001+row['game']*1009+row['ply']*2+row['army']
                if samples==256:seed^=0x52454645
                before=time.perf_counter()
                draws=sampler.sample_worlds(list(bytes.fromhex(row['board'])),list(bytes.fromhex(row['lost'])),
                    row['histories'],random.Random(seed),row['army'],samples)
                elapsed+=time.perf_counter()-before
                total=sum(w for _,w in draws);ess.append(total*total/sum(w*w for _,w in draws))
                p=probabilities(row,draws);scoring=copy.copy(row);scoring['labels']=row['moved_labels'];records.append((scoring,p))
                output.write(json.dumps(dict(method=name,game=row['game'],pair=row['pair'],family=row['family'],
                    ply=row['ply'],army=row['army'],labels=row['moved_labels'],own_spy_unrevealed=row['own_spy_unrevealed'],
                    probabilities={sq:p[sq] for sq in row['moved_labels']}))+'\n')
            predictions[name]=game_metrics(records);metrics[name]=metric_summary(records)
            timing[name]=dict(seconds=elapsed,milliseconds_per_root=elapsed/len(calibration)*1000)
            weight_ess[name]=dict(mean=sum(ess)/len(ess),minimum=min(ess))
            print(name,metrics[name]['all'],timing[name],flush=True)
    comparisons={}
    for mode in ('IS8','swap4-8','IS256'):
        comparisons['flag minus base '+mode]=contrast(predictions['flag-'+mode],predictions['base-'+mode],metadata)
        comparisons['flag minus mirrored-flag '+mode]=contrast(predictions['flag-'+mode],predictions['mirrored-flag-'+mode],metadata)
    # Match the selected Flag-only group's feature set AND strength for an
    # objective-location control; no strength is reselected after sampling.
    exact_records={}
    for name,model,context in [('flag',flag,'objective_features'),('mirrored-flag',sham,'mirrored_features')]:
        records=[]
        for row in calibration:
            model.context=row[context]
            p=model.marginals(list(bytes.fromhex(row['board'])),list(bytes.fromhex(row['lost'])),row['histories'],row['army'])
            records.append((row,p))
        exact_records[name]=game_metrics(records)
    report=dict(scope='Historical calibration follow-up only; all strength/model/group choices fixed by previous development selection. No campaign/validation outcomes read.',
        candidate='Flag-only extra features; selected strength retained unchanged.',strength=chosen['factor_strength'],
        mirrored_control='Same selected Flag-only feature indices and identical selected strength; separately trained mirrored-file feature tables.',
        metrics=metrics,timing=timing,weight_ess=weight_ess,comparisons=comparisons,
        fixed_strength_fractional_flag_minus_mirrored=contrast(exact_records['flag'],exact_records['mirrored-flag'],metadata),
        calibration_games=len(metadata),eligible_games=len(predictions['base-IS8']),calibration_views=len(calibration),
        corpus_sha256=digest(corpus),base_model_sha256=digest(base_path),candidate_models_sha256=digest(DIRECTORY/'model-candidates.json'),
        module_sha256=digest(ROOT/'tools/campaign_inverse_objectives.py'),analysis_sha256=digest(Path(__file__)),
        seconds=time.perf_counter()-started,
        limitations='Selected on historical calibration; intervals descriptive, not unbiased validation. Eight-world estimates are sparse and use fixed5% inventory mixture for scoring. Swap chains finite-burn-in approximate; equal weights do not establish convergence. Correlated spatial features do not prove causal opponent planning.')
    (DIRECTORY/'sampling-followup.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
