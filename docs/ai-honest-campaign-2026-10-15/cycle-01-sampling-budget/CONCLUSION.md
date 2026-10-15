# Cycle 1: more sampled armies did not improve play

Four matched arms played 280 Classic games each against the unchanged DOS
Colonel. There were 1,120 attempts and 14 original DOS errors, retained unscored.

| Beliefs | 8 armies | 32 armies |
|---|---:|---:|
| Existing public-count/behavior model | 26.9% | 24.4% |
| Frozen learned independent model | 30.2% | 21.6% |

Increasing the existing model from eight to 32 armies changes matched score by
−2.2 percentage points (95% interval −7.5 to +3.1). Increasing the learned model
changes it by −8.4 points (−14.5 to −2.5). The explicit difference of those effects
is −7.3 points (−14.6 to 0.0). The learned model at eight armies remains
inconclusive against the original eight-army teacher: +3.2 points (−2.6 to +9.0).
Intervals are descriptive in this exploratory campaign; all contrasts are kept.

The hypothesis that simply increasing this sampling budget unlocks better
beliefs is unsupported. The learned 32-army variant regresses on this cohort.
More accurate Monte Carlo estimates need not help when the opponent model or
value estimates themselves are wrong. This experiment does not identify which
of those errors dominates.

Do not promote either 32-army variant, and do not spend the next cycle scaling
them to 128. Retain both immutable policies and evidence. Continue with cheap
variance control, strategic evaluation and better public-information models.
Production remains unchanged.
