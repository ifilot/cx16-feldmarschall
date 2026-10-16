# A cheap back-row control explains most Flag prediction gain

The source-structured procedural background passed its frozen prediction gate.
A subsequent, explicitly **post-hoc** ablation asks whether its Flag benefit
requires12 screen geometries and learned residual-Bomb row odds. It reuses the
already viewed640 prediction prefixes; these are not new validation data. No
parameter, model weight or tail probability was fitted or selected here.

The control replaces the structural component with uniform legal armies
conditioned only on the Flag occupying canonical back-row origins30..39. The
outer80%template/20%background mixture and the selected1%uniform tail within the
background remain identical. This gives a cheap explicit comparator for fresh
games, rather than attributing every gain to the fuller model.

| Fixed predictive comparison | Mean Flag log-loss difference, nats | Descriptive95% interval |
| --- | ---: | --- |
| Back-row control minus original uniform background | −0.24577 | [−0.25631, −0.22878] |
| Structured background minus original uniform background | −0.25042 | [−0.26560, −0.23135] |
| Structured background minus back-row control | −0.00465 | [−0.01285, +0.00042] |

Lower is better. The last interval does not establish equality, and this reused
cohort cannot confirm the newly introduced control. Almost the same Flag
prediction improvement appears under the simple source constraint. The richer
model does have a lower secondary Bomb Brier score: structured minus back-row
is−0.00204 per original square, descriptive95%[−0.00260,−0.00148]. Whether that
improves native capture choices or routes needs actual fresh matches.

All intervals reuse the frozen study's formation-stratified paired bootstrap:
average four decisions per trajectory, fixed80/20template/procedural weights,
resample generator armies and RNG-context blocks within four fixed formations.
They do not establish generalization over arbitrary formations or humans. The
same one procedural army still produces four confidently wrong predictions
under both backgrounds; four occurrences are not four independent armies.

The control has a closed form. LetDbe the public facts, Ethe event that Flag is
in the back row, Uthe number of unmoved undisclosed origins and Bthe number of
those origins in the back row. Bayes conditioning gives
`P(D | E) / P(D) = P(E | D) / P(E) = 4*B/U` when Flag remains undisclosed. A
known back-row Flag gives ratio4; a known off-row Flag gives zero for this
component. The uniform tail retains positive support. Conditional Flag mass is
uniform over theBcompatible row sites. For a remaining Bomb countR, an unknown
unmoved slot has probability `R*(1-P(Flag at slot))/(U-1)` while Flag is unknown,
or `R/U` after its disclosure. Known Bomb identities remain point masses,
including captured public identities. Moved origins cannot be immobile.

An independent exhaustive five-piece enumeration checks absolute public-evidence
probabilities and both marginals against every compatible small army. The test
passed. The analysis uses only original-origin disclosures and movement facts;
truth is reserved for offline proper scoring.

`tools/analyze_procedural_backrow.py` reproduces the control analysis in a fresh
output directory; its `compare_saved` function reproduces the paired comparison
without generating games. Raw scores, source-cohort hashes, logs and tests are
preserved. This is a prediction/mechanism result, not a DOS playing-strength
score or a policy-promotion decision.
