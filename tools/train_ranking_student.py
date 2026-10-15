"""One fixed residual ranking fit; retained public roots, grouped holdout, no tuning."""
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import zipfile
import numpy as np
from ai_registry import ROOT, get_policy
from diagnose_transfer_teacher import restore
from feldmarschall import Engine, parse_square, square_name
from train_ai_student import predict

BASE=ROOT/'docs/ai-transfer-2026-10-15'
SCALE=1000

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def baseline_model():
    nodes=[]
    for line in (ROOT/'src/core/ai_student_model_production.h').read_text().splitlines():
        v=re.findall(r'-?\d+',line)
        if line.strip().startswith('{') and len(v)==5:nodes.append(dict(zip(('feature','threshold','left','right','value'),map(int,v))))
    assert len(nodes)==31
    return nodes

def compile_observer():
    policy=get_policy('teacher-context-v1-normal'); exe=BASE/'checks/observer'
    command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow','-Isrc/core']
    command+=['-D'+x for x in policy['defines']]
    command+=['-o',str(exe),*policy['sources']]
    subprocess.run(command,cwd=ROOT,check=True)
    (BASE/'checks/observer-build.json').write_text(json.dumps(dict(command=command,sha256=sha(exe),compiler=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],sources={p:sha(ROOT/p) for p in policy['sources']}),indent=2)+'\n')
    return exe

def recover(job):
    record,rows,executable=job; engine=Engine(shlex.quote(str(executable)))
    try:
        restore(engine,record)
        info=record['input'];army=info['army']
        engine.send(f"features {army} {info['enemy_lost_hex']} {info['board_hex']} 0")
        features={}
        while True:
            words=engine.read().split()
            if words[0]=='features_done':break
            assert words[0]=='feature'; values=list(map(int,words[1:]));features[tuple(values[:2])]=values[2:]
        engine.send('ranked');scores={}
        while True:
            words=engine.read().split()
            if words[0]=='move':parent=tuple(map(parse_square,words[1:3]));break
            if words[0]=='candidate':scores[tuple(map(int,words[1:3]))]=int(words[3])
        assert set(scores)==set(features)=={tuple(r['move']) for r in rows}
        recovered=[]; baseline=baseline_model()
        for r in rows:
            move=tuple(r['move']);assert features[move]==r['features']
            guard=int(engine.ask('guarded '+' '.join(map(square_name,move)),'guarded'))
            delta=r['target']-predict(baseline,r['features'])
            recovered.append(dict(r,native=scores[move],guarded=guard,teacher_delta=delta,teacher_value=scores[move]+delta))
        return dict(id=record['id'],group=record['split_group'],validation=rows[0]['validation'],parent=parent,rows=recovered)
    finally:engine.close()

def tree_fit(x,g,h,depth=3,minimum=12,regularization=1.):
    nodes=[]
    def build(indices,level):
        idx=len(nodes);G=g[indices].sum();H=h[indices].sum()
        leaf=int(round(np.clip(24*G/(H+regularization),-24,24)*.2*SCALE))
        nodes.append(dict(feature=255,threshold=0,left=0,right=0,value=leaf))
        if level>=depth or len(indices)<2*minimum:return idx
        best=None
        parent=G*G/(H+regularization)
        for f in range(x.shape[1]):
            order=indices[np.argsort(x[indices,f],kind='stable')];v=x[order,f]
            cut=np.flatnonzero(v[:-1]!=v[1:])+1;cut=cut[(cut>=minimum)&(cut<=len(order)-minimum)]
            if not len(cut):continue
            gl=np.cumsum(g[order])[cut-1];hl=np.cumsum(h[order])[cut-1]
            gains=gl*gl/(hl+regularization)+(G-gl)**2/(H-hl+regularization)-parent
            k=int(np.argmax(gains));gain=float(gains[k]);c=int(cut[k]);threshold=int(v[c-1])
            option=(gain,-f,-threshold)
            if gain>1e-10 and (best is None or option>best[0]):best=(option,f,threshold,order[:c],order[c:])
        if best:
            _,f,t,left,right=best;l=build(left,level+1);r=build(right,level+1)
            nodes[idx]=dict(feature=f,threshold=t,left=l,right=r,value=0)
        return idx
    build(np.arange(len(x)),0);return nodes

def eval_tree(nodes,features):return predict(nodes,features)
def delta(trees,features):return max(-192,min(192,int(sum(eval_tree(t,features) for t in trees)/SCALE)))

def metrics(roots,trees):
    entries=[]
    for root in roots:
        rows=root['rows']; parent=tuple(root['parent'])
        winning=[r for r in rows if r['native']>=30000]
        def select(use_model):
            options=winning or rows
            # Native ai_move retains the first enumerated maximum (strict >).
            return max(options,key=lambda r:r['native']+(0 if r['guarded'] or not use_model else delta(trees,r['features'])))
        prod=select(False);student=select(True);best=max(r['teacher_value'] for r in rows)
        entries.append(dict(id=root['id'],group=root['group'],production=list(prod['move']),student=list(student['move']),production_regret=best-prod['teacher_value'],student_regret=best-student['teacher_value'],changed=prod['move']!=student['move']))
    groups=defaultdict(list)
    for e in entries:groups[e['group']].append(e['production_regret']-e['student_regret'])
    values=np.array([np.mean(v) for v in groups.values()]);rng=np.random.default_rng(1812026)
    samples=np.array([np.mean(rng.choice(values,len(values),replace=True)) for _ in range(10000)]) if len(values) else np.array([0.])
    return dict(positions=len(entries),groups=len(groups),production_regret=np.mean([e['production_regret'] for e in entries]),student_regret=np.mean([e['student_regret'] for e in entries]),mean_improvement=np.mean([e['production_regret']-e['student_regret'] for e in entries]),equal_group_mean_improvement=float(np.mean(values)),equal_group_95=list(np.quantile(samples,[.025,.975])),changed=sum(e['changed'] for e in entries),entries=entries)

