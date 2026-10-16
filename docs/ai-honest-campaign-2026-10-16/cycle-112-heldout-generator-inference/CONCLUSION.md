# Held-out generators: no established inference gain against Missions

The unchanged DOS source-inference champion scored **82.42%** against honest
Missions on the reserved generator-family cohort, versus **86.20%** for native
Fortress without that inference bridge. Its paired difference was **−3.78
percentage points**, with the prespecified 95% interval **[−7.68, +0.13]**.
This independent validation establishes **no generalization gain**; it also
does not establish a stable regression or equivalence. All **768 attempts**
completed without engine errors.

The exact policy versions and complete comparison plan were frozen before any
play. Each arm faced the same 192 opponent Army B records: 32 per previously
unplayed generator family, starting at offset zero. Both chose their unchanged
Fortress army; all initial armies and move seeds matched across arms. Army A
was unused. This tests transfer to these synthetic deployment families against
one fixed honest opponent, rather than human play or DOS strength. Absolute
50% is not the neutral comparison point for these asymmetric deployments.

| Opponent family | Native Fortress | Source inference | Difference |
|---|---:|---:|---:|
| Interior shell | 85.94% | 78.13% | −7.81 points |
| Flank Flag | 89.84% | 85.16% | −4.69 points |
| Double decoy | 90.63% | 93.75% | +3.13 points |
| Front fence | 84.38% | 78.13% | −6.25 points |
| Mobile squads | 86.72% | 84.38% | −2.34 points |
| Lane vanguard | 79.69% | 75.00% | −4.69 points |

All six family results and their uncertainty remain in `result.json`; no family
was selected for tuning or sample extension. Paired scores improved 20 times,
worsened 31 times and tied 141 times. The [trajectory diagnostic](divergence.json)
finds 351 changed complete sequences out of 384, with every first difference by
the candidate at an identical preceding position. Of those changed sequences,
287 retained their outcomes. Later differences are correlated consequences,
not additional independent interventions.

This contrast evaluates the **complete frozen inference bridge**: its source
templates, public count/movement conditioning, uniform background and numerical
interface. It does not isolate a causal benefit or harm of template correlations
alone. In particular, the background can still change native expectations after
all source templates have been eliminated. A narrower causal ablation would
require another prospectively specified policy and suitable fresh evidence.

Cycle 113 was separately predeclared and frozen before this complete result,
using another honest opponent and disjoint layouts. It is a secondary robustness
endpoint, not an arm to pool with these results or a DOS substitute. The usage
ledger records the consumed B layouts. These families are now exposed; remaining
layouts cannot restore an unseen-family claim for a policy tuned from this
outcome. No policy, prior, likelihood or stopping rule was changed.

The unchanged corpus and selector source are embedded in every saved tournament.
Full Python/native replay, frozen own-setup reproduction, artifact integrity and
Qt6 review are retained. No promotion follows from this study, and no honest-AI
ceiling has been established.
