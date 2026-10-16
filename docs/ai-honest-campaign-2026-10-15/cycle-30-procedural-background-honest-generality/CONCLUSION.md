# Procedural backgrounds lose strength outside the DOS setup population

The richer background models did not improve play against the honest guarded
student on these supplied armies. The unchanged template policy scored 49.46%,
the back-row background 41.07%, and the structured procedural background 38.84%.
The pure back-row prior also scored 41.07%. These results support keeping the
out-of-population test separate from the original-DOS screen; greater fidelity
to one setup generator does not establish general Stratego strength.

| Frozen policy | Wins / draws / losses | Score |
| --- | --- | --- |
| Original template mixture | 273 / 8 / 279 | 49.46% |
| Template plus back-row background | 225 / 10 / 325 | 41.07% |
| Template plus structured background | 208 / 19 / 333 | 38.84% |
| Pure back-row prior | 225 / 10 / 325 | 41.07% |

Each arm completed 560 Classic games: 40 side-swapped pairs in each of seven
forced-army families, with identical physical armies and move seeds across arms.
This tests movement on supplied armies, rather than owned deployment. All 2,240
attempts completed without errors and all 280 pairs enter each comparison.
Scores count wins plus half draws; they are not win rates.

| Paired contrast | Effect, percentage points | Planned per-contrast 95% interval |
| --- | --- | --- |
| Back-row background minus original | -8.39 | [-13.04, -3.75] |
| Structured minus back-row background | -2.23 | [-6.61, +2.14] |
| Pure back-row minus original | -8.39 | [-13.04, -3.75] |
| Structured minus original | -10.63 | [-15.27, -6.16] |

The frozen plan specifies four exploratory contrasts. Its ordinary 95%
intervals are per-contrast; the generic 98.3333% intervals are descriptive and
do not control all four comparisons. No campaign-wide or four-comparison
familywise significance claim is made. Structured versus the back-row mixture
remains inconclusive. Matching aggregate results for the pure and mixed
back-row models do not establish identical decisions or policy equivalence.
With no missing outcomes, finite missing-score bounds collapse to the observed
cohort differences and are not confidence intervals. Fresh validation would be
required before any promotion; these results do not support promoting an
addition to the original mixture.

An unexpected SIGTERM ended the initial orchestration after three complete
560-game arms were saved. Its exit status 143, original log and interruption
receipt are retained. Recovery reanalysed those three immutable artifacts,
generated only the previously absent fourth arm under the unchanged frozen
plan, and verified the original three tournament SHA-256 values remained
unchanged. No saved game was discarded, replaced or played again for a new
outcome. Replay verification was repeated during reanalysis. The termination
cause is unknown; it did not select a stopping point or change the fixed sample.

Batch execution was 73.72, 73.54, 83.36 and 61.03 seconds respectively. Different
game lengths and concurrent load prevent treating these as controlled inference
timings. The tested models remain desktop Python/native policies; the separate
compact native prior has its own target qualification and a different immutable
ID. No source, model, coefficient, seed or policy ID was tuned on this cohort.
All games pass Python and native every-state replay with four Qt6 captures.
Frozen identities, artwork, colors and board orientation are preserved. Production
behavior remains unchanged.
