# Desktop teacher and compact student experiments

14 October 2026

The masked-policy rollout teacher establishes a useful Classic Normal strength
gain against the frozen mission policy and the earlier material teacher. A
student trained on representative development games initially broke an existing
Scout-support regression. A cooperation guard preserves assigned support jobs
while retaining a reliable strength gain. This guarded model is now enabled for
Classic Normal. Inventory features and the capture-only ablation remain rejected.

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

## Cooperation guard and production adoption

The accepted version preserves the assigned cooperation actor's native quiet-move
scores. Learned corrections still apply to other quiet moves and to all captures.
This protects a support assignment that the cold future rollout cannot reliably
reconstruct, without disabling quiet corrections throughout the army.

Development scores 55.2% over 560 games. After freezing the executable and model,
fresh independent validation scores 54.0% over 1,400 games, with a paired 95%
interval of 51.8–56.2%. It avoids the same two diagnostic specialist losses and
passes the unchanged Scout-support tests. The decoy family remains weak at
46.5% (42.0–50.5%); the overall result does not establish improvement in that family.

A separate matched league check plays 700 games per policy against five frozen
opponents. Both the student and mission control score 70.07%. The complete-block
interval for their difference is -3.64 to +3.50 percentage points. Gains against
the adaptive opponent offset lower scores against the original and greedy
opponents. Capped games increase from three to thirteen. Adoption therefore rests
on the independently demonstrated mission-baseline gain, with no established
league-wide gain or claim about human strength.

The 31-node model occupies 186 bytes. Production enables it only for Classic
Normal; Easy, Hard and optional variants retain their mission scoring. The
tracker restarts cold after loading GAME.DAT, preserving the existing format.
An actual save/load check verifies that stale observer records are cleared.

The first banked integration exceeded main RAM by three bytes. Moving protected
random deployment and its work pool into bank 24 leaves 585 bytes before the
reserved 1 KB stack. Calls already in bank 24 use the random implementation
directly, avoiding nested gateway state. The tactical bank remains 8,147/8,192
bytes and the mission bank uses 7,512/8,192 bytes. All 180 banked deployment calls
match native layouts and RNG, including the direct Random-button path.

Eighty actual production turns match both native armies with accumulated history
and per-turn RNG. At least 996 stack-canary bytes remain untouched in these AI
calls; this is an observed guard measurement, not a mathematical stack bound.
Their maximum time is 33 frames. Another 100 cold positions match the frozen
candidate and actual X16 build, taking at most 39 frames (0.65 seconds), mean
23.07 frames. A separate 50-position Hard prototype check also matches native.

Production checks pass for 15,163 hidden-rank permutations, 3,836 Silent Defense
comparisons, disclosure bookkeeping, eight banked cooperation fixtures, difficulty
and legacy saves, game flow, demo, variant rules and distribution boot. All 34
browser runtime files match the built game, and its download matches the
distribution ZIP. The [production manifest](../ai-student-production/manifest.json)
retains the model binding, sources, programs, timing, stack, save/load and package
evidence. Optional-variant strength benchmarks remain the next required stage.

## Evidence and reproduction

The [initial checkpoint manifest](manifest.json) identifies its
[evidence archive](evidence-20261014.zip), captured before the cooperation guard.
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

The unguarded model's tactical test remains an expected rejection. Reproduce the
accepted candidate with `make native-student-coop-guard test-ai-student-coop-guard`.
`make all native check` builds and checks the adopted production configuration.
Variant strength remains outstanding.
