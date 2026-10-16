# Cycle14: exact-contact gain did not validate

The fresh fixed-size validation did not establish that the frozen native
exact-contact policy improves over the native guard. The paired score gain was
+0.37 percentage points,95% interval [−1.62,+2.36]. The earlier exploratory gain
of about+3.3 points was not reproduced at comparable magnitude. Keep the rejected
strength hypothesis and its correct probability calculation as separate findings;
no promotion or retuning follows from this result.

Both honest native policies played the original DOS move engine under Classic
rules, using the same seven referee deployment families, seed2220001 and150
side-swapped pairs per family. Each arm attempted2100 games; all4200 attempts,
including error prefixes, were preserved and independently replayed in Python and
native workers. Two Qt6 reviews and the frozen policy/plan/check audit passed.
No policy source, model or coefficient changed on this validation cohort.

| Policy | Wins / draws / losses | Scored score | Unscored errors |
| --- | ---: | ---: | ---: |
| Native guard | 617 / 72 / 1381 | 31.55% | 30 |
| Exact contact risk | 631 / 74 / 1373 | 32.15% | 22 |

The scores count wins plus half of draws and exclude errors. The primary
comparison uses1006 complete common pairs out of1050 planned, resampling whole
matched pairs within family for20,000 bootstrap replicates. Exact contact minus
guard is+0.373pp,95% interval [−1.615,+2.361]. Its98.3333% interval is
[−2.038,+2.783]pp, also including zero; the single prespecified primary contrast
uses the95% interval. Absolute score differences are not substituted for the
matched comparison because errors leave different scored subsets.

All-attempt missing-score sensitivity bounds for the finite planned cohort are
[−0.714,+1.762]pp, allowing every error's unknown score to range from0 to1.
They also include zero and are not population confidence intervals. All52 errors
remain unscored. Complete-pair directions were206 positive,204 negative and596
tied; the sign-symmetry diagnostic is not evidence of a mean improvement.

The strategic idea was to combine potentially lethal contacts into the probability
that any contact succeeds, rather than using only the largest separate risk.
The previous independent enumeration audit validates the rational formula under
its stated uniform count/moved-status prior and checks native integer precision.
Mathematical correctness does not establish that this prior or decision rule
improves play against a real opponent. This fresh strength result provides no
support for promoting the current exact-contact candidate.

The frozen honest-head plan can still assess transfer against an honest opponent;
those games would be separate evidence and cannot replace the failed DOS
validation. Existing production, immutable IDs and source/model snapshots remain
unchanged. Preserve this result without tuning on it or silently revising the
candidate.
