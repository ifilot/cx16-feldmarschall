# Descriptive activation in completed C110 and C111

This post-hoc audit follows the identity initially assigned to common guard
post 21 through completed saved games. It reads own ranks and ranks disclosed
by actual battles. No policy is run, fitted or changed, and no game outcome is
used to attribute strength to the mechanism. Saved error prefixes remain included
and identified; their absent future events are not inferred.

| Study / arm | Original guard attacks a Miner | Games containing those attacks | Captures at an inner gate | Guard retained after those attacks |
|---|---:|---:|---:|---:|
| C110 DOS / reference Miner | 6 | 6 | 3 | 0; all six exchange |
| C110 DOS / candidate Sergeant | 30 | 27 | 1 | 30 |
| C111 Missions / reference Miner | 7 | 7 | 2 | 0; all seven exchange |
| C111 Missions / candidate Sergeant | 14 | 12 | 0 | 14 |

Most candidate guard-versus-Miner combats therefore happened away from the two
inner gates. The counts establish that the assigned Sergeant sometimes remains
a useful surviving combat piece; they do not establish that it was retained as
a stationary Flag guard. Repeated events within a game are not independent
activations. Different initial own armies and subsequent histories also prevent
these counts from being matched-root causal comparisons.

The narrower test asks whether any own defender immediately recaptured a Miner
on the turn after that Miner removed an inner Flag Bomb:

| Study / arm | Immediate recaptures | Retain a defender | Exchange | By original guard 21 |
|---|---:|---:|---:|---:|
| C110 DOS / reference | 4 | 0 | 4 | 3 |
| C110 DOS / candidate | 2 | 2 | 0 | 1 |
| C111 Missions / reference | 5 | 3 | 2 | 2 |
| C111 Missions / candidate | 1 | 1 | 0 | 0 |

This specific natural post-breach use of the new guard was observed once in the
DOS candidate and never in the honest candidate cohort. Other defenders also
recapture, particularly on the left gate already covered by a Lieutenant. These
small descriptive counts cannot explain a policy's total score or demonstrate
the outcome of a counterfactual guard assignment. They provide a useful limit
on the original local explanation without altering the frozen strategy.

The census covers 256 attempts per DOS arm, including five error prefixes each,
and 224 attempts per honest arm with no errors. Both colors are represented
equally. Identity tracking checks every own move's rank against its initial
own origin, including the rotated Blue formation.

Reproduce with `python3 tools/new_campaign_guard_activation.py`.
[Exact event records, definitions and tournament hashes](natural-recaptures-C110-C111.json)
retain both diagnostic categories; the same battle can appear in both categories
and must not be counted twice by summing the tables.
