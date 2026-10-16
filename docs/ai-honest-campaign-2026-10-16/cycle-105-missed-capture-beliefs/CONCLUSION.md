# Missed-capture conditioning v1: no established DOS gain

The single-observation rank-conditioning policy scored **40.48%** against DOS,
versus **40.24%** for its unchanged Fortress-template control. The complete-case
paired difference was **+0.41 percentage points**, with 95% interval
**[−0.41, +1.42]**. This exploratory screen establishes no improvement. The paired
contrast and official standings use different error exclusions and denominators.

Each arm attempted 256 Classic games with seed 3105001 and 128 rotated pairs.
Candidate outcomes were 78 wins, 48 draws, 126 losses and four unscored errors;
control outcomes were 77 wins, 48 draws, 126 losses and five errors. All 512 saved
traces, including errors, remain reviewable. On 123 complete matched pairs, only
three scores changed: two positive, one negative, 120 ties. Sparse outcomes do
not establish equivalence. Across all 128 planned pairs, arbitrary error scores
give finite-cohort effect bounds **[−1.56, +1.95]** points, separately from sampling
uncertainty.

The model uses one public declined capture of an opponent-visible own soldier
to apply a fixed weak rank likelihood. It preserves exact rank inventory and
movement constraints, never multiplies repeated idle evidence, and consumes no
true enemy rank. Immediate moves still come from the unchanged native evaluator
with Flag/Bomb marginals. Declining a capture is behavioral evidence, not a
logical deduction: DOS can prefer another objective.

Independent mechanical review found a v1 eligibility defect **before inspecting
these outcomes**: the apparent absence of recapture protection can depend on the
hypothetical enemy source still blocking a friendly Scout ray. That source would
actually vacate. See [the preserved qualification](../research/information/QUALIFICATION-v1.md).
The original ID and runtime were kept unchanged; this already-launched fixed
sample was completed. V2 corrects the geometry under a new immutable ID and is
tested in a separate fresh cohort, cycle 106. The two cohorts' raw scores are not
a causal estimate of the geometry fix. V1 is not a promotion candidate.

The plan, immutable source/model/recipe, exact own-setup and original-DOS setup
reproductions, Python/native every-state replay, Qt6 captures and independent
SQL arithmetic are retained. Production remains unchanged.
