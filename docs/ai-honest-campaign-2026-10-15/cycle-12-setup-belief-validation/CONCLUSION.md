# Cycle 12: fresh validation does not confirm the setup-belief improvement

The frozen joint Flag/Bomb belief policy scored 29.11% against DOS, compared with Context at 28.01% and the Flag-row control at 28.80%. Its matched improvement over Context was +1.45 percentage points, with a prespecified 98.3333% bootstrap interval of [−1.15, +3.98]. This fresh validation does not establish an improvement. It also does not establish equivalence or rule out a modest benefit.

The three prespecified contrasts use 98.3333% intervals for a nominal 95% familywise interpretation. Each interval includes zero:

| Matched comparison | Score difference | 98.3333% interval | Complete side-swapped pairs |
| --- | ---: | ---: | ---: |
| Flag-row minus Context | +0.56 pp | [−1.97, +3.08] pp | 989 |
| Joint minus Context | +1.45 pp | [−1.15, +3.98] pp | 999 |
| Joint minus Flag-row | +0.58 pp | [−2.01, +3.12] pp | 995 |

These are 20,000 family-stratified paired bootstrap replicates. Each contrast omits a side-swapped pair if either policy has an engine error. Consequently, matched differences need not equal differences between the raw scored standings, and the three contrasts use slightly different retained cohorts.

Cycle 5's joint-versus-Context estimate was +4.0 points with an exploratory 95% interval [+0.2, +7.8]. That screening signal did not reproduce clearly in this larger fresh cohort. Joint also remains unproven against the simpler Flag-row prior, so these games do not establish a benefit from spatial Flag/Bomb coupling. No model or policy was tuned on this validation, and no policy is promoted from it.

Results vary by deployment family. Descriptive matched joint-minus-Context estimates range from −3.36 points on presets to +5.34 on broad-mixed. These subgroup observations were not separate validation targets and are not a basis for selecting or tuning a policy. Both sides received referee-owned deployments from seven stress families; this experiment does not measure strength against the original game's default Colonel deployment distribution.

All 6,300 attempted Classic games were replayed in Python and at every state in the native worker. The original DOS faults remain unscored: 31 Context, 41 Flag-row and 30 Joint, with all legal prefixes retained. Allowing each missing score to range independently from zero to one gives finite-cohort difference bounds of [−0.83, +2.60] points for Flag-row minus Context, [−0.38, +2.52] for Joint minus Context and [−1.50, +1.88] for Joint minus Flag-row. These are error-sensitivity bounds, not confidence intervals; none forces a positive effect.

The first analysis process failed after completing all games and three verified reports because its cached tournament module lacked a newly imported helper. Recovery reanalysed the existing files in a fresh process. No games were rerun, and all three tournament SHA256 values are identical before and after recovery. The failure log, recovery log and independent recovery proof are retained. `campaign_cycle.audit` passed; all frozen policy specifications exactly match Cycle 5, 11 existing checks passed and three Qt6 review captures are present. The fresh masterseed produced no repeated full family/move-seed/army assignment from Cycle 5. Production remains unchanged.
