# Classic AI development cycle — 15 October 2026

The production game continues to use **Guarded Student v1 / Normal**
(`student-guard-v1-normal`). This cycle tested a priority hierarchy, mission
reconsideration, a desktop teacher that retains strategic context, and one
compact student fit. None of the new game-sized candidates earned adoption.
The context-preserving teacher passes the declared strength gates as a desktop
reference. It has no established strength advantage over the previous rollout
teacher. All five stages are complete, including retained rejected experiments.

## Starting point and comparison league

Our original AI mostly chose moves through local material, danger and forward
movement scores. Planned v1 added persistent objectives and routes. Missions v1
added cooperation: a Miner can approach a suspected fortification while another
piece clears or investigates its route. The current Guarded Student adds a small
learned score correction while protecting the assigned support actor's quiet
moves. These versions remain independently rebuildable through the
[catalogue](../../ai/README.md).

The [frozen plan](plan.json) limited this cycle to Classic Normal, one design per
stage and one student fit. A five-policy round robin supplied the starting
comparison: ten tournaments, 420 games, seven deployment families, paired army
assignments. Each policy played 168 games:

| Frozen policy | Score in the starting league |
| --- | ---: |
| Original v1 | 26.5% |
| Planned v1 | 44.6% |
| Missions v1 / Normal | 55.1% |
| Guarded Student v1 / Normal | 57.1% |
| Rollout Teacher v1 / Normal | 66.7% |

This small league identifies useful opponents and review material. It does not
establish every difference in that table or measure human playing strength.
The [baseline report](baseline.json) links the ten portable tournaments.

## What the match review exposed

The [review](review.json) retains 18 positions from production losses or capped
games, with [public inputs and histories](public-cases.jsonl). Six illustrate
known losing captures, six repeated actions, and six decisions near the end of
a match. The last category includes short defeats; it does not mean six late
endgames. Outcomes selected cases but never entered the AI's input features.

Two examples were inspected in the compiled Qt6 viewer:

- In the [decoy example](decoy-scout-loss.png), match 30 of Planned v1 versus
  Guarded Student, the production Red Scout attacks g4–i4 at ply 104. Its target
  is an already disclosed Captain. The attack loses the Scout without learning
  a new rank. This suggests a conflict between a positional objective and the
  cost of executing it.
- In the [quiet example](quiet-stall.png), match 33 of Original v1 versus
  Guarded Student reaches the 1,000-ply cap. Its last 433 plies contain no battle;
  Blue uses only ten distinct moves in its last forty decisions. This motivates
  testing whether a stalled plan should be reconsidered.

All 18 have an optimistic route under the public structural check. That excludes
one simple permanent-obstruction explanation, but does not prove a winnable
position, a safe route, or a superior alternative move. Forced-history diagnostics
condition each candidate on the recorded public actions; they are not
counterfactual game results or exact reproductions of all historic policy state.

## Experiments and decisions

Scores count a win as one point and a draw as half. Every development matchup
contains 112 games, with the same starting armies used for swapped policy sides.
A candidate needed at least 52% and no new tactical failure to proceed to final
validation. Final strength acceptance required both a predecessor score interval
above 50% and a matched league difference interval above zero.

| Candidate | Idea | Development versus production | Decision |
| --- | --- | ---: | --- |
| `priorities-v1-normal` | Rank obligations before ordinary move scores | 12.1% | Reject: poor strength and Scout-support regression |
| `plans-v2-normal` | Remember job/actor progress; reconsider a stalled sector | 54.0% | Reject after independent strength and X16 checks |
| `teacher-context-v1-normal` | Preserve strategic state in masked-policy rollouts | 71.4% | Accept as a desktop reference; no demonstrated gain over the previous teacher |
| `student-context-v2-normal` | One compact full/cold-history fit from that teacher | 42.9% | Reject at development gate |

**Priority hierarchy.** Winning, confirmed defense, safe disclosed captures,
escape, cooperation and ordinary progress received ordered classes. This
particular hierarchy became too conservative: it refused the exposed Scout move
needed by an existing cooperation fixture in all 32 Normal seeds. It also
performed badly in games. The result rejects this design, rather than proving
that every separation of tactics and strategy is harmful.

**Mission reconsideration.** Each army retained its job, participant's public
identity and best route distance. Eight unproductive decisions cooled the target
area for sixteen decisions and allowed Scout-led investigation of another rear
blocker. Public evidence and a disclosed Flag retained priority. The candidate
passed the existing tactical and information-fairness tests.

Its fresh 1,400-game validation scored **50.68%**, paired 95% interval
**49.29–52.04%**. In the four-opponent matched league it scored 54.06% against
production's 54.33%; the difference was **−0.27 percentage points**, block 95%
interval **−1.70 to +1.21**. There is no established strength gain. An isolated
X16 build also overflowed the mission bank by 536 bytes. See
[the complete validation](plans-validation.json).

**Desktop teacher.** The previous rollout teacher started future policy caches
cold. The new teacher uses the guarded student for future decisions, copies the
root observer's permitted goals, mission and quiet-history state before ranking,
and updates public memory during simulated play. Each simulated mover still
receives a masked opposing army. Search remains eight sampled worlds and four
plies; this is a combined update, not a full information-set tree search.

Its independent predecessor tournament finished at **62.39% over 1,400 games**,
paired 95% interval **60.21–64.54%**. In the matched league, each policy played
1,120 games. The new teacher scored **68.44%**, versus production's **55.09%**:
a difference of **+13.35 percentage points**, block 95% interval **+9.73 to +16.96**.
It passes both declared strength gates. The same cohort breaks down as follows:

