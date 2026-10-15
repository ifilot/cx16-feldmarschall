"""Optimistic per-root reachability with a shared correction per feature vector."""
import hashlib
import json
from pathlib import Path
import zipfile
from ai_registry import ROOT
BASE=ROOT/'docs/ai-transfer-2026-10-15'
LIMIT=192

def analyze(root):
    rows=root['rows']
    winning=[i for i,r in enumerate(rows) if r['native']>=30000]
    options=winning or list(range(len(rows)))
    production=max(options,key=lambda i:rows[i]['native'])
    teacher_best=max(r['teacher_value'] for r in rows)
    reachable=set();witnesses={}
    # For an unguarded target, raising its entire feature-equivalence class
    # and lowering every other class maximizes its advantage over every rival.
    # For a guarded target its score is fixed, so lowering all unguarded rivals
    # is optimal, including rivals with the target's own feature vector.
    for target in options:
        feature=tuple(rows[target]['features'])
        def correction(i):
            if rows[i]['guarded']:return 0
            if not rows[target]['guarded'] and tuple(rows[i]['features'])==feature:return LIMIT
            return -LIMIT
        chosen=max(options,key=lambda i:rows[i]['native']+correction(i))
        if chosen==target:
            reachable.add(target)
            witnesses[target]=dict(target_feature=list(feature),target_guarded=bool(rows[target]['guarded']),strategy='all unguarded corrections -192' if rows[target]['guarded'] else 'target feature +192; other features -192; guarded actions 0')
    assert production in reachable
    attainable=max(reachable,key=lambda i:rows[i]['teacher_value'])
    production_regret=teacher_best-rows[production]['teacher_value']
    minimum_regret=teacher_best-rows[attainable]['teacher_value']
    assert minimum_regret<=production_regret+1e-9
    allvectors={tuple(r['features']) for r in rows}
    return dict(id=root['id'],group=root['group'],validation=bool(root['validation']),actions=len(rows),unique_features=len(allvectors),reachable_actions=len(reachable),production_move=rows[production]['move'],production_regret=production_regret,optimistic_minimum_teacher_regret=minimum_regret,teacher_best_reachable=minimum_regret<1e-9,production_has_positive_regret=production_regret>1e-9,better_than_production_reachable=minimum_regret<production_regret-1e-9,best_reachable_move=rows[attainable]['move'],witness=witnesses[attainable])

def summarize(rows):
    positive=[r for r in rows if r['production_has_positive_regret']]
    return dict(positions=len(rows),production_mean_regret=sum(r['production_regret'] for r in rows)/len(rows),optimistic_mean_minimum_regret=sum(r['optimistic_minimum_teacher_regret'] for r in rows)/len(rows),teacher_best_reachable=sum(r['teacher_best_reachable'] for r in rows),production_positive_regret=len(positive),positive_regret_better_choice_reachable=sum(r['better_than_production_reachable'] for r in positive),positive_regret_teacher_best_reachable=sum(r['teacher_best_reachable'] for r in positive),irreducible_positive_regret=sum(r['optimistic_minimum_teacher_regret']>1e-9 for r in rows),positions_with_within_root_feature_aliases=sum(r['actions']>r['unique_features'] for r in rows))

def main():
    archive=BASE/'model/ranking-inputs.zip'
    with zipfile.ZipFile(archive) as z:roots=[json.loads(x) for x in z.read('roots.jsonl').splitlines()]
    results=[analyze(r) for r in roots]
    report=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),input_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),features=16,correction_limit=LIMIT,method='For each candidate action, optimize its relative score by assigning +192 to its feature class and -192 to other classes, with guarded actions fixed at zero. For guarded candidates assign every unguarded class -192. Native first-enumerated ties and immediate-victory action restriction are retained. This exactly tests individual-root reachability with arbitrary bounded feature lookup corrections.',scope='An optimistic lower bound on internal single-batch teacher regret, separately choosing a different mapping for every root. It does not establish one globally consistent model, learnability from data, held-out generalization, true action quality, game strength or X16 feasibility. Original grouped held-out roots became development data in the separate v2 coverage-repair plan.',all=summarize(results),training=summarize([r for r in results if not r['validation']]),old_held_out_now_development=summarize([r for r in results if r['validation']]),positions=results)
    (BASE/'checks/representability.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='positions'},indent=2))
if __name__=='__main__':main()
