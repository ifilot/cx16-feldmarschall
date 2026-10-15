"""Read-only diagnostics of the retained grouped teacher-correction labels."""
import collections
import hashlib
import json
from pathlib import Path
import statistics
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from train_ai_student import predict

def diagnose():
    source=ROOT/'docs/ai-cycle-2026-10-15/student-model/training-evidence.zip'
    with zipfile.ZipFile(source) as archive:
        rows=[json.loads(line) for line in archive.read('labels.jsonl').splitlines()]
        model=json.loads(archive.read('model.json'))
    train=[r for r in rows if not r['validation']]
    held=[r for r in rows if r['validation']]
    def summarize(selected):
        vectors=collections.defaultdict(list)
        for row in selected:vectors[tuple(row['features'])].append(row['target'])
        return {'rows':len(selected),'positions':len({r['position'] for r in selected}),
          'groups':len({r['split_group'] for r in selected}), 'unique_vectors':len(vectors),
          'target_min':min(r['target'] for r in selected),'target_max':max(r['target'] for r in selected),
          'target_zero_fraction':sum(r['target']==0 for r in selected)/len(selected),
          'target_abs_mean':statistics.mean(abs(r['target']) for r in selected),
          'zero_mae':statistics.mean(abs(r['target']) for r in selected),
          'frozen_27node_mae':statistics.mean(abs(predict(model['nodes'],r['features'])-r['target']) for r in selected),
          'in_sample_best_vector_median_mae':sum(sum(abs(y-statistics.median(ys)) for y in ys) for ys in vectors.values())/len(selected),
          'rows_in_conflicting_vectors':sum(len(ys) for ys in vectors.values() if min(ys)!=max(ys)),
          'rows_in_vectors_with_target_range_at_least_32':sum(len(ys) for ys in vectors.values() if max(ys)-min(ys)>=32)}
    vectors=collections.defaultdict(list)
    for row in train:vectors[tuple(row['features'])].append(row['target'])
    seen=[r for r in held if tuple(r['features']) in vectors]
    paired=collections.defaultdict(dict)
    positions=collections.defaultdict(list)
    for row in rows:
        paired[(row['position'],tuple(row['move']))][row['history']]=row
        positions[(row['position'],row['history'])].append(row)
    same=[pair for pair in paired.values() if pair['full']['features']==pair['cold']['features']]
    within=[]
    for key, actions in positions.items():
        v=collections.defaultdict(list)
        for action in actions:v[tuple(action['features'])].append(action['target'])
        within.append(any(len(ys)>1 and min(ys)!=max(ys) for ys in v.values()))
    report={'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'all':summarize(rows),'training':summarize(train),'held_out':summarize(held),
      'held_out_seen_vectors':len(seen),'held_out_seen_fraction':len(seen)/len(held),
      'held_out_seen_vector_median_mae':statistics.mean(abs(statistics.median(vectors[tuple(r['features'])])-r['target']) for r in seen),
      'full_cold_action_pairs':len(paired),'identical_features_full_cold_pairs':len(same),
      'identical_features_different_target_pairs':sum(p['full']['target']!=p['cold']['target'] for p in same),
      'identical_features_full_cold_mean_absolute_target_difference':statistics.mean(abs(p['full']['target']-p['cold']['target']) for p in same),
      'position_history_groups_with_internal_feature_target_conflicts':sum(within),
      'position_history_groups':len(within),
      'limits':['Correction targets alone omit native scores, effective guarded scores, and teacher selected move. Decision regret and action agreement cannot be recovered from this archive.',
       'Different correction targets for identical features indicate label aliasing, not necessarily different optimal actions: native action scores may resolve choices.',
       'In-sample median-vector MAE is a memorization lower bound on this sample, not held-out performance or irreducible population noise.',
       'Full/cold target differences can include context changes and sampled-world differences. They do not isolate a single missing feature.']}
    print(json.dumps(report,indent=2))
    return report
if __name__=='__main__':diagnose()
