"""Development-only conditional objective features; retain all groups/controls."""
from collections import defaultdict
import copy
import gzip
import json
import math
from pathlib import Path
import time

from ai_registry import ROOT
from belief_experiment import rows,metric_summary
from campaign_inverse_objectives import ObjectiveMemory,ObjectiveBeliefs,FEATURE_SIZES,FEATURE_NAMES,SCHEMA
from information_strategy_cycle import bootstrap,digest
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

DIRECTORY=ROOT/'docs/ai-honest-campaign-2026-10-15/research/inverse-objectives'
GROUPS={'flag':(False,[0,1,2]),'spy':(False,[3,4]),'combined':(False,[0,1,2,3,4]),
        'motion':(False,[1,2,4]),'mirrored-control':(True,[0,1,2,3,4])}
STRENGTHS=(0.,.125,.25,.5,1.)


def enrich(corpus):
    grouped=defaultdict(dict)
    for row in rows(corpus):
        assert row['partition'] in ('train','calibration')
        grouped[row['game']][row['ply'],row['army']]=row
    result=[]
    with Tournament(corpus.with_name('development.fmtour')) as saved:
        for game_id,views in grouped.items():
            game=saved.game(game_id)
            assert 'msdos-1990-v2-normal' in (game['red'],game['blue'])
            army=1-int(game['blue']=='msdos-1990-v2-normal')
            memory=ObjectiveMemory();memory.observe(['new',('red','blue')[army]])
            memory.observe(['setup',game[('red_setup','blue_setup')[army]]])
            states,_=replay(game);events=public_events(game,states)
            for ply in range(max(p for p,a in views if a==army)+1):
                if (ply,army) in views:
                    row=copy.deepcopy(views[ply,army]);cells=list(bytes.fromhex(row['board']))
                    row['objective_features']={sq:memory.features(cells,army,sq,h) for sq,h in row['histories'].items()}
                    row['mirrored_features']={sq:memory.features(cells,army,sq,h,True) for sq,h in row['histories'].items()}
                    row['moved_labels']={sq:rank for sq,rank in row['labels'].items() if row['histories'][sq][5]}
                    assert all(rank<10 for rank in row['moved_labels'].values())
                    row['own_spy_unrevealed']=any(c<254 and bool(c&16)==bool(army) and c&15==9 and not c&32 for c in cells)
                    result.append(row)
                if ply<len(events):memory.observe(events[ply].split())
    return result


def fit(data,context):
    training=[row for row in data if row['partition']=='train'];views=defaultdict(int)
    for row in training:views[row['game']]+=1
    counts=[[[0.]*size for size in FEATURE_SIZES] for _ in range(10)];totals=[0.]*10
    for row in training:
        for square,rank in row['moved_labels'].items():
            weight=1/views[row['game']];totals[rank]+=weight
            for feature,value in enumerate(row[context][square]):counts[rank][feature][value]+=weight
    alpha=10.;tables=copy.deepcopy(counts)
    for feature,size in enumerate(FEATURE_SIZES):
        pooled=[sum(counts[rank][feature][v] for rank in range(10)) for v in range(size)]
        frequencies=[(v+1)/(sum(pooled)+size) for v in pooled]
        for rank in range(10):
            tables[rank][feature]=[math.log((counts[rank][feature][v]+alpha*frequencies[v])/
                (totals[rank]+alpha)/frequencies[v]) for v in range(size)]
    return tables


def game_metrics(records):
    values=defaultdict(list)
    for row,probabilities in records:
        for sq,rank in row['moved_labels'].items():
            p=probabilities[sq]
            values[row['game']].append((-math.log(max(1e-12,p[rank])),sum((v-int(r==rank))**2 for r,v in enumerate(p))))
    return {game:[sum(v[i] for v in vs)/len(vs) for i in range(2)] for game,vs in values.items()}


def contrast(first,second,metadata):
    pairs=defaultdict(list)
    for game in first.keys()&second.keys():
        pairs[metadata[game]].append([first[game][i]-second[game][i] for i in range(2)])
    return bootstrap([(family,dict(log_loss_delta=sum(v[0] for v in values)/len(values),
                                  brier_delta=sum(v[1] for v in values)/len(values)))
                      for (_,family),values in pairs.items()])


