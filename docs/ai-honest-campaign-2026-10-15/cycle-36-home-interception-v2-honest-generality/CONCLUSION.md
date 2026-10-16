# Cycle 36: home interception changes too few outcomes to establish a gain

The corrected home-interceptor v2 produced a small positive score difference
against an honest opponent, but this screen does not establish a general strength
gain. Its paired effect was **+0.268 percentage points, 95% interval [0, +0.714]**.
Only two of 280 matched pairs had a nonzero aggregate score difference; both were
positive. The other 278 pairs tied in aggregate score. Such sparse differences
make the bootstrap interval especially limited; observing no negative pair is not
a guarantee of safety or future improvement.

Both arms played honest `student-guard-v1-normal` moves under Classic rules. The
same seven referee deployment families, seed and side-swapped pairs were shared
across the baseline opening-inference policy and its home-interceptor v2 variant.
All 1,120 attempts completed with zero errors and were independently replayed in
Python and native workers. Qt6 reviews, frozen recipes and qualification evidence
are preserved. These are honest-opponent results, not additional DOS scores.

| Policy | Wins / draws / losses | Score | Errors |
| --- | ---: | ---: | ---: |
| Template Flag/Bomb baseline | 283 / 11 / 266 | 51.518% | 0 |
| Corrected home interceptor v2 | 284 / 12 / 264 | 51.786% | 0 |

The primary single contrast uses all 280 matched pairs, with 40 pairs per family
and 20,000 whole-pair bootstrap replicates. Its additionally reported 98.3333%
interval is [0, +0.804]pp. Missing-score bounds equal the observed +0.268pp because
there are no errors. The two positive and zero negative non-tied pairs give a
sign diagnostic of 0.5; this is supplementary and does not prove a mean gain.
No policy, coefficient or sample size was tuned on these outcomes.

The idea is to preserve time for a capable home defender to intercept an already
disclosed enemy Miner instead of accepting a quiet schedule that is too late.
The mechanism checks other pieces as stationary and does not certify global
safety against hidden threats, coordinated future enemies or an offensive Flag
race. The observed score difference alone does not identify which interventions
mattered. The independent DOS screen is a separate context and must be reviewed
separately before deciding whether a larger fresh validation is warranted.

Version 1 was rejected during preflight after a shuttle-reset counterexample;
it has no strength result. This cohort tested the new immutable v2 policy only.
The original stale v1 contrast reference in the v2 plan was corrected through an
explicit preserved pre-run revision before any games, without changing policy IDs
or source archives. Original freeze records remain under `plan-revisions/v1`.

This is an exploratory desktop strategic prototype, with no CX16 fit claim.
The result does not justify promotion. Production and all frozen policies remain
unchanged; retain both the rejected preflight version and the v2 evidence.
