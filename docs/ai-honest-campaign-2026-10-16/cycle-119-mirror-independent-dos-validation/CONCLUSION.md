# Fresh DOS validation establishes no mixture improvement

The unchanged orientation mixture did not reproduce its positive screening
signal. Across 485 complete side-swapped pairs, mixture minus original Fortress
was **−0.72 percentage points**, with the prespecified primary 95% paired interval
**[−3.56, +2.16]**. This establishes neither improvement, reliable regression nor
equivalence. The full fixed sample of **2,048 attempts** completed; no sample was
extended or stopped for a favorable result. Production remains unchanged.

| Own formation | Wins / draws / losses | Unscored errors | Scored score |
|---|---:|---:|---:|
| Original Fortress | 305 / 229 / 468 | 22 | 41.87% |
| Existing-ticket original/mirror mixture | 309 / 217 / 478 | 20 | 41.58% |

Score counts a draw as half a win. These scored-arm percentages use 1,002 and
1,004 games respectively; their difference is not the complete-pair effect.
Among the 485 complete pairs, 84 improved, 92 worsened and 309 tied. The remaining
27 of 512 planned pairs contain at least one unscored error. All 42 error attempts
and their legal prefixes remain preserved.

Allowing each unscored game any score from zero to one gives an all-planned-pair
finite-cohort effect range of **[−2.34, +1.76] percentage points**. Missing outcomes
can change this sample's direction. These conservative bounds are not confidence
intervals and do not quantify sampling uncertainty. The primary 95% interval is
reported separately; neither calculation establishes a useful gain.

The [selection protocol](../research/mirror-deployment/FINAL-VALIDATION-PROTOCOL.json)
was frozen before either source screen was complete. After both source screens
finished and passed their audits, its fixed rule selected the larger positive
DOS paired mean, the unchanged immutable ID
`student-fortress-mirror-mixture-template-v1-normal`. This fresh cohort compares
it with the unchanged `student-fortress-template-flag-bomb-v1-normal`, using seed
3119001, 512 side-swapped pairs per arm, 1,000 plies and the original-DOS setup
population. The selected ID, likelihoods, placements and stopping rule were not
tuned from validation games. No historical, screening or honest-opponent score
is pooled into this primary contrast. The earlier champion's separately
validated 44.33% comes from another cohort; the comparator here is the same
policy's newly measured 41.87% score.

The [terminal intended-setup audit](intended-setups-audit.json) independently
reconstructs the frozen original Fortress table and each recorded accepted RNG
ticket. It verifies all 2,048 actual-color own deployments, matched opponent
armies, move seeds and sides. The mixture selects original Fortress in 258 pairs
and its complete horizontal mirror in 254. All **516 original-selected mixture
games**, including **13 error prefixes**, exactly match the corresponding baseline
initial states, move sequences, outcomes, plies and raw reasons. The 508
mirrored-selected games have no fixed-mirror arm in this cohort: their intended
setups and common opponents/seeds/sides are checked, without any claim of
mirrored-subset trajectory equivalence.

The six component tests were executed for the unchanged C117 sources and are
**reused qualification**, not six new C119 test executions. The
[qualification provenance receipt](qualification-provenance.json) verifies that
the copied log is byte-identical and every C119 frozen policy specification
matches C117. Terminal C119 game replay and deployment reproduction are separate
checks retained in their own receipts. Target component evidence elsewhere
qualifies only the isolated banked deployment path, not this desktop inference
bridge or complete production gameplay.

This is DOS-specific validation of a source-informed honest policy: it receives
its own army, public events and a declared setup-population prior, without enemy
setup or hidden-rank input. The DOS reference retains its original information
access. Fresh seeds may repeat built-in templates; this is not unseen-generator
or human-opponent validation. The mixture uses its existing setup ticket, with
its setup seed deterministically derived from the movement seed; enemy deployment
uses a separate private draw. No benefit under a different RNG coupling is
established. Five of ten accepted tickets select each orientation; exact balance
in every finite seed cohort is not required.

The fresh result supplies no reason to replace the reference policy or claim an
honest-AI ceiling. Both candidate IDs, their earlier positive and negative
screens, this inconclusive validation and every engine error remain available
for review.
