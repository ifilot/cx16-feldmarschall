# Reset activation without observed choice changes on an old screen

The fixed source-bound audit completed all saved public histories for the first
40 C21 screening game IDs, both colors: **80 side histories and 17,581 own native
decisions per policy**. Every baseline and candidate adapter decision matched its
registered frozen launcher: **35,162 parity checks passed**. Chosen moves were
corrected to the actual saved move through `played` in both the adapter and its
launcher before continuing, preserving persistent goal behavior on the forced
history. No current benchmark or validation trajectory selected this sample.

The one-time hard-support reset fired in **50 of 80 side histories**. Nevertheless,
**zero selected choices changed** relative to the unchanged baseline. Thus this
audit does not demonstrate an improvement in actual decision selection, despite
proving that the public gate fires and the native cache clear executes. It is a
negative mechanism-incidence result on this cohort, not policy equivalence.
The fixed sample and gate were not expanded or relaxed after observing this.

The separate cycle 109 development tournament did contain two changed complete
trajectories, so the zero old-screen choice count cannot establish that the
mechanism is globally inert. That tournament established no score gain. Neither
result supplies evidence for promotion, and later differences along a changed
trajectory would not count as independent first-root interventions.

Mean host time for choose plus public-event processing was **1.625 ms** per own
decision for baseline and **1.669 ms** for candidate: measured difference
**+0.044 ms**. Choose alone averaged 1.360 versus 1.367 ms; public-event work
accounted for the remaining measured cost. These are wall times under concurrent
load, not controlled microbenchmarks, target cycle counts or CX16 qualification.

The [protocol](ACTIVATION-PROTOCOL.json) pins the exact cohort, game IDs, policies
and auditor source hash before execution. The [results](activation-result.json)
retain every side-history count and first-choice field, including the null
fields. Execution took 176.95 seconds. No new strength games were played and no
source, coefficient, runtime or sample was changed from these observations.
