# Reply-Aware Teacher v1 — 15 October 2026

This trial tests **Reply-Aware Teacher v1 / Normal**
(`teacher-replies-v1-normal`) against **Context Teacher v1 / Normal**
(`teacher-context-v1-normal`). **The candidate is rejected for promotion:** its
48.6% head-to-head development score fails the declared gate for independent
validation. The completed league has a positive but uncertain difference.
Production remains Guarded Student v1; no student was fitted.

## What changed

The [previous linked-scouting trial](../ai-linked-scouting-2026-10-15/README.md)
rewarded a probe when a nearby ally had a legal, rank-dependent attack. The
opponent often moved the target or captured that ally before it could act.

Context Teacher v1 already evaluates the current move, one opponent reply,
our next move and another opponent move. Its limitation for this trial is the
single predicted first reply. The new teacher evaluates up to **three plausible
first replies**, then follows the same policy for the remaining continuation:

```text
Each legal current move
    ├─ plausible opponent reply A → our move → opponent move
    ├─ plausible opponent reply B → our move → opponent move
    └─ plausible opponent reply C → our move → opponent move
```

The reply shortlist comes from the replying player's **masked view**, public
history, own ranks and policy scores. Only the top three moves within 32 score
points of the best qualify. Their fixed weights are 33 minus that score gap.
No hypothetical hidden outcome enters reply membership or weighting. The teacher
averages their continuation values, then averages across sampled hidden armies.

Both teachers use the same eight sampled worlds, four-ply horizon, guarded
student policy, strategic utility, full root context and bounded correction
blend. The same response model evaluates the existing counterfactual waiting
reference. Actual choices remain legal attacks or quiet moves; no pass move is
introduced. Scout cost remains in the native immediate score, and subsequent
losses, retreats and recaptures enter the simulated continuation.

This is a weighted response model. It still depends on the guarded policy's
ranking of plausible replies and on its later choices. It does not establish
that every dangerous reply or best continuation has been considered.

## Reviewing the eighteen Scout losses

[All 18 public roots](public-cases.jsonl) were reconstructed, including their
legitimate own starting armies, masked board, inventories and public histories.
The recorded future is diagnostic metadata and is excluded from the root
teacher inputs. The [review manifest](review.json) binds this corpus to the
previous trial. Representative public outcomes were inspected in the Qt6 desk:

- [Intended attacker removed](review-attacker-removed.png): after the Scout
  disclosed a Miner on g7, the opponent's Colonel captured the Captain on g8.
- [Target retreats](review-target-retreat.png): the disclosed Miner moves from
  i7 to the Scout's vacated h7 square.
- [Flag loss](review-flag-loss.png): a Scout attack at a9 is followed by the
  opposing General capturing the known-to-Blue Flag on a10.

These illustrate different response risks. A Scout loss is not automatically
a mistake: identifying a Bomb or superior rank can justify declining a later
attack. The goal is stronger play, not simply fewer probes.

The two frozen teachers were also run on all 18 roots with identical strategic
contexts and sampled-world RNG seeds. The candidate changes four decisions.
It selects the recorded probe in seven cases, versus six for Context Teacher.
These alternative choices do not establish better continuations. Full action
values and source bindings are retained in [the diagnostics](diagnostics.json).

## Does the reply model cover the observed responses?

A separate [coverage diagnostic](reply-coverage.json) starts **after the public
probe battle**, before applying the recorded opponent reply. It samples eight
worlds consistent with that new public information and obtains the reply
shortlist in each world. Only after prediction does it compare those shortlists
with the recorded response. This hindsight diagnosis never changes a root
decision, tournament, model, setting or promotion gate.

The single-policy choice includes the recorded reply in at least one sampled
world for **13 of 18 cases**. The expanded reply set covers **16 of 18**. Of the
144 sampled reply sets, 98 contain multiple moves. Thus the implementation
broadens the considered responses in these cases. Coverage means inclusion in
a sampled shortlist; it is not a calibrated probability that an opponent will
choose that move, or evidence of greater game strength.

The candidate uses **36,348 policy calls**, versus the control's **16,081**, in
the 18 root comparisons: about **2.26 times** as many. Calls include repeated
policy evaluation needed to restore branch-local goals correctly. This is a
diagnostic workload measurement, not a general timing or scaling guarantee.

