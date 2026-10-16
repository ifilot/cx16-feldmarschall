# Cycle 25: Fortress deployment gain validates against honest moves

The unchanged Fortress-only deployment improved over the validated mixture in
this fresh honest-opponent validation: **+7.000 percentage points, 95% interval
[+4.925, +9.075]**, with no errors. This reproduces the earlier honest-opponent
screening signal without tuning either formation or the native move policy.
It supports the fixed formation in this tested context; it does not establish
superiority against every opponent or change production automatically.

Both players used honest native moves. Our two policies differed only in own
deployment. The opponent used `student-guard-v1-normal` with its own army drawn
from the original DOS deployment population. Seed 2350001 supplied 1,000 matched,
side-swapped pairs per arm, 2,000 games each and 4,000 total. The plan, immutable
policies and sample size were frozen before these games. All attempts completed
and were independently replayed in Python and native workers; Qt6 review and
own/original-army setup provenance are preserved.

| Own deployment | Wins / draws / losses | Score | Errors |
| --- | ---: | ---: | ---: |
| Validated mixture | 961 / 88 / 951 | 50.25% | 0 |
| Fortress only | 1098 / 94 / 808 | 57.25% | 0 |

Scores count wins plus half of draws. These are **honest-opponent results, not DOS
strength scores**. Own and opponent deployment populations differ, so an absolute
50% score is not the prespecified fair-null benchmark. The matched Fortress-minus-
mixture contrast is the relevant comparison.

All 1,000 pairs are complete. The single primary contrast uses 20,000 whole-pair
bootstrap replicates: +7.000pp, 95% interval [+4.925, +9.075]. The additionally
reported 98.3333% interval is [+4.475, +9.550]pp. The 95% interval is primary for
this single prespecified validation contrast. Missing-score sensitivity bounds
equal the observed +7.000pp because no game is missing. Pair directions were
225 positive, 110 negative and 665 tied; that diagnostic is supplementary to
the paired mean-effect interval.

The result concerns using the existing Fortress consistently instead of mixing
three existing formations. It is separate from the rejected double-Bomb-shell
rearrangement. This experiment does not isolate which formation feature creates
the gain. The policy remains honest, cheap at setup, and unchanged in move search,
rank information, evaluation coefficients and RNG consumption.

The paired DOS validation in cycle 24 also favored Fortress on completed games
(+5.495pp, 95% interval [+3.785, +7.265]), but its 276 unscored errors leave
all-attempt bounds crossing zero. This clean honest result does not fill those
missing DOS outcomes or remove that limitation. Any promotion decision must
review both contexts, target correctness/cost and the preserved error evidence.
No formation was retuned on either validation cohort; existing production and
immutable IDs remain unchanged.
