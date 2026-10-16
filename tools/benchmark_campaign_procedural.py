"""Public-query parity/cost of structured/backrow priors; no matches or tuning."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import statistics
import sys
import time

from campaign_procedural_beliefs import ProceduralTemplateBeliefs
from feldmarschall import Engine,square_name
ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'docs/ai-honest-campaign-2026-10-15/research/procedural-background-v1'
OBSERVER=ROOT/'build/ai-catalog/student-template-flag-bomb-v1-normal/observer'
MODEL=ROOT/'ai/models/dos-procedural-background-v1.json'


def inputs(observer):
    army,board,lost,_=observer.ask('public','public').split();army=int(army);cells=list(bytes.fromhex(board))
    histories={sq:list(map(int,observer.ask('memory '+square_name(sq),'history').split()))
        for sq,c in enumerate(cells)if c<254 and bool(c&16)!=bool(army)and not c&32}
    return cells,army,list(bytes.fromhex(lost)),histories


def stats(values):return dict(samples=len(values),mean_ms=statistics.mean(values),median_ms=statistics.median(values),maximum_ms=max(values))


def benchmark():
    protocol=json.loads((RESEARCH/'protocol.json').read_text());rows=json.loads((RESEARCH/'heldout-public-prefixes.json').read_text())
    sys.path.insert(0,str(RESEARCH));from structural_model import StructuralModel
    from study import predict as research_predict
    fixed=json.loads(MODEL.read_text());kernel=StructuralModel(weights=[fixed['row_weights'][s//10]for s in range(40)])
    results={}
    for kind in('structured','backrow'):
        config=dict(fixed,background_kind=kind);cold=[];warm=[];posterior=[];query=[];checked=0
        for row in rows[::10]:
            observer=Engine(shlex.quote(str(OBSERVER)));model=ProceduralTemplateBeliefs(config)
            try:
                for event in(['new','red'],['rules','0'],['seed','39117'],['setup',protocol['own_formations'][row['formation']]]):
                    model.observe(event);observer.send(' '.join(event))
                for event in row['transcript']:model.observe(event);observer.send(' '.join(event))
                observer.ask('isready','readyok')
                begin=time.perf_counter_ns();public=inputs(observer);query.append((time.perf_counter_ns()-begin)/1e6)
                begin=time.perf_counter_ns();first,remaining=model.rank_marginals(*public);cold.append((time.perf_counter_ns()-begin)/1e6)
                begin=time.perf_counter_ns();weights,report=model.posterior();posterior.append((time.perf_counter_ns()-begin)/1e6)
                begin=time.perf_counter_ns();second,other=model.rank_marginals(*public);warm.append((time.perf_counter_ns()-begin)/1e6)
                assert(first,remaining)==(second,other)
                assert model.cache_misses==1 and model.cache_hits==2
                if kind=='structured':
                    expected=research_predict(row,kernel,fixed['epsilon'],with_bombs=True)
                    for a,b in zip(weights,expected['component_weights']):assert abs(a-b)<1e-12
                    for sq,probs in first.items():
                        origin=model.tokens[sq][1]
                        assert abs(probs[11]-expected['flag'][origin])<1e-10
                        assert abs(probs[10]-expected['bomb'][origin])<1e-10
                checked+=1
            finally:observer.close()
        results[kind]=dict(public_query_only=stats(query),rank_marginals_uncached=stats(cold),
            rank_marginals_cached=stats(warm),posterior_after_marginals_cached=stats(posterior),public_prefixes=checked,
            study_prediction_parity=kind=='structured')
    return dict(kind='native-procedural-prior-public-query-cost',games_played=0,source=RESEARCH.relative_to(ROOT).as_posix(),
        sample='Every10th heldout public prefix,64samples. Observer gets own setup/public events only; model never gets actual army, generation receipt or RNG. Prior posterior unchanged by caching.',
        results=results,limitations='Host timing only, no CX16 bank fit/cycle claim. IPC/public-memory reads measured separately; nativego not included.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in(Path(__file__),ROOT/'tools/campaign_procedural_beliefs.py',MODEL)},
        observer_sha256=hashlib.sha256(OBSERVER.read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise FileExistsError(args.out)
    args.out.parent.mkdir(parents=True,exist_ok=True);result=benchmark();args.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
