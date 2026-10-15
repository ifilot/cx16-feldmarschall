"""Compare exact frozen joint and identical-prior control on development only."""
from collections import defaultdict
import json
from pathlib import Path

from ai_registry import ROOT
from belief_experiment import rows
from campaign_joint_research import bomb_reveals,predict,local
from information_strategy_cycle import bootstrap,digest
from tournament_store import Tournament
import math


def audit():
    corpus=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    paths=[ROOT/'ai/models'/name for name in ('joint-flag-bomb-beliefs-v1.json','flag-row-prior-control-v1.json')]
    joint,control=[json.loads(path.read_text()) for path in paths]
    assert joint['weights']==control['weights'] and joint['phi']==control['phi']
    assert control['theta']==[0.,0.]
    grouped=defaultdict(list)
    for row in rows(corpus):
        assert row['partition'] in ('train','calibration')
        if row['partition']=='calibration':grouped[row['game'],row['army']].append(row)
    selected=[]
    for views in grouped.values():
        views.sort(key=lambda row:row['ply'])
        selected.extend(views[i] for i in sorted({len(views)//3,2*len(views)//3}))
    with Tournament(corpus.with_name('development.fmtour')) as saved:
        revealed={game:bomb_reveals(saved.game(game)) for game in {r['game'] for r in selected}}
    values=defaultdict(list);metadata={};byclue=defaultdict(list)
    for row in selected:
        flags=[sq for sq,rank in row['labels'].items() if rank==11]
        if not flags:continue
        flag=local(row['histories'][flags[0]][2],1-row['army'])
        old=predict(row,control,revealed[row['game']],False)
        new=predict(row,joint,revealed[row['game']],False)
        metrics=(-math.log(old[flag]),-math.log(new[flag]),max(old,key=old.get)==flag,max(new,key=new.get)==flag)
        values[row['game']].append(metrics);metadata[row['game']]=(row['pair'],row['family'])
        clue=any(ply<=row['ply'] and owner!=row['army'] for ply,(owner,_) in revealed[row['game']])
        byclue['public_bomb' if clue else 'no_public_bomb'].append(metrics)
    pairs=defaultdict(list)
    for game,observations in values.items():
        pairs[metadata[game]].append([sum(m[k] for m in observations)/len(observations) for k in range(4)])
    blocks=[(family,dict(log_loss_delta=sum(m[1]-m[0] for m in observations)/len(observations),
                         accuracy_delta=sum(m[3]-m[2] for m in observations)/len(observations)))
            for (_,family),observations in pairs.items()]
    return dict(scope='Fixed historical calibration pairs only; models already fitted/frozen, no fitting or parameter selection.',
        comparison='Exact correlated model versus exact same-weight/same-Flag-row-prior theta=0 control. Differences isolate cross-piece adjacency model.',
        model_sha256=digest(paths[0]),control_sha256=digest(paths[1]),analysis_sha256=digest(Path(__file__)),
        corpus_sha256=digest(corpus),tournament_sha256=digest(corpus.with_name('development.fmtour')),
        games=len(values),snapshots=len(selected),paired=bootstrap(blocks),
        by_public_clue={group:dict(snapshots=len(observations),
            control_log_loss=sum(m[0] for m in observations)/len(observations),
            joint_log_loss=sum(m[1] for m in observations)/len(observations),
            control_accuracy=sum(m[2] for m in observations)/len(observations),
            joint_accuracy=sum(m[3] for m in observations)/len(observations))
            for group,observations in byclue.items()},
        limitation='Exact Flag posterior predictions, not eight sampled runtime worlds. Log-loss improvements do not establish playing strength.')


if __name__=='__main__':
    report=audit()
    out=ROOT/'docs/ai-honest-campaign-2026-10-15/research/joint-exact-control-calibration.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
