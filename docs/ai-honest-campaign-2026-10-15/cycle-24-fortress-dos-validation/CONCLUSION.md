# Cycle 24: Fortress improves completed DOS comparisons; errors limit the claim

The unchanged Fortress-only deployment improved over the validated mixture in
this fresh, prespecified validation among complete matched pairs. Its paired gain
was **+5.495 percentage points, 95% interval [+3.785, +7.265]**. This supports the
earlier deployment signal on completed games. However, 276 attempts ended in
unscored errors, and conservative missing-score bounds include zero. The result
does not establish an unconditional gain across every planned game or justify
promotion by itself.

The native move policy was identical in both arms; only own deployment differed.
Each arm attempted 1,000 side-swapped pairs, using original DOS-generated opponent
armies and fresh seed 2340001. Policies, recipes and sample size were frozen before
these validation games. No coefficient, formation or policy was tuned on the
validation outcomes. All 4,000 attempts were retained and independently replayed
in Python and native workers; Qt6 reviews and setup provenance are preserved.

| Own deployment | Wins / draws / losses | Scored score | Unscored errors |
| --- | ---: | ---: | ---: |
| Validated mixture | 261 / 167 / 1412 | 18.723% | 160 |
| Fortress only | 359 / 185 / 1340 | 23.965% | 116 |

Scores count wins plus half of draws and exclude errors. They use different
scored subsets, so their direct difference is not the primary paired estimate.
The single prespecified contrast uses 819 complete common pairs out of 1,000,
with 20,000 whole-pair bootstrap replicates. Fortress minus mixture is +5.495pp,
95% interval [+3.785, +7.265]. The additionally reported 98.3333% interval is
[+3.388, +7.662]pp. No multiplicity adjustment is required for this single
prespecified validation contrast; the 95% interval is primary.

The finite-cohort missing-score effect bounds are **[−2.650, +11.150]pp** when
every missing game score can range from zero to one. These bounds are not
confidence intervals. They show why the positive complete-case result must be
qualified: 181 pairs contain at least one error, and their unknown outcomes could
remove the overall planned-cohort advantage. Errors remain officially unscored;
none was silently converted to a win, loss or draw. Complete-pair directions were
155 positive, 69 negative and 595 tied; the sign diagnostic does not replace the
mean-effect interval or solve missing-outcome uncertainty.

The tested strategic change was to use the existing Fortress formation consistently
rather than the validated three-formation mixture. This is distinct from the
rejected double-Bomb-shell package: no extra Bomb layer or three-swap rearrangement
is present here. The target build and portable tests already establish that this
fixed formation has a bounded setup implementation and leaves the move policy
unchanged. This validation cannot identify which formation feature produces the
observed advantage, and no such causal explanation is claimed.

Cycle 25 independently tests the same frozen deployment contrast against honest
native moves with the same original-army population. Its outcomes must be reviewed
alongside this DOS result and the unresolved errors before any production decision.
Absolute scores are specific to these deployment populations and are not evidence
of a 50/50 match against DOS. Production and immutable policy IDs remain unchanged.
