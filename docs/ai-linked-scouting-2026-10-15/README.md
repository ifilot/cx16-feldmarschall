# Linked scouting experiment — 15 October 2026

**Linked Scouting v1 / Normal is rejected for promotion.** It scored 51.1%
against production in development and did not improve the matched opponent
league. Production remains **Guarded Student v1 / Normal**. The named candidate
and all nine tournaments remain selectable/reviewable through the Qt6 desk.

## Starting behavior and the proposed improvement

Production already knows public ranks and movement history, chooses persistent
objectives, and coordinates Scouts with Miners. It also gives inexpensive pieces
a fixed information bonus for attacking a concealed enemy. That bonus does not
ask whether the army can use the discovery. The guarded learned model can still
choose Scout losses against already disclosed pieces.

An [earlier experiment](../ai-strategy-research.md) estimated information value
from a friendly piece's proximity. It failed its strength tests; proximity could
include pieces separated by lakes or blockers. This experiment therefore asked
a narrower question: **does a Scout help when another friendly piece has a legal
attack whose value depends on learning the target's rank?**

The [frozen plan](plan.json) allowed one design and no new teacher or student fit.
The candidate is `linked-scouting-v1-normal`, with its own immutable source
archive and production model in the [catalogue](../../ai/registry.json).
`AI_LINKED_SCOUTING` enables its changes only for Classic Normal:

1. A different friendly non-Scout must have a currently legal attack on the
   concealed target. Lakes, intervening pieces and two-square restrictions matter.
2. Public remaining-rank counts and movement restrictions estimate the value of
   choosing attack or abstention after disclosure. Ranks where the Scout wins
   or exchanges receive no information credit: there is no surviving target to
   investigate further.
3. Credit must cover the Scout's material value and is capped. It replaces the
   Scout's fixed probe bonus and also guides its objective selection. Other
   inexpensive ranks retain their existing scoring; cooperation remains intact.

For example, a General facing one possible Marshal and two possible Colonels
has a blind immediate combat payoff of zero under those counts. Disclosure
lets it avoid the Marshal and attack a Colonel: the bounded information estimate
is 66 material points, versus a Scout cost of 10. This is an opportunity estimate,
not a guaranteed gain. The opponent gets a turn, and the capture may expose the
General to another piece. No future action is forced or reserved by this design.

## Public match review

The [public review](review.json) reconstructs opportunities in all 18 retained
failure positions from the previous cycle. Three were examined in the Qt6 GUI:

- [Decoy / known Scout loss](review-decoy.png): production attacks g4–i4 with
  a Scout against an already disclosed Captain. This buys no new rank information.
- [Another known Scout loss](review-scout-loss.png): h4–j4 attacks a disclosed
  Captain in an unguarded-layout capped game.
- [A conditional attack](review-opportunity.png): c3–c2 has a rank-dependent
  follow-up value under the new criterion, but no Scout can probe it immediately.

Only the last of the 18 positions has a valued opportunity under this strict
definition. None has an immediately available Scout probe of that opportunity.
This does not prove information is useless in those positions; it limits the
mechanism's expected direct effect there. All 18 forced-history decisions
remain unchanged in [the diagnostics](diagnostics/summary.json).

## Development tests and results

The candidate was frozen before strength games. The OpenMP worker used four
workers, seven layout families and swapped policy sides with common starting
armies. The head-to-head used seed 1610001 and 20 pairs per family: 280 games.
The matched league used seed 1611001 and ten pairs per family against each of
four preserved opponents. Candidate and production each played 560 league games.
The complete experiment therefore contains **1,400 games in nine `.fmtour` files**.

| Development comparison | Linked Scouting | Production control |
| --- | ---: | ---: |
| Direct head-to-head, 280 games | 51.07% | 48.93% |
| Matched league, 560 games per policy | 56.07% | 58.04% |

The head-to-head paired 95% interval is **46.96–55.18%**. The matched league
difference is **−1.96 percentage points**, block 95% interval **−4.91 to +0.98**.
These do not establish a strength improvement or a reliable strength decrease.

| League opponent | Linked Scouting | Production | Games per policy |
| --- | ---: | ---: | ---: |
| Original v1 | 76.07% | 76.07% | 140 |
| Planned v1 | 53.57% | 56.07% | 140 |
| Missions v1 / Normal | 51.79% | 54.29% | 140 |
| Rollout Teacher v1 / Normal | 42.86% | 45.71% | 140 |

