# Richer procedural inference did not establish a playing-strength gain

The strategic idea was to model the original engine’s procedural deployments more faithfully, while retaining the same 80% mass on its eight fixed formations. A second control discarded the formations entirely and used only a back-row Flag prior. Better prediction alone was not treated as evidence of better play.

All four fixed policies played 1,000 fresh attempts against the original DOS engine, with its original army generator and both armies rotated across colors. No model was tuned on this cohort. All 4,000 attempts were replayed in Python and the native engine; 148 DOS errors remain preserved and unscored.

| Policy | W / D / L | Errors | Scored result |
|---|---:|---:|---:|
| student-template-flag-bomb-v1-normal | 270 / 215 / 485 | 30 | 38.92% |
| student-template-backrow-background-v1-normal | 272 / 232 / 467 | 29 | 39.96% |
| student-template-structured-background-v1-normal | 268 / 247 / 459 | 26 | 40.20% |
| student-backrow-only-v1-normal | 246 / 140 / 551 | 63 | 33.72% |

| Matched comparison | Paired change | 95% interval | Complete pairs | Missing-outcome effect bounds |
|---|---:|---:|---:|---:|
| student-template-backrow-background-v1-normal minus student-template-flag-bomb-v1-normal | +0.97 pp | [-0.43, +2.43] | 463/500 | [-1.95, +3.95] pp |
| student-template-structured-background-v1-normal minus student-template-backrow-background-v1-normal | +0.21 pp | [-1.23, +1.66] | 468/500 | [-2.55, +2.95] pp |
| student-backrow-only-v1-normal minus student-template-flag-bomb-v1-normal | -4.55 pp | [-8.57, -0.59] | 423/500 | [-9.15, +0.15] pp |
| student-template-structured-background-v1-normal minus student-template-flag-bomb-v1-normal | +1.24 pp | [-0.22, +2.69] | 465/500 | [-1.60, +4.00] pp |

Neither richer background established an improvement over the existing formation mixture, and the richer screen/Bomb structure did not establish an improvement over the simpler back-row background. The minimal prior lost 4.55 paired points to the formation mixture on complete pairs. Its 95% interval is negative, but the wider 98.3333% interval and finite missing-outcome bounds include zero. This four-contrast exploratory screen does not support a familywise significance claim or an unconditional regression claim.

Missing-outcome bounds assign every unscored attempt an arbitrary score from zero to one; they are finite-cohort sensitivity bounds, not confidence intervals. Every comparison’s bounds cross zero. The 98.3333% intervals in result.json do not control all four contrasts, as specified before play.

Retain the independently validated original formation model as the reference. Preserve the richer alternatives without promotion or tuning on these outcomes. This screen does not compare the minimal prior directly with plain native play: that fresh comparison, including the compact target implementation, is cycle 31. Honest-opponent generality is separately frozen as cycle 30. No CX16 readiness or human-general strength claim follows from these host-side games.

The complete campaign comparison is in [OVERVIEW.md](../OVERVIEW.md).
