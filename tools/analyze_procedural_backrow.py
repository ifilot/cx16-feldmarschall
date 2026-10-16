"""Post-hoc cheap-control audit; never fit to the reused predictive cohort."""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from ai_registry import ROOT
from campaign_template_beliefs import background_log_evidence
from feldmarschall import COUNTS


class BackrowBackground:
    """Uniform legal armies conditional on the Flag lying in an allowed set."""
    def __init__(self, counts=COUNTS, allowed=range(30, 40)):
        self.counts = tuple(counts)
        self.size = sum(counts)
        self.bomb = len(counts)-2
        self.flag = len(counts)-1
        self.allowed = set(allowed)
        assert self.counts[self.flag] == 1 and self.allowed

    def predict(self, known, moved, with_bombs=True):
        known = {int(o): r for o, r in known.items()}
        moved = set(moved)
        log_uniform = background_log_evidence(known, moved, self.counts, self.bomb)
        if not math.isfinite(log_uniform):
            return dict(log_evidence=-math.inf, flag=None, bomb=None)
        candidates = set(range(self.size))-set(known)-moved
        known_flags = [o for o, r in known.items() if r == self.flag]
        if known_flags:
            if known_flags[0] not in self.allowed:
                return dict(log_evidence=-math.inf, flag=None, bomb=None)
            flag = [float(o == known_flags[0]) for o in range(self.size)]
            ratio = self.size/len(self.allowed)
        else:
            allowed = candidates & self.allowed
            if not allowed:
                return dict(log_evidence=-math.inf, flag=None, bomb=None)
            flag = [float(o in allowed)/len(allowed) for o in range(self.size)]
            ratio = self.size*len(allowed)/(len(self.allowed)*len(candidates))
        bomb = None
        if with_bombs:
            remaining = self.counts[self.bomb]-sum(r == self.bomb for r in known.values())
            denominator = len(candidates)-int(not known_flags)
            bomb = [float(known[o] == self.bomb) if o in known else
                    remaining*(1-flag[o])/denominator if o in candidates and denominator else 0.
                    for o in range(self.size)]
            assert abs(sum(bomb)-self.counts[self.bomb]) < 1e-9
        return dict(log_evidence=log_uniform+math.log(ratio), flag=flag, bomb=bomb)


def compare_saved(source, out):
    sys.path.insert(0, str(source))
    from study import bootstrap
    structured = json.loads((source/'result.json').read_text())['scored_rows']
    backrow = json.loads((out/'result.json').read_text())['scores']
    key = lambda row: (row['formation'], row['branch'], row['case'], row['step'])
    a = {key(row): row for row in structured}
    b = {key(row): row for row in backrow}
    assert a.keys() == b.keys()
    rows = []
    bomb_rows = []
    for k, row in a.items():
        other = b[k]
        assert row['hard'] == other['hard']
        shared = dict(formation=row['formation'], branch=row['branch'], case=row['case'], step=row['step'])
        rows.append(dict(shared, delta_logloss_nats=row['delta_logloss_nats']-other['delta_logloss_nats']))
        bomb_rows.append(dict(shared, delta_logloss_nats=row['candidate_Bomb_brier']-other['candidate_Bomb_brier']))
    report = bootstrap(rows)
    report['interpretation'] = 'Post-hoc descriptive ablation on reused heldout prediction data, not fresh confirmation. Negative favors structured over backrow. No parameters selected or altered.'
    report['secondary_bomb_brier_difference'] = bootstrap(bomb_rows)
    report['secondary_bomb_brier_difference']['units'] = 'Mean40-origin Bomb Brier difference, not nats; negative favors structured. Same trajectory/block averaging, descriptive secondary endpoint.'
    (out/'structured-minus-backrow.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    source = ROOT/'docs/ai-honest-campaign-2026-10-15/research/procedural-background-v1'
    out = source.parent/'procedural-backrow-ablation'
    out.mkdir(exist_ok=False)
    sys.path.insert(0, str(source))
    from study import evaluate, bootstrap
    protocol = dict(epoch=time.time(), label='Post-hoc mechanism ablation on an already viewed predictive cohort; no independent confirmation.',
                    models='Uniform background; fixed backrow-only conditional-uniform background; frozen source-structured background. Outer template0.8/background0.2 and structural-selected uniform tail0.01 identical for both candidate controls.',
                    fitting='No parameters fitted or selected. Backrow-only model is a new source-fact control, not a tuned version of the validated structural model.',
                    source_sha256={n: hashlib.sha256((source/n).read_bytes()).hexdigest() for n in ('heldout-public-prefixes.json', 'result.json', 'trained-model.json')},
                    next_step='Any playing-strength comparison uses new immutable policy IDs and fresh tournament seeds.')
    (out/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    rows = json.loads((source/'heldout-public-prefixes.json').read_text())
    started = time.perf_counter()
    scores = evaluate(rows, BackrowBackground(), .01)
    elapsed = time.perf_counter()-started
    comparison = dict(backrow_minus_uniform=bootstrap(scores), elapsed_seconds=elapsed,
                      prefixes=len(rows), branches={})
    for branch in ('template', 'procedural'):
        group = [r for r in scores if r['branch'] == branch]
        comparison['branches'][branch] = dict(samples=len(group), mean_logloss_delta=sum(r['delta_logloss_nats'] for r in group)/len(group),
            confident_wrong_occurrences=sum(r['candidate']['confident_wrong'] for r in group),
            baseline_confident_wrong_occurrences=sum(r['hard']['confident_wrong'] for r in group))
    (out/'result.json').write_text(json.dumps(dict(summary=comparison, scores=scores), indent=2)+'\n')
    print(json.dumps(comparison, indent=2))
    print(json.dumps(compare_saved(source, out), indent=2))


if __name__ == '__main__':
    main()
