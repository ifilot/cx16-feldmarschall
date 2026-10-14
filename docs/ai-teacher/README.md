# Desktop teacher and compact student experiments

14 October 2026

The masked-policy rollout teacher establishes a useful Classic Normal strength
gain against the frozen mission policy and the earlier material teacher. A
student trained on representative development games also passes an independent
strength gate, but breaks an existing Scout-support regression. It remains
disabled in production. Inventory features and a capture-only ablation do not
establish a gain. The next experiment must retain useful quiet decisions while
preserving support for a specialist.

## Teacher behaviour and validation

The original teacher searches a fully specified hypothetical world with a
three-ply material beam. The successor evaluates the same legal root actions
across sampled worlds, then uses the frozen mission policy for each subsequent
mover. Before every simulated decision it masks that mover's concealed enemies.
It restores hypothetical truth only for resolving the move. Separate random
streams prevent an opponent's private branching from changing the mover's RNG.
Its strategic utility also rewards progress toward the hypothetical flag, with
lake and stationary-piece constraints. Hypothetical ranks enter that utility,
but never the simulated mover's permitted board.

The adapter samples from public rank inventories, movement constraints and
encounter histories. The frozen successor uses eight samples, four plies and
bounded corrections to the mission evaluator. Immediate known victories retain
their native priority. Future rollout policy caches start cold; actual root
history and public sampling beliefs accumulate during play. This is a
masked-policy rollout approach, not a full information-set tree search.

| Experiment | Games | Score against reference | Paired 95% interval |
| --- | ---: | ---: | --- |
| Material teacher, raw development | 280 | 53.6% | 48.2–58.9% |
| Rollout teacher, raw development | 280 | 67.3% | 61.8–72.7% |
| Rollout correction, development | 280 | 68.4% | 63.9–72.9% |
| Frozen rollout correction versus missions | 1,400 | 71.0% | 69.0–73.0% |
| Frozen rollout correction versus material teacher | 1,400 | 54.0% | 51.9–56.1% |

The final two runs use independent, predeclared seeds, all seven layout
families and swapped engine sides with identical deployments. The mission
comparison has one capped game and positive results in all seven families.
The material reference uses the same public sampler and correction adapter,
with its original three-ply search. Compute and horizon are not matched;
the comparison establishes the successor's combined benefit rather than
isolating the effect of masking or strategic utility.

Focused histories cover quiet repetition, decoys, Miner approaches, specialist
losses and blocked controls. They verify permitted views and legal decisions;
changing a selected move alone is not evidence of a better continuation.
The teacher audit also compares identical initial information and observations
under changed concealed assignments, including subsequent mover decisions.

## Student data and results

The first fit used 512 positions from the retained loss/stall corpus. Its
17-node, 102-byte tree generated 23,376 full/cold-history labels and scored
37.1% against missions over 560 new development games. It was rejected.

A second corpus samples development games by layout family, phase and army,
without selecting by outcome. Opening positions precede ply 60, middle positions
precede ply 180, and later positions form the final bucket. It contains 973
positions from 280 source games. Forty buckets supply 24 examples each;
forward layouts have only seven red and six blue late positions available.
The corpus retains this shortage rather than duplicating examples.

Each position supplies full and cold history. The producer reconstructs the
player's initial army from legitimate own ranks and Classic battle disclosures.
Only the permitted input and public history reach teacher workers. Source family
and seed determine grouping, keeping paired games and related positions together.
The second fit has 97 training groups and 27 holdout groups, with 32,998 and
13,810 rows respectively. The 46,808 rows include 44,540 quiet moves. The teacher
evaluated 1,532,042 nodes. Both subsequent trees have 31 nodes and occupy 186 bytes.

| Student experiment | Games | Score versus missions | Decision |
| --- | ---: | ---: | --- |
| Original loss/stall fit | 560 | 37.1% | Reject |
| Representative data, original 16 features | 560 | 55.4% | Freeze for validation |
| Same frozen model, independent validation | 1,400 | 56.25% | Strength passes; tactical gate fails |
| Representative data, 21 public features | 560 | 51.4% | Reject |
| Original 16 features, capture-only correction | 560 | 50.0% | Reject |

The independent score interval is 53.96–58.54%. All seven family point estimates
exceed 50%; most individual family intervals remain inconclusive. Twelve games
reach the ply cap. The model avoids two disclosed specialist losses in the
18-case diagnostic set, choosing curated alternatives. Hard remains unchanged
because student scoring applies only to Classic Normal.

However, the existing tactical fixture requires a Scout to support a blocked
Miner by moving from 61 to 41. The full model instead moves to 31 in all 32
Normal seeds. A quiet correction limit of two still fails two seeds. Removing
quiet corrections passes tactics, 15,163 hidden-rank permutation comparisons
and 3,836 Silent Defense comparisons, but loses the measured strength gain.
These gates were retained without weakening the Scout expectation.

The 21-feature ablation adds disclosed enemy inventory context, remaining own
Miners and forward movement. Its labels, original 16 features and grouping match
the corresponding 46,808 original rows exactly. It has the same Scout regression
and no established development strength gain. These features remain opt-in.

Held-out mean absolute error also fails to beat zero correction: 14.52 versus
13.96 for the representative 16-feature model, and 14.86 for the context model.
The game results justify investigating move ranking and quiet-move safeguards,
rather than treating regression accuracy as a sufficient promotion criterion.

## Evidence and reproduction

The [manifest](manifest.json) identifies the [evidence archive](evidence-20261014.zip).
It contains full/cold public inputs, labels, generated models, source snapshots,
programs, frozen teacher settings, strength gates, focused reports and rejected
tactical results. The initial failed producer is retained too: it compared stale
coordinates for a zero-count repetition record. Canonicalizing those unused
coordinates fixes reconstruction without changing the observed repetition state.

Game archives and acceptance/rejection records are in the
[experiment ledger](../ai-experiments.json). The evidence archive uses repository
relative `build/` paths. Restore benchmark archives into their corresponding run
directories to re-audit the absolute paths recorded in the frozen teacher gate;
new experiments must use new output directories and fresh validation seeds.

```sh
make test-teacher-rollout test-teacher-student-inputs
make test-teacher-corpus test-student-context
python3 tools/verify_ai_archives.py
python3 tools/verify_student_stage.py \
  --policy build/ai-student/balanced-v2-development/frozen-policy.json \
  --run build/ai-student/balanced-v2-validation --out NEW_STRENGTH_REPORT
python3 tools/build_teacher_corpus.py \
  --run build/ai-teacher/rollout-correction-development \
  --out NEW_CORPUS --per-bucket 24
python3 tools/train_teacher_student.py --gate build/ai-teacher/teacher-gate.json \
  --corpus NEW_CORPUS/positions.jsonl --positions 973 --samples 8 --jobs 4 \
  --out NEW_FIT
make native-student-v2 AI_STUDENT_V2_DIR=NEW_FIT
```

The all-action model's tactical test is an expected rejection, not a passing
integration check. No student has earned X16 promotion. Production still uses
coordinated missions with the validated deployment mixtures. Variant strength,+a successful mission/student change and its hardware gates remain outstanding.
