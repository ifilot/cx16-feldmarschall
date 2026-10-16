# Cycle 27: deployment and formation beliefs can combine

The frozen Fortress-plus-template candidate scored highest on this exploratory cohort: 41.88%, compared with 37.50% for template beliefs with the existing validated deployment, 25.81% for Fortress alone and 20.77% for the original native policy/deployment. Adding Fortress to the template policy improved complete-pair score by +4.28 percentage points (95% interval [+0.53, +8.16]), but its wider 99% interval [-0.67, +9.36] includes zero. The additional deployment benefit remains suggestive; no combined policy is promoted. Fresh independent single-contrast validation is queued as C41.

The 2×2 design separates own deployment from honest source-informed enemy beliefs. Each of four immutable arms attempted 400 Classic games on 200 matched pairs, with the same original DOS enemy armies and move seeds. Own setups are the declared treatment. Both armies rotate 180 degrees across sides, preserving the exact original DOS-local formation. Source snapshots, models, prior likelihoods and native movement rules were frozen before any games; no coefficient or policy was tuned on this cohort.

| Arm | W / D / L | Unscored errors | Score |
|---|---:|---:|---:|---:|
| student-validated-deployment-v1-normal | 63 / 31 / 284 | 22 | 20.77% |
| student-fortress-deployment-v1-normal | 80 / 31 / 259 | 30 | 25.81% |
| student-template-flag-bomb-v1-normal | 112 / 67 / 209 | 12 | 37.50% |
| student-fortress-template-flag-bomb-v1-normal | 124 / 82 / 188 | 6 | 41.88% |

| Planned contrast | Complete pairs | Effect (points) | 95% interval | 99% interval |
|---|---:|---:|---:|---:|
| student-fortress-template-flag-bomb-v1-normal minus student-template-flag-bomb-v1-normal | 187 | +4.28 | [+0.53, +8.16] | [-0.67, +9.36] |
| student-fortress-template-flag-bomb-v1-normal minus student-fortress-deployment-v1-normal | 165 | +17.58 | [+11.52, +23.64] | [+9.55, +25.61] |
| student-fortress-template-flag-bomb-v1-normal minus student-validated-deployment-v1-normal | 173 | +23.27 | [+17.49, +28.90] | [+15.75, +30.78] |
| student-template-flag-bomb-v1-normal minus student-validated-deployment-v1-normal | 169 | +18.49 | [+12.28, +24.85] | [+10.36, +26.63] |
| student-fortress-deployment-v1-normal minus student-validated-deployment-v1-normal | 166 | +5.72 | [+2.11, +9.64] | [+0.90, +10.99] |

The preregistered five exploratory contrasts requested 95% and 99% widths. The shared harness also retains 98.3333% intervals; those do not control multiplicity across all five comparisons. The supplemental paired-99-intervals.json uses the same 20,000 bootstrap draws and seed, exactly reproduces every stored 95% interval, and supplies the requested 99% widths. The combination-minus-template 98.3333% interval also includes zero. No positive statistical interaction or general additive law is established by these pairwise contrasts.

All 70 original DOS error prefixes are retained and excluded from official scores. Assigning each missing outcome any score in [0,1] gives finite-cohort effect bounds of [+1.88, +6.38] points for combination minus template, [+9.88, +18.88] for combination minus Fortress, and [+16.12, +23.12] for combination minus original. Template minus original remains [+11.25, +19.75]; Fortress minus original spans [-1.25, +11.75]. These are missing-outcome bounds for this cohort, not confidence intervals.

Recorded batch execution was 275.50 seconds for original, 349.86 for Fortress, 519.10 for template and 531.04 for their combination. The combined arm used about 2.3% more wall time than template alone in this run; game lengths and concurrent load affect totals, so this is not an isolated per-decision cost. Scores remain below 50% against the DOS engine.

Template inference consumes only public events and the known source prior, never the actual hidden army or private setup seed. Its 20% uniform background approximates the actual procedural branch. The DOS opponent retains its registered information advantage. DOS enemy deployment is produced by the original unchanged level3 machine code, with frozen setup assets/runtime/requests reproduced by independent audits. Move RNG is independently reseeded rather than continued from the original interactive game’s post-deployment state. These opponent/distribution and RNG boundaries limit generalization.

All 1,600 games pass Python/native every-state replay with four Qt captures, frozen owner/original-generator setup audits and exact registered rebuilds. The desktop belief driver does not establish a ready CX16 port: the earlier direct interface overflows the AI bank, while a separate experimental bank25 target prototype is under development and has not been qualified or registered. Production remains unchanged. No source, model, deployment coefficient or immutable ID is changed by this screen.
