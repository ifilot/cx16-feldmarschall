# Feldmarschall AI implementation handoff

14 October 2026

The AI speed, difficulty and fairness work is complete and verified. Normal
keeps the previous planned evaluator's decisions while reducing its maximum
measured thinking time from 0.72 to 0.40 seconds. Easy, Normal and Hard are
available in New Game, and every level receives the same concealed enemy view.

All changes are saved in the local repository and remain **uncommitted**.
The X16 runtime, distribution ZIP and local browser build have been rebuilt.
No remote publication or Git push was performed.

## Implemented behaviour

The evaluator caches source danger once per piece, uses a neighbor lookup table,
and caches combat outcomes and gains for each turn. Normal retains persistent
piece objectives, routes around lakes and occupied squares, scout-ray danger
checks, immediate flag defence, and changing specialist values.

Easy skips route planning and introduces more variation. Normal is the default.
Hard checks the opponent's best material reply to six promising moves, weighting
possible outcomes when the target's rank is concealed. It also checks a revealed
moving flag's immediate arrival victory. Hard replaces the existing local danger
penalty with its reply assessment to avoid counting that risk twice.

Click the difficulty button in New Game to cycle levels, or use left/right arrow
keys. Classic changes rules independently of difficulty. Saved games retain the
selected level using spare bits in the existing scene byte; old saves and invalid
encoded levels default to Normal. The file format and size remain compatible.

## Results

The speed comparison used the same 500 positions and seeds for every evaluator.
Native and X16 decisions matched throughout. Timing measures the AI mailbox call,
excluding the game's presentation and animation delays.

| Evaluator | Mean frames | Maximum frames | Maximum seconds at 60 Hz |
| --- | ---: | ---: | ---: |
| Previous planned evaluator | 20.54 | 43 | 0.72 |
| Easy | 13.19 | 14 | 0.23 |
| Normal | 17.14 | 24 | 0.40 |
| Hard | 31.21 | 45 | 0.75 |

Normal matched the previous evaluator on **17,417 decisions across 30 complete
games**, including persistent goals and move histories. Another 200 positions
with all rule variants enabled matched on Hard, with a maximum of 55 frames
(0.92 seconds).

The independent difficulty benchmark played 3,600 games across mixed, random
and preset deployments. Each pairing played 1,200 games with identical
deployments and engine sides swapped. Draws count as half a point.

| Comparison | Wins | Draws | Losses | Score | Paired 95% interval |
| --- | ---: | ---: | ---: | ---: | --- |
| Normal versus Easy | 881 | 174 | 145 | 80.7% | 78.8–82.6% |
| Hard versus Normal | 617 | 86 | 497 | 55.0% | 52.5–57.5% |
| Hard versus Easy | 974 | 67 | 159 | 84.0% | 82.0–85.9% |

No illegal decisions occurred. Hard's advantage over Normal is modest; the
mixed-deployment subgroup alone did not establish an advantage. Strength
measurements use classic rules, not the optional variants or human opponents.

## Fairness guarantees and checks

The production caller saves the true board, masks every undisclosed opposing
rank as unknown, calls the AI with disclosed casualty counts, and restores the
true board. **Spy, Marshal and Flag have no exceptions.** Demo spectators can
see both armies, but each AI still receives only its own permitted view.

The permanent tests verify 15,242 decisions across all three levels and all
64 rule combinations after permuting concealed ranks. They require identical
moves, random consumption, persistent goals/history and restored views. Spy,
Marshal and Flag are explicitly included among the changed identities.

Another 3,644 Silent Defense comparisons change undisclosed casualty inventories
without changing the observable position. Native protocol tests check casualty
and revelation bookkeeping, including winning hidden defenders, Scout disclosure
and previously revealed ranks. Address and undefined-behaviour sanitizers pass.

The AI can infer ranks from public movement, combat revelations and remaining
counts. Difficulty provides no extra knowledge of the true opposing layout.

## Game verification and memory

Passed checks include rules and presets; tactics and hidden-information
invariance; native information bookkeeping; native/X16 parity; keyboard and
pointer difficulty controls; saving/restoring every level; old and invalid saved
values; actual banked Hard execution; menus; game flow; demo mode; optional
variants; music and effects; and distribution boot.

The AI bank uses 7,906 of 8,192 bytes. Main RAM has 126 bytes below the reserved
1 KB C stack. Future code growth needs attention to the linker map.

## Files and artifacts

- [Implementation and detailed evidence](ai-comparison.md).
- [Difficulty benchmark summary](ai-level-benchmark.json).
- [Speed samples and fairness counts](ai-speed.json).
- [Earlier comparison against the original AI](ai-benchmark.json).
- [Updated New Game screenshot](game-settings.png).
- `src/core/ai.c`: evaluator, optimizations and Hard reply checks.
- `src/core/ai_level.c`: public level configuration and shared rank masking.
- `src/scenes/game_settings.c`: difficulty button and keyboard controls.
- `src/scenes/play.c`: masked calls and saved difficulty.
- `tests/ai_test.c` and `tests/native_info_test.c`: tactical and fairness checks.
- `tests/baselines/`: frozen original and planned evaluators; keep them unchanged.
- `tools/benchmark_ai.py`, `tools/compare_ai.py`, `tools/parity.py`, and
  `tools/test_ai_levels.py`: reproducible verification tools.
- `build/ai-level-benchmark/`: complete game records and deployments.
- `build/dist/FELDMARSCHALL.ZIP`: rebuilt distribution.
- `build/site/`: rebuilt local browser version.

## Resume commands

```sh
make
make check
make compare-ai
make test-ai-levels
make benchmark-ai-levels
make parity
python3 tools/parity.py --difficulty easy --positions 500
python3 tools/parity.py --difficulty hard --positions 500
python3 tools/parity.py --difficulty hard --rules 63 --positions 200
make test-demo test-variants test-sound test-menus test-flow test-dist
```

A commit can be reviewed and created later; it should include the implementation,
new tests and tools, frozen baselines, updated documentation and screenshot.
There is no required implementation work left for this request. Possible future
improvements are better endgame progress, broader reply exploration, and separate
strength benchmarks for the optional variants. All 327 difficulty-benchmark draws
reached the referee's 1,000-ply cap.
