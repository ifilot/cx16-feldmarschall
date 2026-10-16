# Mobile-rank pursuit: honest development endpoint

Keeping token-specific mobile-rank beliefs in long-range objectives did **not
establish an improvement** against the honest Missions opponent. The frozen
candidate scored **53.13%** (51 wins, no draws, 45 losses), versus **55.73%** for
the source-template control (53 wins, one draw, 42 losses). The matched difference
was **−2.60 percentage points**, 95% paired interval **[−10.42, +5.21]**.
All 192 attempts completed without engine errors.

This is move-policy development evidence on six unfamiliar synthetic deployment
families, with eight side-swapped records per family. Both policies received
identical physical armies, public priors and move seeds. Their Fortress setup
choice is not evaluated here. Family effects vary: −6.25 points for uniform and
exposed rear, −9.38 for rear shells, −12.50 for a single decoy, +6.25 for forward
Flags and +12.50 for scattered guards. Each family has only eight paired records;
none supplies a reliable standalone improvement or regression conclusion.

The [trajectory diagnostic](divergence.json) found 32 changed complete game
sequences out of 96; all first differing moves were made by the candidate at an
identical preceding position. Sixteen changed sequences retained their outcomes.
Paired scores improved five times, worsened nine times and tied 34 times. Later
choices on diverged trajectories are dependent consequences, not additional
independent mechanism activations. These data establish neither equivalence nor
a generality loss.

The implementation changes only concealed-target objective gains. Native capture
and danger values remain unchanged. An independent arithmetic oracle additionally
checks 19,200 actor cases spanning both colors, moved/unmoved targets,
exchangeable mobile probabilities and zero conditional-mobile-mass fallback.
All reduce exactly to the existing integer expectation. This numerical property
does not imply that complete persistent policies become identical after their
earlier goals or choices have already differed.

The registered archive was independently rebuilt in a temporary directory; its
launcher, observer and Python runtime files reproduce the bytes embedded in the
saved candidate tournament. The test helpers match the frozen adapter functions.
See the [independent rebuild receipt](../research/evaluation/mobile-goal-independent-rebuild.json).
The added 2,000-byte table and larger protocol buffer remain desktop research:
no CX16 fit, latency or production-readiness claim follows from these games.

Python/native replay and Qt6 captures are retained. Neither reserved validation
partition was used. No policy, formation or coefficient was tuned from these
outcomes. Production remains unchanged; cycle 103 is a separate DOS endpoint.