The development gate required at least 52% head-to-head, a nonnegative matched
league difference, and unchanged tactical/fairness tests. Both strength
conditions fail. **No independent validation games, second candidate or fit were
launched.** The fresh validation seeds remain unused. See the complete
[development report](development.json).

Intervals use 10,000 bootstrap resamples of complete side-swapped pairs within
layout families. League blocks retain all opponents, both sides and matched
controls together. These are development results against the fixed Classic
distribution, not human-strength estimates.

## Did the intended behavior occur?

[Activity analysis](activity.json) reconstructs public opportunities at the
actual Scout attacks and follows their public outcomes. Each policy has 840
appearances across head-to-head and league games. The policies produced different
traces in 234 of 560 matched league games; every first divergence involves a
Scout choice. The implementation therefore did change play.

| Observed behavior | Linked Scouting | Production |
| --- | ---: | ---: |
| Scout attacks on concealed pieces | 2,338 | 2,539 |
| Such attacks with a valued follow-up | 21 | 1 |
| Losing Scout attacks on already disclosed pieces | 61 | 50 |

The desired opportunities remained rare: fewer than 1% of the candidate's
concealed Scout attacks qualified. Most Scout attacks still arose from other
scores and objectives. There is no descriptive reduction in the disclosed-loss
count; these counts alone do not establish a causal difference or that every
such sacrifice was mistaken.

Eighteen of the 21 valued probes lost the Scout. On the next own turn, only
seven still had a legal credited follow-up. Nine defenders had left the target
square, four cases lost all credited beneficiaries, and one game ended before
another own turn; the first two categories overlap. Five of the seven remaining
targets were unfavorable immediate battles, and the AI declined them. Two were
winning immediate battles, but the AI selected other moves:

- [Head-to-head, match 24, ply 31](followup-not-taken-head.png): a Scout disclosed
  the Miner on b3, with a Major on a3. The next move develops another Scout.
- [Original v1 matchup, match 45, ply 32](followup-not-taken-league.png): the
  Captain on a8 could beat the disclosed Miner on b8, but moves to a9 instead.

Winning that immediate combat does not mean the capture is safe or preferable.
The surrounding concealed pieces, recapture risk and other objectives still
affect the evaluator. These examples do not justify forcing either capture.

The useful finding is that **a legal rank-dependent attack is too weak a basis
for valuing an information mission**. Opportunities often disappear during the
opponent's response, and credit does not ensure a safe, worthwhile continuation.
A future strategic experiment should consider that response and continuation;
increasing the information bonus or forcing a follow-up is not supported by
these results. No such second experiment was attempted here.

## Verification and reproduction

Focused tests cover the exact conditional value on both armies, unavailable
follow-ups, known ranks, unaffordable information, movement exclusions and
different actions after favorable/unfavorable disclosures. The unchanged
Scout/Miner cooperation fixtures pass, along with **15,163 hidden-rank
permutation decisions** and **3,836 Silent Defense inventory comparisons**.
Variant checks are regressions; strength research remains Classic only.

`make all native check` passes. The default production executable matches the
frozen production policy on **3,901 decisions**, including both armies' goals
and histories. The model and default build flags remain unchanged. X16
feasibility and adoption checks were not attempted for this rejected candidate.
Logs are retained in [`checks/`](checks/).
The [frozen-source test bundle](checks/frozen-tactics.zip) separately preserves
the test source, executable, command, compiler identity and successful log. That
suite was also compiled against the immutable candidate archive with every
candidate define enabled, plus the test interface.

```sh
make desktop-build
build/desktop/feldmarschall-desk \
  docs/ai-linked-scouting-2026-10-15/tournaments/development-head/linked-scouting-v1-normal--student-guard-v1-normal.fmtour
make test-ai-linked-scouting
python3 tools/audit_linked_scouting.py
```

The [completion audit](audit.json) replays every saved game, verifies participant
sources/runtime hashes, planned seeds, common setups and paired assignments,
recomputes the reports and activity analysis, and reruns the 18 forced histories.
The runner can reuse completed files after identity/configuration checks; it
refuses incomplete existing files. New strength claims need a new plan, output
directory, candidate ID and seeds. Preserve these rejected results.
