"""One grouped full/cold-history fit from this cycle's public development games."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

from ai_cycle import BASE
from ai_registry import ROOT, build_policy
from build_teacher_corpus import extract, select
from train_ai_student import fit, predict
from train_teacher_student import label_record, public_record
from tournament_store import Tournament


def train():
    out = BASE/'student-model'
    out.mkdir(exist_ok=False)
    source=BASE/'tournaments/teacher-development/teacher-context-v1-normal--student-guard-v1-normal.fmtour'
    with Tournament(source) as tournament:
        assert tournament.metadata()['status']=='complete'
        games=[]
        for row in tournament.games():
            game=tournament.game(row['id'])
            games.append(dict(game,group=game['family'],deployments=[game['red_setup'],game['blue_setup']]))
    source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    selected=select(games,8)
    corpus=list(extract(games,selected,source_sha))
    records=[public_record(r) for r in corpus]
    baseline=[]
    for line in (ROOT/'src/core/ai_student_model_production.h').read_text().splitlines():
        numbers=re.findall(r'-?\d+',line)
        if line.strip().startswith('{') and len(numbers)==5:
            baseline.append(dict(zip(('feature','threshold','left','right','value'),map(int,numbers))))
    assert len(baseline)==31
    executable,receipt=build_policy('teacher-context-v1-normal')
    tasks=[(record,str(executable.parent/'observer'),str(executable.parent/'teacher'),8,
            dict(context=True,baseline_model=baseline)) for record in records]
    rows=[]; nodes=0
    with (out/'labels.jsonl').open('x') as labels, ThreadPoolExecutor(max_workers=4) as pool:
        for index,result in enumerate(pool.map(label_record,tasks),1):
            rows.extend(result['rows']);nodes+=result['nodes']
            for row in result['rows']:labels.write(json.dumps(row,sort_keys=True)+'\n')
            if index%16==0:print(f'{index}/{len(records)} positions',flush=True)
    training=[r for r in rows if not r['validation']]; validation=[r for r in rows if r['validation']]
    assert training and validation
    train_groups={r['split_group'] for r in training}; held_groups={r['split_group'] for r in validation}
    assert not train_groups & held_groups
    model=fit(training,depth=4,minimum=24)
    header=['/* Context Rollout Student v1: generated from public development histories. */',
            'static const student_node_t student_nodes[] = {']
    for node in model:header.append('    {'+','.join(str(node[k]) for k in ('feature','threshold','left','right','value'))+'},')
    header.append('};')
    (out/'ai_student_model_v2.h').write_text('\n'.join(header)+'\n')
    (out/'public-inputs.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in records))
    report=dict(nodes=model,node_bytes=len(model)*6,positions=len(records),rows=len(rows),teacher_nodes=nodes,
                source_tournament=str(source.relative_to(ROOT)),source_sha256=source_sha,teacher=receipt,
                training_groups=len(train_groups),held_out_groups=len(held_groups),
                training_rows=len(training),held_out_rows=len(validation),
                validation_mae=sum(abs(predict(model,r['features'])-r['target']) for r in validation)/len(validation),
                zero_mae=sum(abs(r['target']) for r in validation)/len(validation),
                label_target='existing guarded-student correction plus context teacher delta; shared assigned-actor guard remains in runtime',
                selection='eight deterministic public positions per available family/phase/army bucket; no outcome selection; paired seed groups never split',
                scope='Development fit. Teacher validation, independent student games, tactics, fairness and X16 checks remain separate adoption gates.')
    (out/'model.json').write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(out/'training-evidence.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
        for name in ('labels.jsonl','public-inputs.jsonl','model.json','ai_student_model_v2.h'):
            bundle.write(out/name,name)
    # Keep the compact archive and readable model/manifest in the repository.
    (out/'labels.jsonl').unlink();(out/'public-inputs.jsonl').unlink()
    print(json.dumps({k:v for k,v in report.items() if k not in ('nodes','teacher')},indent=2))


if __name__=='__main__':train()
