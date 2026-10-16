# One-time pursuit reset: no observed DOS behavior change

The frozen regime-reset policy produced **exactly the same saved trajectories**
as its unchanged Fortress-template reference on this cohort: all **254 matched
complete games** and both retained error prefixes match. Both scored **44.09%**
(86 wins, 52 draws, 116 losses; two unscored errors per arm). There is no observed
playing-strength gain or policy behavior change in this fixed DOS screen.

All 126 side-swapped pairs complete in both arms tied. The paired score difference
and bootstrap interval are therefore both zero. **A zero bootstrap interval does
not establish global policy equivalence**: it reflects zero observed variation
in this particular comparison. The separate conservative finite missing-score
bounds over all 128 planned pairs are **[−0.78, +0.78] percentage points**. They
allow each unscored error outcome to vary independently and are not confidence
intervals. All four error attempts remain unscored with their prefixes intact.

The [trajectory diagnostic](divergence.json) identifies no first different move.
The separate [old-screen activation audit](../research/regime/ACTIVATION-CONCLUSION.md)
replayed 80 full forced side histories, executing 17,581 own decisions per policy
and passing 35,162 registered-launcher parity checks. The public reset fired in
50 histories, yet no selected choices changed there either. This distinguishes
a functioning cache-clear API from an intervention that changes decisions.

The separate honest development endpoint, cycle 109, had two changed complete
trajectories and one worsened paired score. That prevents a claim that the
mechanism can never affect behavior, while supplying no evidence of improvement.
No additional cohort or broader reset gate was selected after these results.

The policy clears only its own persistent square goals once when public facts
first eliminate every compatible source template. It retains ordinary goal
persistence otherwise, with unchanged captures, missions, risk, counters and
RNG. This evidence suggests that this narrow one-time reset usually leaves the
selected native action unchanged. It does not establish whether richer model
changes or differently structured commitments would help.

The fixed 512 attempts used identical Fortress armies, matched original DOS
armies and move seeds. Immutable sources, exact rebuild checks, both deployment
audits, full Python/native replay and Qt6 captures are retained. No source,
threshold or coefficient was tuned from this cohort. Production remains
unchanged; neither held-out setup partition was used.
