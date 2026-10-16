# Fortress reflection and ticket mixture: honest screen

Fixed horizontal mirroring produced a negative signal against Missions; the
two-formation ticket mixture established no gain over the original Fortress.
All 672 planned attempts completed without errors.

| Own formation | Wins / draws / losses | Score |
|---|---:|---:|
| Original Fortress | 195 / 1 / 28 | 87.28% |
| Fixed horizontal mirror | 168 / 4 / 52 | 75.89% |
| Existing-ticket mixture | 187 / 3 / 34 | 84.15% |

Score counts a draw as half a win. Across 112 matched side-swapped pairs per
contrast, fixed mirror minus original was **−11.38 percentage points**, with the
planned exploratory 95% interval **[−18.53, −4.02]**. Eighteen pairs improved,
34 worsened and 60 tied. Mixture minus original was **−3.13 points [−7.59,
+1.12]**: ten pairs improved, 14 worsened and 88 tied. No mixture benefit or
policy equivalence is established. The two intervals are exploratory and
unadjusted for campaign hypothesis selection; neither result is a general
Stratego-strength or promotion decision.

Family variation is substantial. Each row has 16 pairs; these additional
intervals are unadjusted for family or campaign multiplicity.

| Opponent setup family | Fixed mirror difference, points [95% interval] | Mixture difference, points [95% interval] |
|---|---:|---:|
| fortified | −7.81 [−34.38, +18.75] | −7.81 [−28.13, +10.94] |
| uniform | +4.69 [−14.06, +21.88] | +6.25 [0.00, +15.63] |
| unguarded | −28.13 [−40.63, −15.63] | −12.50 [−25.00, −3.13] |
| forward | +6.25 [0.00, +15.63] | +3.13 [0.00, +9.38] |
| decoy | −18.75 [−37.50, 0.00] | +3.13 [0.00, +9.38] |
| presets | −34.38 [−59.38, −6.25] | −12.50 [−25.00, −3.13] |
| broad-mixed | −1.56 [−18.75, +14.06] | −1.56 [−17.19, +10.94] |

The exact full reflection preserves rank inventory, Bomb-cut distance and mobile
connectivity. It reflects Flag and Spy along with every other own rank. Movement,
inference and random draws retain their source. Reflecting only our formation
changes matchups against the fixed opponent population, so this screen cannot
separate coordinate tie ordering from formation interactions. A full-position
symmetry experiment would be a different study. Absolute 50% is not a neutral
reference because our armies and the opponent's setup distribution differ.

The [preregistered composition audit](composition-audit.json) verifies more than
the intended layouts. The mixture chose original Fortress in 58 pairs and its
mirror in 54. Every one of its 224 saved games exactly reproduces the selected
fixed arm's initial state, move sequence, termination and outcome. Thus its
behavior is the intended deployment mixture, rather than a changed move policy.
Its finite-cohort score need not equal the arithmetic mean of the other arms:
the fixed ticket rule selects particular paired matchups. There was no adaptive
selection from their outcomes.

The [independent direct-SQL review](independent-review.json) reproduces standings,
complete-pair effects and finite error bounds while explicitly allowing the
intended own-setup differences. Opponent armies, move seeds and sides match
across arms. With no errors, finite missing-score bounds collapse to each
observed sample effect; those bounds are not confidence intervals. Six component
tests, all-state Python/native replay, policy-owned setup reproduction and three
Qt6 captures support the mechanical qualification.

C117's DOS endpoint and this honest endpoint were both frozen before the first
saved game. No held-out generator cohort, placement, score or stopping rule was
used for tuning. This is fresh-layout screening from familiar generators against
one honest opponent. Preserve both candidate IDs and this negative/inconclusive
evidence; the original formation remains the comparator. Production is unchanged.
