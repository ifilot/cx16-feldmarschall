"""Replay all historical development histories through the honest joint sampler."""
from collections import defaultdict
import json
from pathlib import Path
import random
import time

from ai_registry import ROOT
from belief_experiment import rows
from campaign_joint_beliefs import JointSetupBeliefs
from information_strategy_cycle import digest
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


def audit():
    corpus=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    bygame=defaultdict(dict)
    for row in rows(corpus):
        assert row['partition'] in ('train','calibration')
        bygame[row['game']][row['ply'],row['army']]=row
    count=0;events_seen=0;start=time.perf_counter();sampling_seconds=0.
    with Tournament(corpus.with_name('development.fmtour')) as saved:
        for gid,views in bygame.items():
            game=saved.game(gid);states,_=replay(game);events=public_events(game,states)
            models=[JointSetupBeliefs.load(ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json') for _ in (0,1)]
            for side,model in enumerate(models):
                model.observe(['new',('red','blue')[side]])
                model.observe(['setup',game[('red_setup','blue_setup')[side]]])
            for ply in range(len(events)+1):
                for side,model in enumerate(models):
                    if (ply,side) in views:
                        row=views[ply,side];before=time.perf_counter()
                        model.sample_worlds(list(bytes.fromhex(row['board'])),list(bytes.fromhex(row['lost'])),
                            row['histories'],random.Random(999+gid+ply),side,8)
                        sampling_seconds+=time.perf_counter()-before;count+=1
                if ply<len(events):
                    for model in models:model.observe(events[ply].split());events_seen+=1
    return dict(development_only=True,games=len(bygame),public_events_checked=events_seen,
        sampled_roots=count,samples=8,sampling_seconds=sampling_seconds,
        mean_milliseconds_per_root=1000*sampling_seconds/count,total_seconds=time.perf_counter()-start,
        audit_sha256=digest(Path(__file__)),source_sha256=digest(ROOT/'tools/campaign_joint_beliefs.py'),
        model_sha256=digest(ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json'),corpus_sha256=digest(corpus))


if __name__=='__main__':
    result=audit()
    out=ROOT/'docs/ai-honest-campaign-2026-10-15/research/joint-public-prefix-audit.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
