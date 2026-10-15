"""Measure complete original-AI matches, exact acceleration parity and OpenMP throughput."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import platform
import time

from ai_registry import ROOT,get_policy
from tournament import run,FAMILIES
from tournament_store import Tournament,verify


def benchmark(out,rounds=1,max_plies=1000,workers=4,seed=1911001):
    out.mkdir(parents=True,exist_ok=False)
    records={};games={}
    stages=[('counted','msdos-1990-v1-normal','openmp',1),
            ('fast-serial','msdos-1990-v2-normal','openmp',1),
            ('fast-parallel','msdos-1990-v2-normal','openmp',workers),
            ('fast-python','msdos-1990-v2-normal','python',workers)]
    for label,identity,backend,jobs in stages:
        path=out/(label+'.fmtour');started=time.perf_counter()
        with (out/(label+'.log')).open('x') as log,contextlib.redirect_stdout(log):
            run(identity,'student-guard-v1-normal',path,rounds=rounds,seed=seed,jobs=jobs,
                families=FAMILIES,max_plies=max_plies,backend=backend)
        seconds=time.perf_counter()-started
        summary=verify(path)
        with Tournament(path) as tournament:
            rows=[tournament.game(r['id']) for r in tournament.games()]
            metadata=tournament.metadata()
        games[label]=rows
        total=sum(r['plies'] for r in rows)
        execution=metadata['execution_seconds']
        records[label]=dict(policy=get_policy(identity),backend=backend,workers=jobs,
            reuse_engine_processes=metadata.get('reuse_engine_processes',False),
            seconds=seconds,games=len(rows),plies=total,games_per_minute=60*len(rows)/seconds,
            execution_seconds=execution,execution_games_per_minute=60*len(rows)/execution,
            execution_plies_per_second=total/execution,
            plies_per_second=total/seconds,summary=summary,parallel_execution=metadata.get('parallel_execution'),
            fmtour_bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        print(label,json.dumps({k:v for k,v in records[label].items() if k not in ('policy','summary')}),flush=True)
    reference=games['counted']
    for label,rows in games.items():
        assert len(rows)==len(reference)
        for a,b in zip(reference,rows):
            assert all(a[k]==b[k] for k in ('id','seed','pair_id','family','red_setup','blue_setup','moves','result','reason','plies')),(label,a['id'])
    report=dict(schema=1,platform=platform.platform(),processor=platform.processor(),seed=seed,rounds=rounds,max_plies=max_plies,families=list(FAMILIES),measurements=records,
        counted_to_fast_serial_speedup=records['counted']['seconds']/records['fast-serial']['seconds'],
        openmp_speedup=records['fast-serial']['seconds']/records['fast-parallel']['seconds'],
        all_complete_traces_identical=True,verified_games=sum(v['games'] for v in records.values()),
        verified_plies=sum(v['plies'] for v in records.values()),
        timing_scope='End-to-end including runtime/source hashes, compression and SQLite writes. Same legal complete paired games, side-swapped on all seven families. Warm host/build cache. No DOSBox/UI timing comparison or hardware-independent performance guarantee.',
        fidelity_scope='Fast and instruction-counted execution of identical original AI images. Exact match parity does not establish equivalence to every complete original DOS UI/game-loop path.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--rounds',type=int,default=1)
    parser.add_argument('--max-plies',type=int,default=1000)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--seed',type=int,default=1911001)
    args=parser.parse_args();benchmark(args.out.resolve(),args.rounds,args.max_plies,args.workers,args.seed)
