# Open reserve: honest end-to-end formation screen

Releasing Fortress's isolated Lieutenant did **not establish an honest playing
gain**. Against Missions, the candidate scored **73.88%** (165 wins, one draw,
58 losses), versus **78.13%** for the unchanged Fortress template reference
(174 wins, two draws, 48 losses). All 448 planned attempts completed without an
engine error. Score counts a draw as half a win.

Across 112 matched side-swapped pairs, candidate minus reference was **−4.24
percentage points**, with the planned 95% paired interval **[−10.71, +2.23]**.
Seventeen pair scores improved, 26 worsened and 69 tied. The screen establishes
neither a population benefit nor equivalence; the interval also includes zero.
With no missing scores, the finite missing-outcome bounds collapse to the
observed −4.24-point sample difference. Those bounds are not confidence intervals.

The family breakdown retains variation rather than averaging it away. Each row
has 16 pairs; intervals are exploratory and unadjusted for seven-family or
campaign selection.

| Opponent setup family | Candidate score | Reference score | Paired difference, points | 95% interval, points |
|---|---:|---:|---:|---:|
| fortified | 48.44% | 57.81% | −9.38 | [−26.56, +9.38] |
| uniform | 75.00% | 87.50% | −12.50 | [−34.38, +6.25] |
| unguarded | 71.88% | 81.25% | −9.38 | [−28.13, +9.38] |
| forward | 90.63% | 100.00% | −9.38 | [−25.00, 0.00] |
| decoy | 96.88% | 100.00% | −3.13 | [−9.38, 0.00] |
| presets | 62.50% | 54.69% | +7.81 | [−12.50, +29.69] |
| broad-mixed | 71.88% | 65.63% | +6.25 | [−9.38, +25.00] |

The idea changes one initial assignment: swap own origins 28 and 38, moving a
Bomb behind the previously isolated Lieutenant. This gives all 33 mobile pieces
potential front access once friendly corridors clear, compared with 32 in the
reference. It does not immediately open a legal move for the reserve in the
crowded starting formation. Flag, Spy, inner Bombs, common guard, move policy,
public prior and random draws retain their source. Geometry proves a newly
available resource, while these games test whether the whole assignment helps.
No benefit is established here.

The [intended-setup audit](intended-setups-audit.json) verifies the exact swap in
every actual saved own army, including the rotated Blue view. Opponent armies,
move seeds and sides match across arms. Both policies generated their own armies;
the setup corpus was not forced over the deployment treatment. Because own
formations intentionally differ, all 224 cross-arm roots are unequal and the
[trajectory diagnostic](divergence.json) excludes them from mechanism activation
comparisons. Later move differences cannot identify the causal value of the
released Lieutenant by themselves.

This is a fresh-layout screen from seven familiar generators against one honest
opponent, not held-out generator validation or general strength. Absolute 50% is
not the neutral reference because our Fortress armies and the opponent's setup
distribution differ. C115's separately frozen DOS study addresses another
endpoint. No gate, placement, source, stopping rule or policy was adapted from
either study's outcomes.

The original six-test component proof was preserved: this cycle reran the tests
with output redirected to a private temporary directory. Python/native replay,
Qt6 captures, saved policy-owned setup reproduction and independent direct-SQL
arithmetic passed. Observed whole-arm host times were 23.99 seconds for the
candidate and 23.19 for the reference; these include their different game
trajectories and are not an isolated setup-cost estimate. Preserve the policy and
negative screening evidence. Production remains unchanged.
