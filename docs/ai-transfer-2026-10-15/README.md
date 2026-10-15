# Teacher transfer feasibility — 15 October 2026

**Neither desktop student passes its offline learning gate.** Production remains
Guarded Student v1. No strength tournament, X16 compression or promotion was
launched. This investigation tested whether an existing stronger teacher could
be transferred before investing in another strategic mechanism.

Context Teacher v1 already scored 62.4% against production in the
[earlier independent validation](../ai-cycle-2026-10-15/teacher-validation.json).
That establishes a desktop advantage on the tested distribution; it does not
identify which parts are strategic planning rather than tactical search.

## What the investigation found

The previous compact student was not simply too small. Its held-out error
against retained teacher targets was **11.73**, while the existing production
model already scored **9.35**. The zero-correction comparison, 11.18, was an
incomplete baseline because the targets include production's existing learned
correction. Exploratory larger versions of that same regression tree did not
improve held-out error. These are diagnostic fits, not selectable policies or
new playing-strength evidence. See [label analysis](checks/evaluation-labels.json)
and [capacity analysis](checks/evaluation-capacity.json).

The teacher also supplies noisy preferences. Across **32 outcome-blind public
roots**, two independent batches of eight sampled hidden armies chose the same
move in **23 cases**. Nine alternatives to production were repeated in both
batches. Disagreements include substantial score margins, so noise is not confined
to ties. This small development diagnostic measures repeatability, not the
correctness of a move or its chance of winning. Full public histories, own ranks,
boards and strategic contexts were reconstructed; production-equivalent choices
matched in all 32 cases. See [stability](checks/stability.json).

## Two preserved desktop models

Both models retain production's existing tree and add a correction bounded to
±192. Both use the same 16 permitted move features, 64 shallow trees, and the
existing cooperation guard. They have native C inference and immutable source
snapshots in the catalogue; neither is a production upgrade.

The original [plan](plan.json) specified one fixed fit and an offline gate before
fresh games. **Ranking Student v1 / Normal** (`ranking-student-v1-normal`)
trained pairwise preferences among the top three teacher and production moves.
The model improved that pairwise loss but made worse actual choices: other legal
moves remained eligible at runtime without being adequately constrained during
training. On the original 53 held-out roots, it chose 17 moves outside that
shortlist; 16 were worse under the retained teacher scores. This was a modeling
mistake in this trial, not evidence that teacher transfer is impossible.

One explicit [coverage-repair plan](coverage-repair-plan.json) expanded the
original one-fit limit. **Ranking Student v2 / Normal**
(`ranking-student-v2-normal`) compares all legal-action pairs using the same
features, training roots, capacity and hyperparameters. No further design,
parameter adjustment or fit followed its result. Because the old held-out result
informed this repair, those positions are development evidence for v2. Fresh
tournament seeds were reserved, but neither model reached the gate to use them.

| Internal teacher-score regret; lower is better | Production | Ranking v1 | Ranking v2 |
| --- | ---: | ---: | ---: |
| 267 training positions | 30.99 | 38.37 | 31.30 |
| 53 original held-out positions; development only for v2 | 23.34 | 43.68 | 24.51 |

Regret is the retained teacher's best score minus its score for the selected
move. It is **not a win percentage** or an independently observed action value.
The values account for the actual cooperation guard and native tie-breaking.
V1 fails the original held-out gate. V2 fails its predeclared mean training
regret gate. Its equal-group training statistic is more favorable, but does not
replace that failed gate. See the [v1 model](model/model.json),
[v2 model](coverage-repair-model/model.json) and
[independent objective audit](checks/ranking-objective-audit.json).

## What this does and does not explain

An optimistic diagnostic gives every position its own ideal bounded correction
mapping over the existing features. It can select the teacher's best move in
**318 of 320 positions**, and some improvement in every one of the 128 positions
where production has positive teacher regret. The two exceptions involve the
fixed cooperation guard. Thus within-position feature collisions, correction
bounds and the guard explain little of these fitting failures.

This diagnostic does not prove that one model can learn a consistent mapping
across positions or generalize. It also does not show that the teacher's best
scored move truly improves the game. The [representability report](checks/representability.json)
explicitly records these limits.

The strongest conclusion is narrower: **our training losses can improve without
improving the move actually selected.** The first trial exposed an action-coverage
flaw; fixing that substantially reduced the damage, but did not deliver useful
learning. Teacher sampling noise is another measured obstacle. There is no basis
here for blaming the exporter, claiming that more capacity alone solves transfer,
or asserting that an entirely new army planner is necessary.

A next learning experiment should first demonstrate improvement in actual
training choices with uncertainty-aware teacher labels and then use independent
positions and fresh whole-game validation. Do not continue fitting against the
53 old held-out positions and describe them as independent validation. No such
third experiment is part of this investigation.

## Source and verification

Both policies are labelled `rejected-offline` and remain rebuildable/selectable
for review. The optional ensemble evaluator leaves the default production model
and build flags intact. A diagnostic-only `guarded` query exposes whether a move's
learned correction is suppressed; it does not alter game state.

Verification includes:

- Exact frozen-teacher observer parity across **320 roots / 7,754 legal actions**:
  native scores, features and baseline choices match the recovered training inputs.
- Each student's native inference matches Python over **53 full-history positions
  / 1,246 actions**, repeated on cold roots. Actual native decisions reproduce the
  regret results, including 35 guarded actions.
- Zero-ensemble preservation, positive/negative clipping and 53 paired sampled
  hidden-world masking comparisons for each model. Frozen probe sources, headers,
  binaries and commands are in the runtime evidence ZIPs.
- `make all native check`: production builds and regression checks pass, including
  15,163 hidden-rank permutation decisions and 3,836 private-inventory comparisons.

The initial fit executed again after a JSON scalar serialization error; the
algorithm, data and parameters were unchanged. The initial log and inputs are
retained. A separate measurement fix changed teacher-style tie preference to
native first-maximum selection without refitting or changing either model.
The initial metrics are retained in `checks/model-before-native-tie-correction.json`.

Reproduce diagnostics and inference checks:

```sh
python3 tools/diagnose_transfer_labels.py
python3 tools/diagnose_transfer_teacher.py
python3 tools/audit_transfer_objective.py
python3 tools/diagnose_transfer_representability.py
python3 tools/audit_teacher_transfer.py
python3 tools/test_ranking_student.py
python3 tools/test_ranking_student.py \
  --identity ranking-student-v2-normal \
  --model-dir docs/ai-transfer-2026-10-15/coverage-repair-model \
  --output-prefix docs/ai-transfer-2026-10-15/checks/ranking-v2-runtime
```

Completed model directories must be preserved; training refuses to overwrite
one. New experiments require new plans, IDs and independent evaluation cohorts.
The [completion audit](audit.json) records hashes, outcomes, unused tournament cohorts and the
elapsed time against the requested 40-minute limit.
