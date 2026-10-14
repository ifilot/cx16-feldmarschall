# AI speed, difficulty and fairness

Normal retains the planned evaluator's choices while reducing its maximum
observed thinking time from **43 to 24 frames** (0.72 to 0.40 seconds).
Easy, Normal and Hard are selectable in New Game. Every level uses the same
masked information; difficulty changes evaluation, not access to hidden ranks.

## Choosing a level

Click the difficulty button to cycle Easy → Normal → Hard, or use the
left/right arrow keys. The choice persists during the session and in saved
games. Classic resets the optional rules without changing difficulty. Older
saved games default to Normal; invalid encoded levels also fall back to Normal.
The saved-game format and size are unchanged: spare bits in the scene flag byte
hold a marker and the level.

| Level | Decision behaviour | Maximum observed thinking time |
| --- | --- | ---: |
| Easy | Skip route planning; larger score variation permits small mistakes. Immediate victory and flag protection remain active. | 14 frames / 0.23 s |
| Normal | Persistent objectives, routes, danger, flag defence and specialist values. Default level. | 24 frames / 0.40 s |
| Hard | Re-evaluate six shortlisted moves against the opponent's best material reply, including moving-flag arrival. | 45 frames / 0.75 s |

Hard checks legal captures by revealed enemies using their known ranks.
Unknown enemies use estimates from the remaining rank pool and movement
information. Concealed attacks are evaluated across their possible occupancy
outcomes, weighted by remaining counts. It replaces the candidate's local
danger deduction with the reply assessment, avoiding counting the same danger
twice. This is bounded two-ply tactical evaluation, not a full minimax search:
ordinary quiet replies, longer strategic sequences and unrevealed long scout
moves are not explored. Enemy knowledge of our own ranks is treated
conservatively when estimating its capture opportunities.

## Strength measurements

Final validation used fresh seeds after development, with no subsequent tuning.
Each pairing played 1,200 games: 400 mixed deployments, 400 randomly generated
and 400 from the built-in presets. Each round plays identical deployments twice
with the engine sides swapped. Draws count as half a point.

| Comparison | Wins | Draws | Losses | Score | Paired 95% interval |
| --- | ---: | ---: | ---: | ---: | --- |
| Normal versus Easy | 881 | 174 | 145 | 80.7% | 78.8–82.6% |
| Hard versus Normal | 617 | 86 | 497 | 55.0% | 52.5–57.5% |
| Hard versus Easy | 974 | 67 | 159 | 84.0% | 82.0–85.9% |

The 3,600 games contain no illegal decisions. The referee owns the true board
and passes only permissible information. Games end on flag capture, inability
to move, or a 1,000-ply cap. All 327 draws reached that cap. Confidence intervals
use 10,000 bootstrap resamples of complete side-swapped pairs.

Hard's overall improvement is modest. Its mixed-deployment subgroup scored
51.7%, with an interval of 47.2–56.1%, so that subgroup alone does not establish
an advantage. Random and preset groups scored 56.4% and 56.9%. These results
compare our levels under classic rules; they are not human Elo ratings or
variant-specific strength measurements. [The full difficulty report](ai-level-benchmark.json)
records group results, seeds, source hashes and executable hashes. Raw games
and exact deployments are in `build/ai-level-benchmark/games.jsonl`.

The earlier 1,800-game comparison against the original v0.2.0 evaluator scored
69.8%: 894 wins, 724 draws and 182 losses, with a paired interval of 68.3–71.3%.
Its [historical report](ai-benchmark.json) retains the original source hashes.
Normal's optimization preserves that evaluator's decision logic.

## Speed work and equivalence

The optimizations calculate source danger once per piece, use a precomputed
neighbor table instead of repeated coordinate arithmetic, and cache rank
matchups and gains for the turn. Resulting-position danger remains recalculated
because vacating a source or capturing a blocker can open a scout ray.
Expected hidden-rank gains were already cached in the planned evaluator.

The frozen `tests/baselines/ai_planned.c` provides the comparison implementation.
Normal and that implementation chose identical moves throughout 30 complete
games, covering **17,417 decisions** and persistent histories for both armies.
Normal also matched the reference and the X16 on 500 fresh positions.

Each level and the reference were measured on the same 500 positions and random
seeds. All levels matched native/X16 decisions, with no mismatches:

| Evaluator | Mean frames | 95th percentile frames | Maximum frames |
| --- | ---: | ---: | ---: |
| Previous planned AI | 20.54 | 29 | 43 |
| Easy | 13.19 | 14 | 14 |
| Normal | 17.14 | 20 | 24 |
| Hard | 31.21 | 37 | 45 |

Normal's maximum is about 44% lower; its average is about 17% lower. These are
observations on the measured corpus, not universal worst-case guarantees.
An additional 200 positions with all rule variants enabled matched on Hard;
the maximum was 55 frames (0.92 seconds). [The speed report](ai-speed.json)
contains all frame samples and source/executable hashes.

The AI bank uses 7,906 of 8,192 bytes for code, constants and private state.
Main RAM retains 126 bytes below the reserved 1 KB C stack. The linker checks
both regions. Shared main-memory configuration holds difficulty; private
working state remains in bank 23.

## Fairness regression

The production caller saves the true board, calls `ai_mask`, invokes the AI
using disclosed enemy casualties, and restores the true board. Masking has no
special exceptions for Spy, Marshal or Flag. Own casualties can inform rescue
planning; undisclosed enemy casualties cannot inform rank estimates.

`make check` tests **15,242 decisions** across all three levels and all 64 rule
combinations. It permutes concealed identities while preserving occupancy,
public movement/revelation bits and the rank inventory. Spy, Marshal and Flag
are explicitly required to appear among the changed identities. Each comparison
starts with identical random state and persistent goals/history. The chosen
move, random consumption, next goals/history and restored view must match.

Under Silent Defense, another **3,644 comparisons** exchange an undisclosed
casualty with a hidden unmoved piece, changing the true remaining rank inventory
without changing the observable position. The AI must still behave identically.
Native protocol tests also ensure that unrevealed defeated defenders do not
enter the known casualty ledger, unrevealed winning defenders stay unknown,
and Scouts and previous disclosures retain their permitted information.

Tactical tests cover immediate victory, spy/marshal combat, miners, scout-ray
escape, lake routing, flag defence, and a Hard reply that avoids exposing an
allied Spy while taking a Scout. Easy retains victory and flag safety checks;
its intentionally weaker planning and greater variation can delay small
captures or mishandle low-value pieces.

The actual banked-game tests check pointer/keyboard selection, saving/restoring
all levels, legacy and invalid save values, masked Hard entry, alternating demo
armies, pause/resume, rescues, menus and sound. Address/undefined-behaviour
sanitizers pass the native tactical/fairness tests.

## Reproduce

```sh
make check
make compare-ai
make benchmark-ai-levels
make test-ai-levels
make parity
python3 tools/parity.py --difficulty easy --positions 500
python3 tools/parity.py --difficulty hard --positions 500
python3 tools/parity.py --difficulty hard --rules 63 --positions 200
make bridge-planned native-planned
python3 tools/parity.py --engine build/feldmarschall-ai-planned --bridge build/BRIDGE-PLANNED.PRG --positions 500
make test-demo test-variants test-sound test-menus test-flow test-dist
```

`tools/benchmark_ai.py --levels --rounds N --jobs J --out DIRECTORY` controls
benchmark size, parallelism and output location. The standard level benchmark
uses 200 paired rounds for each pairing in each of three deployment groups.
`make benchmark-ai` retains the earlier comparison against the original AI.
