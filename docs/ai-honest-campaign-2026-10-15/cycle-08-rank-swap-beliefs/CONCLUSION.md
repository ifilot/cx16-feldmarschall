# Cycle 8: rank-swap posterior rejuvenation did not improve play

Four sweeps of count-preserving rank-swap Metropolis updates did not improve the eight-world teacher on this screening cohort. The swap policy scored 28.49%, compared with 31.03% for weighted calibrated beliefs, 31.58% for the unweighted proposal control and 29.67% for the context teacher. Every planned paired confidence interval includes zero; the observed swap effects are unfavorable, and no policy is promoted.

The strategic hypothesis was to reduce noise from importance weights in a batch of only eight hidden worlds. The zero-sweep control averages equal-weight draws from the learned sequential proposal; the four-sweep candidate then rejuvenates independent chains with rank swaps that preserve public inventory and history constraints. Both retain eight native rollouts at depth 4 and the same context/strategic correction. Finite rejuvenation is approximate posterior sampling, and equal weighting alone does not establish exact posterior draws. No actual hidden enemy ranks enter these policies.

Each policy attempted 560 Classic games on the same armies and move seeds across seven stress families. These forced-army families are not the original DOS deployment distribution.

| Policy | W / D / L | Unscored errors | Score |
|---|---:|---:|---:|---:|
| teacher-context-v1-normal | 159 / 6 / 381 | 14 | 29.67% |
| teacher-calibrated-beliefs-v1-normal | 167 / 8 / 376 | 9 | 31.03% |
| teacher-unweighted-beliefs-v1-normal | 171 / 6 / 374 | 9 | 31.58% |
| teacher-swap-beliefs-v1-normal | 153 / 8 / 390 | 9 | 28.49% |

| Planned contrast | Complete pairs | Effect (points) | 95% interval | 98.3333% interval |
|---|---:|---:|---:|---:|
| teacher-swap-beliefs-v1-normal minus teacher-calibrated-beliefs-v1-normal | 265 | -2.45 | [-6.60, +1.70] | [-7.45, +2.64] |
| teacher-swap-beliefs-v1-normal minus teacher-unweighted-beliefs-v1-normal | 266 | -3.38 | [-7.42, +0.66] | [-8.27, +1.69] |
| teacher-unweighted-beliefs-v1-normal minus teacher-calibrated-beliefs-v1-normal | 264 | +0.38 | [-3.79, +4.55] | [-4.73, +5.59] |
| teacher-swap-beliefs-v1-normal minus teacher-context-v1-normal | 260 | -0.67 | [-4.62, +3.27] | [-5.58, +4.23] |

These are exploratory paired bootstrap intervals. The 98.3333% intervals do not control multiplicity across the four contrasts, and no familywise strength claim is made. Complete-pair direction diagnostics likewise provide no strong signal (all exact two-sided sign p values exceed 0.18; those diagnostics test directions rather than a mean-effect null).

All 41 original DOS error prefixes are preserved and excluded from official scores. Allowing every error game an arbitrary unknown score in [0,1] bounds the finite-cohort swap-minus-calibrated effect at [-4.11, -0.89] points and swap-minus-unweighted at [-4.64, -1.43]. Swap-minus-context remains [-3.39, +0.71], and unweighted-minus-calibrated [-1.07, +2.14]. These are missing-outcome bounds for this cohort, not confidence intervals or generalization claims.

Recorded batch execution was 337.78 seconds for context, 455.40 for calibrated, 388.76 for unweighted and 496.59 for swap beliefs. Swap therefore used about 28% more batch wall time than unweighted draws while adding no rollout worlds; game lengths and concurrent load affect those totals. The finite-sample and mixing limitations remain, but this experiment supplies no reason to adopt the extra computation.

All 2,240 games pass Python and native every-state replay, with Qt captures and exact frozen runtime rebuilds preserved. Source snapshots, model files, registered IDs and production behavior remain unchanged. This candidate is retained as a negative screening result rather than promoted or tuned on this cohort.
