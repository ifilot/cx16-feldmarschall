# Fortress reflection and ticket mixture: DOS screen

Both candidate formations improved the observed DOS sample, but neither establishes a population improvement. The fixed screen completed all 768 planned attempts, including 13 unscored engine errors. Production is unchanged.

| Own formation | Wins / draws / losses | Errors | Scored score |
|---|---:|---:|---:|
| Original Fortress | 69 / 57 / 126 | 4 | 38.69% |
| Fixed horizontal mirror | 77 / 50 / 124 | 5 | 40.64% |
| Existing-ticket mixture | 80 / 48 / 124 | 4 | 41.27% |

Score counts a draw as half a win. Fixed mirror minus original was **+3.33 percentage points** across 120 complete side-swapped pairs, with exploratory 95% interval **[−4.38, +11.04]**. Forty-eight pairs improved, 42 worsened and 30 tied. Mixture minus original was **+3.93 points [−1.65, +9.71]** across 121 complete pairs: 30 improved, 20 worsened and 71 tied. Intervals cross zero and are unadjusted for campaign selection; neither is confirmation or a promotion decision.

Errors affect eight of 128 planned pairs for the fixed-mirror comparison and seven for the mixture. Assigning every unscored game any score from zero to one gives finite-cohort effect bounds of **[+0.20, +3.71] points** for fixed mirror and **[+0.98, +4.10] points** for mixture. Thus missing outcomes cannot reverse this particular sample's direction. These bounds do not account for sampling uncertainty and are not confidence intervals. Scored-arm percentages and complete-pair effects use different denominators.

The [composition audit](composition-audit.json) verifies all intended layouts, setup tickets and matched opponent armies. The mixture chose original Fortress in 54 pairs and mirrored Fortress in 74. All 256 saved mixture streams exactly reproduce the selected fixed arm's initial state, moves and termination, including four identical error prefixes. The five-of-ten rule is fixed before outcomes; the finite cohort need not have equal orientation counts or equal the arithmetic mean of the two fixed-arm scores. No orientation was selected from observed game results.

Reflecting every own rank preserves inventory and static formation geometry, including Flag and Spy. Movement, inference and RNG draws retain the frozen baseline. Own-only reflection changes interactions with the opponent's layout, so this screen cannot isolate coordinate tie ordering. It also does not establish a universal best orientation. The separate, concurrently preregistered honest-opponent C118 screen found a negative fixed-mirror signal and no mixture gain. Together these endpoints favor preserving the evidence rather than promoting this layout mixture.

The [independent direct-SQL receipt](independent-review.json) reproduces standings, complete-pair effects and finite error bounds, explicitly permitting the intended own-layout treatment while requiring identical opponent armies, move seeds and sides. Full mechanical qualification separately covers source rebuilds, six component tests, all-state Python/native replay, policy-owned setup reproduction, original DOS setup reproduction and three Qt6 captures. The audit receipt records their results.

Both C117 and C118 plans and policy snapshots were frozen before either endpoint's first saved game. No held-out generator cohort, game outcome, score or stopping rule was used to alter these policies. This remains an exploratory screen against the specified DOS setup population, not evidence of an honest-AI ceiling or a deployment recommendation. Preserve both immutable candidate IDs and all errors.
