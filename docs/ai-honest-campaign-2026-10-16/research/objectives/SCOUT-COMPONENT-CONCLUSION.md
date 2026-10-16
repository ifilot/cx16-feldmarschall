The stronger native component test changes **all 14 prespecified Scout pursuit
goals but zero whole selected moves**, across the same 356 roots from 48 old
screening games. This resolves the earlier uncertainty about whether redirecting
a previously unselected actor could promote its alternative above other actors:
it does not do so at these sampled states. No new strength policy or tournament
was created.

The isolated native patch skips only the certified actor's current disclosed
Scout target during `plan()`. The ordinary planner then chooses another target
with unchanged eligibility, utility, distance, persistence, tie ordering and
capture/danger scoring. Fourteen actor vetoes occur in 12 roots. The remaining
344 sampled roots have an empty veto map and retain default-off behavior.

Every counterfactual starts from the identical public F/B packet, persistent
native strategy and RNG state used for the baseline. After the counterfactual,
the pre-decision state is restored and the baseline decision rerun. Its chosen
move, complete native goal trace, strategy bytes and RNG exactly match the first
baseline run in every active root. The final baseline rerun also regenerates the
diagnostic goal scratch used by actual-move correction. All 6,520 intervening
prefix choices match the immutable Fortress-template launcher. The alternative
goals are never allowed to contaminate subsequent historical decisions.

This is a **same-state, one-decision component rejection**, not proof of full
policy equivalence. A persistent policy could carry altered nonmoving actors'
goal memories into later decisions, where the existing persistence bonus could
change choices. Nor does the certificate prove indefinite Scout evasion. The
current incidence and direct action test supply insufficient reason to launch a
strength tournament; preserve the result rather than relaxing the original
eligibility gate to force activation.

Three native fixture tests cover permitted own ordinary actor/disclosed enemy
Scout mappings, rejection of concealed targets/own Scouts/out-of-range targets/
optional rules, and snapshot/restore choice, strategy and RNG parity. The native
component is compiled in a temporary copy of the frozen reference archive; no
shared core or policy source changed. The first complete run is preserved as
`scout-component-attempt1-result.json` and `.log`. A subsequent defensive API
check moves target range validation before array access; it changes no valid
mapping, strategic gate or model. The final run repeats the fixed protocol with
that input-validation correction.

Evidence: `SCOUT-COMPONENT-PROTOCOL.json`, `scout_component.py`,
`scout-component-result.json`, `scout-component.log`, `test_scout_component.py`,
`scout-component-tests.log`. No final-validation or current-screen trajectories
were read, and no game-outcome labels select these roots.