def train(repair=False):
    out=BASE/('coverage-repair-model' if repair else 'model');out.mkdir(exist_ok=False)
    archive=ROOT/'docs/ai-cycle-2026-10-15/student-model/training-evidence.zip'
    with zipfile.ZipFile(archive) as z:
        records=[json.loads(l) for l in z.read('public-inputs.jsonl').splitlines()]
        labels=[json.loads(l) for l in z.read('labels.jsonl').splitlines() if json.loads(l)['history']=='full']
    by=defaultdict(list)
    for r in labels:by[r['position']].append(r)
    if repair:
        # The independently audited v1 inputs are unchanged; only pair coverage
        # changes. The old held-out set is development evidence for this repair.
        with zipfile.ZipFile(BASE/'model/ranking-inputs.zip') as z:
            roots=[json.loads(l) for l in z.read('roots.jsonl').splitlines()]
    else:
        observer=compile_observer()
        with ThreadPoolExecutor(max_workers=4) as pool:
            roots=[]
            for root in pool.map(recover,[(r,by[r['id']],observer) for r in records]):
                roots.append(root)
                if len(roots)%32==0:print(f'recovered {len(roots)}/320 roots',flush=True)
    with zipfile.ZipFile(out/'ranking-inputs.zip','x',zipfile.ZIP_DEFLATED) as z:z.writestr('roots.jsonl',''.join(json.dumps(r)+'\n' for r in roots))
    training=[r for r in roots if not r['validation']];held=[r for r in roots if r['validation']]
    assert not {r['group'] for r in training}&{r['group'] for r in held}
    rows=[r for root in training for r in root['rows']];x=np.array([r['features'] for r in rows],dtype=np.int16)
    native=np.array([r['native'] for r in rows],float);eligible=np.array([not r['guarded'] for r in rows]);trees=[]
    pairs=[];start=0
    for root in training:
        rr=root['rows'];n=len(rr)
        if not any(r['native']>=30000 for r in rr):
            indices=list(range(n)) if repair else sorted(set(sorted(range(n),key=lambda i:rr[i]['teacher_value'],reverse=True)[:3]+sorted(range(n),key=lambda i:rr[i]['native'],reverse=True)[:3]))
            pp=[(a,b) for i,a in enumerate(indices) for b in indices[i+1:] if abs(rr[a]['teacher_value']-rr[b]['teacher_value'])>1 and not(rr[a]['guarded'] and rr[b]['guarded'])]
            for a,b in pp:pairs.append((start+a,start+b,1/len(pp)))
        start+=n
    a=np.array([p[0] for p in pairs]);b=np.array([p[1] for p in pairs]);w=np.array([p[2] for p in pairs]);teacher=np.array([r['teacher_value'] for r in rows]);desired=1/(1+np.exp(-np.clip((teacher[a]-teacher[b])/24,-30,30)))
    current=native.copy();raw=np.zeros(len(rows))
    for it in range(64):
        probability=1/(1+np.exp(-np.clip((current[a]-current[b])/24,-30,30)))
        residual=(desired-probability)*w;curvature=np.maximum(.01,probability*(1-probability))*w
        g=np.zeros(len(rows));h=np.zeros(len(rows))
        np.add.at(g,a,residual);np.add.at(g,b,-residual);np.add.at(h,a,curvature);np.add.at(h,b,curvature)
        g[~eligible]=0;h[~eligible]=0
        tree=tree_fit(x,g,h);trees.append(tree)
        raw+=np.array([eval_tree(tree,r['features']) for r in rows]);current=native+eligible*np.clip(np.trunc(raw/SCALE),-192,192)
        if (it+1)%16==0:print(f'fitted {it+1}/64 ranking trees',flush=True)
    plan_path=BASE/('coverage-repair-plan.json' if repair else 'plan.json')
    report=dict(plan_sha256=sha(plan_path),corpus_sha256=sha(archive),input_sha256=sha(out/'ranking-inputs.zip'),trees=trees,trees_count=len(trees),node_count=sum(map(len,trees)),scale=SCALE,features=16,training=metrics(training,trees),held_out=metrics(held,trees),parameters=json.loads(plan_path.read_text())['learner'],scope='Internal rounded teacher score regret on retained grouped development roots; not win probability, not independent strength validation. For v2 the old held-out set informed this repair and is development evidence only.')
    report['offline_gate_passed']=bool(report['training' if repair else 'held_out']['mean_improvement']>0)
    (out/'model.json').write_text(json.dumps(report,indent=2)+'\n')
    header=['/* Ranking Student '+('v2' if repair else 'v1')+': additive desktop model; immutable trial. */','#define ENSEMBLE_TREES 64','#define ENSEMBLE_SCALE 1000','static const ensemble_node_t ensemble_nodes[] = {']
    offsets=[];n=0
    for tree in trees:
        offsets.append(n);n+=len(tree)
        for node in tree:header.append('    {'+','.join(str(node[k]) for k in ('feature','threshold','left','right','value'))+'},')
    header+=['};','static const unsigned int ensemble_offsets[] = {'+','.join(map(str,offsets))+'};']
    (out/'ai_student_ensemble.h').write_text('\n'.join(header)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('trees','training','held_out')},indent=2))
    for key in ('training','held_out'):print(key,json.dumps({k:v for k,v in report[key].items() if k!='entries'}))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage-repair',action='store_true')
    train(parser.parse_args().coverage_repair)
