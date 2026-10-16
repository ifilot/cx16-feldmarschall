# Cycle 32: the compact back-row prior loses strength against the honest reference

The compact native policy scored 43.04% against the honest guarded student, compared with 50.00% for the native control and 43.75% for the Python back-row prior. Its paired difference from control was −6.96 percentage points, with a 95% interval of [−10.63, −3.39] and a retained 98.3333% interval of [−11.52, −2.59]. This is evidence of a generality cost on these supplied armies, rather than a general improvement. The separate DOS validation does not remove this limitation.

Each arm played 560 Classic games: 40 side-swapped pairs in each of seven forced-army families, with identical physical armies and move seeds across arms. The native control and reference share movement behavior in this setting; their exact 50% score is a consistency check. Deployment ownership is not tested here. These families differ from the original DOS deployment population that motivated the prior.

| Policy | Wins / draws / losses | Score | Batch seconds |
|---|---:|---:|---:|
| Native control | 275 / 10 / 275 | 50.00% | 12.08 |
| Python back-row prior | 239 / 12 / 309 | 43.75% | 87.44 |
| Compact native prior | 238 / 6 / 316 | 43.04% | 11.01 |

The Python prior also underperformed control: −6.25 points, 95% interval [−9.91, −2.68], retained 98.3333% interval [−10.71, −1.88]. Compact minus Python was −0.71 points, with intervals [−2.59, +1.16] and [−2.95, +1.52], respectively. The latter comparison does not establish equivalence. The implementation bridge changes integer rounding and integration as well as execution cost, so any differences cannot be assigned only to rounding.

All 1,680 games completed without errors, and every comparison includes all 280 planned pairs. Missing-outcome bounds therefore collapse to the observed cohort differences; they are not confidence intervals. For compact minus control, pair directions were 59 positive, 99 negative and 122 tied; exact two-sided sign p=0.00183 is a direction diagnostic, not a mean-effect null test. The reported intervals describe this prespecified exploratory cohort and do not establish campaign-wide significance or justify promotion.

Batch timing includes different game lengths and concurrent load; it is not controlled per-decision timing. The compact target implementation has separate build and banked qualification evidence, whereas the Python comparison is a desktop driver. No model or source was changed or tuned on these games. All games pass Python and native every-state replay, with three Qt captures and frozen policy/source identities. Existing artwork and orientation are retained. Production behavior remains unchanged.