## Frozen comparison and gates

The [plan](plan.json) freezes one candidate, five opponents, seven layout
families, four OpenMP workers and a 1,000-ply move limit. Development uses 140
head-to-head games against Context Teacher v1, followed by candidate/control
comparisons against Original, Planned, Missions, production Guarded Student and
Rollout Teacher v1. Each league matchup contains 84 games, giving 420 games per
policy and **980 games in 11 tournaments** overall.

Each pair uses common starting Red and Blue armies, then swaps the policies'
army assignments. Head-to-head and league seeds are 1710001 and 1711001. League
candidate/control runs share seeds and setups across all opponents. Confidence
intervals resample complete paired blocks within layout families; league blocks
retain all opponents and both sides together, with 10,000 bootstrap resamples.

Development requires at least 52% against Context Teacher, a nonnegative matched
league difference, more than 50% against production, and passed privacy/state
checks. The head-to-head score of **48.57%** fails that gate. Final validation
would require fresh head-to-head and league intervals wholly in the candidate's
favor, plus a production interval above 50%. No student fitting is authorized
within this trial, regardless of its outcome.

| Development comparison | Reply-Aware Teacher | Context Teacher control |
| --- | ---: | ---: |
| Direct head-to-head, 140 games | 48.57% | 51.43% |
| Matched league, 420 games per policy | 67.62% | 65.00% |

The head-to-head paired 95% interval is **41.43–55.71%**. The matched league
difference is **+2.62 percentage points**, block 95% interval **−3.81 to +8.57**.
Neither establishes a strength gain over Context Teacher, or a reliable decrease.

| League opponent | Reply-Aware Teacher | Context Teacher | Games per policy |
| --- | ---: | ---: | ---: |
| Original v1 | 80.95% | 80.36% | 84 |
| Planned v1 | 71.43% | 66.67% | 84 |
| Missions v1 / Normal | 67.86% | 64.29% | 84 |
| Production Guarded Student v1 | 63.10% | 58.33% | 84 |
| Rollout Teacher v1 / Normal | 54.76% | 55.36% | 84 |

The candidate's score against production has paired 95% interval **53.57–72.62%**.
Being stronger than the small production policy was already a property of the
existing desktop teacher; this is insufficient to establish a useful successor.
Per-family scores, endings, identities and source hashes are in
[the development report](development.json).

**No final validation or student fit was launched.** The reserved final seeds
1720001 and 1721001 remain unused, and no second design or score adjustment
followed these results. All 11 `.fmtour` files remain reviewable in the Qt6 desk.

The trial demonstrates broader reply coverage, at additional computation cost,
without a demonstrated improvement over the existing teacher. It does not
establish that response breadth alone explains the earlier Scout losses.

## Source, tests and reproduction

The [catalogue](../../ai/registry.json) preserves a distinct immutable name,
recipe, driver arguments and source archive. Reply branching is an opt-in native
teacher feature. Existing playing policies, model headers, X16 build flags and
deployment policies are unchanged.

Six frozen-source behavioral tests cover root-context transfer, concealed-rank
invariance, reply membership/weights from the mover's information, exact
single-reply parity with Context Teacher, reversed branch-order equivalence,
complete legal root actions, reproducibility and immediate Flag priority. The
legacy teacher/input suites and production checks pass. Logs are in
[`checks/`](checks/).

The initial reply-privacy fixture altered the replying player's own ranks,
changing its permitted view and yielding no comparable inputs. The corrected
fixture changes concealed ranks belonging to the root player and demands
identical replies when the opponent's information is identical. Its initial
failure log is retained; the AI design and score settings were not changed.

```sh
make desktop-build
build/desktop/feldmarschall-desk \
  docs/ai-reply-teacher-2026-10-15/tournaments/development-head/teacher-replies-v1-normal--teacher-context-v1-normal.fmtour
python3 tools/test_teacher_replies.py
python3 tools/audit_reply_teacher.py
```

The [completion audit](audit.json) reconstructs all 18 public cases, reproduces both teachers' diagnostic
decisions and post-probe reply sets, checks the frozen source/settings and
scheduled seeds, and legally replays every retained tournament with its embedded
source/runtime hashes. New experiments need new IDs, plans, seeds and output
directories. Existing completed files must be preserved.
