The persistent follow-through finds **one later native choice change among 6,520
forced-prefix decisions**. Immediate vetoing remains inert at all 14 certified
actor goals, but retaining the altered goal memory changes one subsequent whole
move. The earlier one-decision result therefore does not establish policy
inertness or equivalence. This sparse activation does not justify registering or
launching a strength policy.

The exact trail occurs in old screening game 122, Blue. At own decision 101
(ply 201), refusing the disclosed Scout target 45 changes the goal stored for the
actor at 13 to 61, while the selected move remains 54→64. That single goal byte
continues to differ at decisions 102–114. At decision 109(ply 217), the baseline
chooses 5→4 and the candidate chooses 13→12. The goal-memory difference clears at
decision 115. This is eight own decisions after the veto, exposing the delayed
route/persistence effect that a one-decision comparison could miss.

Across the same 48 old games and 356 fixed sampled positions, the unchanged gate
still qualifies 14 actor goals in 12 positions. There are 47 decisions with differing
goal memory after correction to the actual saved move. The compact trail has 56
records covering memory onset, persistence and clearing. No other native strategy
byte differs after actual-move correction. All 6,520 public belief packets and
RNG states match, and every baseline native choice matches the frozen launcher.
A repeated run adding the complete memory trail exactly reproduces the first
run's counts, choices, roots and divergence records.

Candidate and baseline keep separate native strategy/RNG histories throughout.
At a sampled candidate position, a temporary proposal identifies its current
native goals; the gate is applied after restoring ONLY that candidate's own
pre-decision state. The final goal memories persist. No candidate state is reset
to the baseline. Both sides' proposed moves are independently corrected to the
same actual public move before the historical game continues. Consequently this
is activation on **forced recorded histories**, not play along the candidate's
own trajectory and not evidence of a higher score.

The gate, safety conditions, alternate-objective requirement, 356 positions and
old screening cohort remain unchanged. No current screen or validation game was
inspected, no placement/score parameter was tuned and no new policy was registered.
All further policy or all-decision schedule work would need a separate prospective
mechanism/cost study before strength screening.

Evidence: `SCOUT-PERSISTENT-PROTOCOL.json`, `scout_persistent.py`,
`scout-persistent-result.json`, `scout-persistent.log`, the preserved first run,
and `scout-persistent-review.json`.
