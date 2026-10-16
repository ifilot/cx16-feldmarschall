The corrected missed-capture background model has **no established gain against
the honest Missions opponent** on the frozen development setup corpus. V2 scores
56.77% (54 wins, 1 draw, 41 losses), versus 55.73% for the unchanged Fortress
template reference (53 wins, 1 draw, 42 losses). The matched difference is
**+1.04 percentage points**, with paired 95% interval **[-2.08, +4.17]** across
48 complete side-swapped pairs. All 192 attempts are scored; there are no engine
errors. These exploratory results establish neither improvement, regression nor
equivalence.

The trajectories expose limited activation: nine of the 96 matched games first
diverge on a candidate decision; 87 retain identical moves. Six of the nine
changed trajectories retain the same score. Two pairs improve, one worsens and
45 tie. Tied outcomes are distinct from identical trajectories, and later move
differences within a changed game are consequences rather than independent
mechanism activations. Family effects vary: uniform is +12.5 points and
rear-shell -6.25 points, each from only eight pairs; the other four families have
zero paired score difference. These small family samples support no broad
generality claim.

V2 preserves the declared single soft missed-capture observation and exact
uniform-background conditional rank calculation. Its geometry checks friendly
recapture rays after the hypothetical enemy source is vacated, correcting the
V1 source-occupancy bug. A concealed token's willingness to forgo an attack is
not a logical deduction of its rank: traps, future plans and opponent errors can
all explain the action. The model applies a limited likelihood assumption rather
than proving the unknown capture was free or assigning a hidden rank. Mechanical
qualification of the correction does not validate that behavioral assumption.

This is an honest-opponent development transfer endpoint, separate from the DOS
screen. It uses fresh move seeds and the same fixed development armies in both
arms, without playing either validation partition. It is not a controlled direct
V1-versus-V2 strength comparison. Source archives and earlier rejected evidence
remain preserved; production policy is unchanged.

All games were replayed in Python and by the native verifier through every saved
state; Qt6 review captures are retained. The independent review also checks
registered source hashes, permitted capabilities, frozen dataset records,
matched armies/seeds/IDs and the corrected archived geometry. See `audit.json`,
`divergence.json`, and `../research/evaluation/cycle-107-independent-review.json`.