def main():
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    corpus=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    base_path=ROOT/'ai/models/public-history-beliefs-v1.json';base=json.loads(base_path.read_text())
    started=time.perf_counter();data=enrich(corpus)
    assert {r['pair'] for r in data if r['partition']=='train'}.isdisjoint({r['pair'] for r in data if r['partition']=='calibration'})
    calibration=[row for row in data if row['partition']=='calibration']
    tables={False:fit(data,'objective_features'),True:fit(data,'mirrored_features')}
    documents={};grid={};predictions={};runtimes={}
    with gzip.open(DIRECTORY/'calibration-predictions.jsonl.gz','wt') as output:
        for group,(mirrored,features) in GROUPS.items():
            document=dict(schema=SCHEMA,feature_sizes=list(FEATURE_SIZES),feature_names=list(FEATURE_NAMES),
                base_document=base,base_model_sha256=digest(base_path),factor_strength=0.,selected_features=features,
                extra_log_likelihood_ratios=tables[mirrored],mirrored_control=mirrored,extra_log_bound=.75,
                recipe='DOS-only training views; moved concealed enemy ranks only; game-view weights; categorical alpha10 smoothing. Frozen old weights unchanged.')
            documents[group]=document;grid[group]={};predictions[group]={};runtimes[group]={}
            for strength in STRENGTHS:
                document['factor_strength']=strength;model=ObjectiveBeliefs(document);records=[];seconds=0.
                for row in calibration:
                    model.context=row['mirrored_features' if mirrored else 'objective_features']
                    before=time.perf_counter()
                    p=model.marginals(list(bytes.fromhex(row['board'])),list(bytes.fromhex(row['lost'])),row['histories'],row['army'])
                    seconds+=time.perf_counter()-before
                    scoring=copy.copy(row);scoring['labels']=row['moved_labels'];records.append((scoring,p))
                    output.write(json.dumps(dict(group=group,strength=strength,game=row['game'],pair=row['pair'],
                        family=row['family'],ply=row['ply'],army=row['army'],labels=row['moved_labels'],
                        probabilities={sq:p[sq] for sq in row['moved_labels']}))+'\n')
                metrics=metric_summary(records);grid[group][str(strength)]=metrics
                predictions[group][strength]=game_metrics(records);runtimes[group][str(strength)]=seconds
                print(group,strength,metrics['all'],flush=True)
            selected=min(STRENGTHS,key=lambda t:(grid[group][str(t)]['all']['log_loss'],t))
            documents[group]['factor_strength']=selected
    metadata={r['game']:(r['pair'],r['family']) for r in calibration}
    baseline=predictions['flag'][0.]
    comparisons={group:contrast(predictions[group][doc['factor_strength']],baseline,metadata) for group,doc in documents.items()}
    best=min(GROUPS,key=lambda g:(grid[g][str(documents[g]['factor_strength'])]['all']['log_loss'],g))
    report=dict(scope='Historical development selection, not fresh validation. Only public own-setup/event features; DOS-specific views, no campaign cohorts or outcomes used.',
        interpretation='Conditional spatial/motion likelihood factors inspired by inverse planning; not a causal test or full inverse planning implementation.',
        train_views=sum(r['partition']=='train' for r in data),calibration_views=len(calibration),
        train_moved_labels=sum(len(r['moved_labels']) for r in data if r['partition']=='train'),
        calibration_moved_labels=sum(len(r['moved_labels']) for r in calibration),grid=grid,
        selected_strengths={g:d['factor_strength'] for g,d in documents.items()},best_group=best,
        selected_vs_frozen_base=comparisons,runtimes_seconds=runtimes,
        real_combined_minus_mirrored=contrast(predictions['combined'][documents['combined']['factor_strength']],
            predictions['mirrored-control'][documents['mirrored-control']['factor_strength']],metadata),
        calibration_rule='Minimum game-weighted moved-rank logloss within each fixed strength grid0,.125,.25,.5,1; zero retains exact frozen base. Report every group/control; exploratory intervals after selection.',
        limitations='Count-balanced fractional marginals are approximate. Grid selected and compared on same historical calibration cohort, so intervals are descriptive and optimistic. Actual eight-world sampling and fresh strength remain untested.',
        base_model_sha256=digest(base_path),corpus_sha256=digest(corpus),module_sha256=digest(ROOT/'tools/campaign_inverse_objectives.py'),
        analysis_sha256=digest(Path(__file__)),seconds=time.perf_counter()-started,
        primary_sources=['https://dspace.mit.edu/entities/publication/2e23673d-f720-4720-98bc-6db894ba27e1','https://project.dke.maastrichtuniversity.nl/games/files/bsc/OMStratego.pdf'])
    (DIRECTORY/'model-candidates.json').write_text(json.dumps(documents,indent=2)+'\n')
    (DIRECTORY/'development-selection.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