| Opponent | Context teacher | Production control | Games per policy |
| --- | ---: | ---: | ---: |
| Original v1 | 80.9% | 70.2% | 280 |
| Planned v1 | 72.0% | 59.5% | 280 |
| Missions v1 / Normal | 70.9% | 53.8% | 280 |
| Rollout Teacher v1 / Normal | 50.0% | 37.0% | 280 |

The last row is 139 wins, 139 losses and two draws for the new teacher: there is
no demonstrated strength gain over the previous teacher. Its acceptance is as
an additional desktop reference with verified context transfer, not as an X16
replacement or a proven stronger successor to Rollout Teacher v1. See
[the final validation](teacher-validation.json).

A separate 112-game
comparison with an otherwise identical cold-root control scored **52.23%**,
interval **48.66–56.25%**. Behavioral tests verify context transfer and concealed
rank invariance, but this sample does not establish that root context alone
improves playing strength. See [the ablation](teacher-context-ablation.json).

**Compact student.** Training used only teacher-development games, never final
validation. Deterministic sampling by family, phase and army supplied 320 public
positions; shortages were retained. Each position supplied full and cold history,
producing 15,508 move labels and 506,032 teacher nodes. Related source family/seed
groups stayed together: 40 training groups and 10 held-out groups. Since the
teacher corrects the existing student, replacement targets include the existing
model correction as well as the new teacher delta.

The single depth-four fit produced **27 nodes / 162 bytes**. Held-out mean
absolute error was 11.73, versus 11.18 for zero correction. Its 42.9% development
score, interval 36.6–48.7%, failed the gate; no final student validation or second
fit followed. It passed tactical and fairness regressions and changed five of
the 18 diagnostic decisions, avoiding the Scout loss illustrated above. That
local improvement did not translate into stronger overall play. The
[model](student-model/model.json) and compressed
[inputs, labels and fit](student-model/training-evidence.zip) are retained.

The rejected student fits an isolated X16 build. One hundred cold positions and
80 real banked turns match native decisions with no mismatches. The latter cover
both armies, accumulated history and per-turn RNG. Maximum observed times were
34 and 27 frames respectively; at least 996 stack-canary bytes remained untouched
in the banked sample. These establish hardware feasibility for this sample,
not strength or production adoption. Production's model was left unchanged.
The [hardware evidence archive](checks/student-runtime-evidence.zip) retains the
actual programs, source, map, symbols, build logs and decision report, bound by
the recorded source and executable hashes.

## Reproducibility and verification

Every tested policy has a distinct immutable catalogue entry, source archive and
build recipe. Each `.fmtour` embeds source/runtime provenance, initial armies and
compressed moves. Development and final validation use separate predeclared
seeds. The four-opponent final league uses matched candidate/control deployments
and seeds. Confidence intervals use 10,000 bootstrap resamples of complete paired
blocks within each layout family; league blocks retain all opponents and both
sides together.

Two administrative corrections are explicit: the unbuildable initial
`plans-v1-normal` snapshot is preserved in [the build-failure record](plan-build-failure.json),
and the corrected build is v2. Registration now compiles a policy before making
it selectable. The student's frozen description mistakenly says 31 nodes; its
actual model has 27, as recorded in [the metadata erratum](metadata-errata.json).

Existing production regression, disclosure/fairness, compiled desktop, tournament
storage and legacy teacher checks pass. A separate comparison against the frozen
production executable matches **3,901 decisions exactly**. Full runtime adoption
checks for saves and distribution are required for promotion; no game-sized
candidate reached that stage in this cycle. Logs and hardware reports are in
[`checks/`](checks/).

Open a retained tournament directly:

```sh
make desktop-build
build/desktop/feldmarschall-desk \
  docs/ai-cycle-2026-10-15/tournaments/plans-validation/plans-v2-normal--student-guard-v1-normal.fmtour
```

Recompute the [completion audit](audit.json):

```sh
python3 tools/audit_ai_cycle_20261015.py
```

The cycle runner (`tools/ai_cycle.py`) reuses completed files after checking their
identity and configuration, and refuses incomplete existing runs. Reproducing a
new strength experiment requires a separate destination/plan and fresh seeds;
do not overwrite these files. The training script deliberately refuses to reuse
the existing model directory.

The audit verifies **33 complete tournaments / 8,260 games**, including every
recorded move, terminal result, paired setup and embedded source/runtime hash.
It reconstructs the 18 review cases and all 320 training inputs, reproduces
sampled labels at three history lengths, refits the exact model, reruns all
forced-history comparisons, and checks the retained hardware artifacts.

| Requested stage | Retained evidence | Outcome |
| --- | --- | --- |
| Comparison league | [Baseline](baseline.json), ten `.fmtour` files | Complete |
| Public failure review in the GUI | [Review](review.json), 18 cases, two screenshots | Complete |
| Explicit priorities | [Development](priorities-development.json), tactical failure log | Tested and rejected |
| Mission selection/reconsideration | [Validation](plans-validation.json), focused tests, X16 build log | Tested and rejected |
| Context-preserving teacher and one compact student | [Teacher validation](teacher-validation.json), [ablation](teacher-context-ablation.json), [student development](student-development.json), model and hardware evidence | Desktop reference accepted; student rejected |

The strategic lesson is that neither stricter move classes nor a simple
stall timeout solves the observed coordination problem. The desktop search has
more promise; fitting its score corrections into a small model remains an
unresolved learning problem. This cycle stops at its declared experiments.
