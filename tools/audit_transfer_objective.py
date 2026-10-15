"""Audit one frozen ranking fit without changing its model or acceptance gate."""
import collections
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import shlex
import zipfile
from ai_registry import ROOT,build_policy
from diagnose_transfer_teacher import restore
from feldmarschall import Engine,parse_square
from train_ranking_student import delta
BASE=ROOT/'docs/ai-transfer-2026-10-15'

def frozen_parity(job):
    record,root,observer=job
    engine=Engine(shlex.quote(str(observer)))
    try:
        restore(engine,record);info=record['input']
        engine.send(f"features {info['army']} {info['enemy_lost_hex']} {info['board_hex']} 0")
        features={}
        while True:
            words=engine.read().split()
            if words[0]=='features_done':break
            assert words[0]=='feature';v=list(map(int,words[1:]));features[tuple(v[:2])]=v[2:]
        engine.send('ranked');scores={}
        while True:
            words=engine.read().split()
            if words[0]=='move':parent=tuple(map(parse_square,words[1:3]));break
            if words[0]=='candidate':scores[tuple(map(int,words[1:3]))]=int(words[3])
        assert parent==tuple(root['parent'])
        assert len(scores)==len(root['rows'])
        for r in root['rows']:
            key=tuple(r['move']);assert scores[key]==r['native'];assert features[key]==r['features']
        return dict(id=root['id'],moves=len(scores),parity=True)
    finally:engine.close()

def main():
    p=BASE/'model';model=json.loads((p/'model.json').read_text());trees=model['trees']
    with zipfile.ZipFile(p/'ranking-inputs.zip') as z:roots=[json.loads(x) for x in z.read('roots.jsonl').splitlines()]
    report=dict(source_sha256=hashlib.sha256((ROOT/'tools/train_ranking_student.py').read_bytes()).hexdigest(),model_sha256=hashlib.sha256((p/'model.json').read_bytes()).hexdigest(),audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Post-fit diagnosis, no refit or gate change. Teacher regret is internal rounded teacher score, not game strength. Native tie simulation uses first enumerated action. Missing features are not established by this audit.')
    for validation in (False,True):
        losses=[[],[]];c=collections.Counter();regrets=[[],[]];ties=0
        for root in roots:
            if bool(root['validation'])!=validation:continue
            rr=root['rows'];n=len(rr);indices=sorted(set(sorted(range(n),key=lambda i:rr[i]['teacher_value'],reverse=True)[:3]+sorted(range(n),key=lambda i:rr[i]['native'],reverse=True)[:3]))
            wins=[r for r in rr if r['native']>=30000];options=wins or rr
            score=lambda r:r['native']+(0 if r['guarded'] else delta(trees,r['features']))
            prod=max(options,key=lambda r:r['native']);student=max(options,key=score)
            offline=max(options,key=lambda r:(score(r),tuple(r['move'])==tuple(root['parent']),-r['move'][0],-r['move'][1]))
            ties+=student['move']!=offline['move'];best=max(r['teacher_value'] for r in rr)
            regrets[0].append(best-prod['teacher_value']);regrets[1].append(best-student['teacher_value'])
            outside=rr.index(student) not in indices;harmful=student['teacher_value']<prod['teacher_value']
            c['roots']+=1;c['selected_outside_shortlist']+=outside;c['harmful_outside_shortlist']+=outside and harmful;c['harmful_changes']+=harmful;c['helpful_changes']+=student['teacher_value']>prod['teacher_value']
            if wins:continue
            pairs=[(a,b) for i,a in enumerate(indices) for b in indices[i+1:] if abs(rr[a]['teacher_value']-rr[b]['teacher_value'])>1 and not(rr[a]['guarded'] and rr[b]['guarded'])]
            for use_model in (False,True):
                ll=[]
                for a,b in pairs:
                    desired=1/(1+math.exp(-max(-30,min(30,(rr[a]['teacher_value']-rr[b]['teacher_value'])/24))))
                    value=lambda r:score(r) if use_model else r['native']
                    margin=(value(rr[a])-value(rr[b]))/24
                    ll.append(max(margin,0)-margin*desired+math.log1p(math.exp(-abs(margin))))
                if ll:losses[use_model].append(sum(ll)/len(ll))
        report['held_out' if validation else 'training']=dict(c,native_tie_rule_disagreements=ties,production_regret=sum(regrets[0])/len(regrets[0]),student_native_tie_regret=sum(regrets[1])/len(regrets[1]),pair_loss_production=sum(losses[0])/len(losses[0]),pair_loss_student=sum(losses[1])/len(losses[1]))
    with zipfile.ZipFile(ROOT/'docs/ai-cycle-2026-10-15/student-model/training-evidence.zip') as z:records=[json.loads(x) for x in z.read('public-inputs.jsonl').splitlines()]
    executable,receipt=build_policy('teacher-context-v1-normal');by={r['id']:r for r in roots}
    with ThreadPoolExecutor(max_workers=4) as pool:parity=list(pool.map(frozen_parity,[(r,by[r['id']],executable.parent/'observer') for r in records]))
    report['frozen_observer_parity']=dict(positions=len(parity),actions=sum(r['moves'] for r in parity),all_match=all(r['parity'] for r in parity),frozen_source_sha256=receipt['policy']['source_sha256'],positions_detail=parity)
    (BASE/'checks/ranking-objective-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='frozen_observer_parity'},indent=2));print('Frozen observer parity:',len(parity),'roots',sum(r['moves'] for r in parity),'actions')
if __name__=='__main__':main()
