# Coordinated AI missions handoff

14 October 2026

The shared mission planner is implemented and enabled for Normal and Hard in
the native engine and X16 game. Easy retains its previous policy. The runtime,
distribution ZIP and local browser package have been rebuilt. All changes
remain uncommitted; no push or publication was performed.

## What changed

The army coordinates a miner approach after a disclosed rear bomb provides
evidence of a fortified area. This is a hypothesis about the flag area, not
knowledge of concealed ranks. A relaxed route identifies the first cooperation
job: move a friendly blocker out of the corridor, scout an unknown defender,
or select an appropriate attacker against a known defender. A strict route
checks that support pieces can reach their job. Targets persist separately for
both armies; assignments are re-evaluated after changes in the permitted view.
The tactical evaluator still checks danger, immediate victories and flag safety.

The first prototype guessed an arbitrary concealed back-row target without
supporting evidence. It passed strategic fixtures but scored 48.8% on Normal
and 47.1% on Hard in development, so it was rejected. The retained policy
requires public fortification evidence before starting a speculative mission.

## Independent strength validation

Each level played 600 held-out classic-rule games against its frozen adaptive
predecessor, using mixed, random and preset deployments with sides swapped.

| Candidate | Wins | Draws | Losses | Score | Paired 95% interval |
| --- | ---: | ---: | ---: | ---: | --- |
| Mission Normal versus preceding Normal | 344 | 1 | 255 | 57.4% | 53.7–61.2% |
| Mission Hard versus preceding Hard | 329 | 18 | 253 | 56.3% | 52.7–59.8% |

Another 1,800 games tested current difficulties: Normal scored 85.1% against
Easy, Hard 81.8% against Easy, and Hard 51.2% against Normal (47.5–55.0%).
Hard superiority over Normal remains unestablished. Strength results cover
classic rules and these engine opponents, not optional variants or human play.

The [experiment ledger](ai-experiments.json) now contains 24 runs covering
8,286 games. It preserves rejected and accepted candidates, full source and
executable snapshots, deployments, seeds, moves, results and decision reasons.
[Integrity verification](ai-runs/archive-integrity.json) checks archive hashes,
CRC, evaluator hashes and retained executable hashes. The
[milestone record](ai-milestones.md) describes all implementation stages.

## Implementation and hardware

- `src/core/ai_mission.c`: shared mission selection, routes, scouting and clearing.
- `src/core/ai.c`: tactical evaluation with the mission contribution.
- `src/ui/mission_bank.s`: gateways between tactical bank 23 and mission bank 24.
- `MISSION.BIN`: new required runtime file, loaded before play starts.
- Tactical AI bank: 8,147/8,192 bytes, 45 bytes free.
- Mission bank: 2,175/8,192 bytes, 6,017 bytes free.
- Main RAM: 50 bytes below the reserved 1 KB stack.

Mission code and its scratch maps occupy the additional bank; enlarging the
planner can use that space while keeping the tactical interface small. Core
and main RAM headroom remain tight. The build/linker checks all bank capacities.

Normal native/X16 parity passed 100 positions, maximum 29 frames (0.48 seconds).
Hard parity passed 100 positions with all variants, maximum 49 frames
(0.82 seconds). Another 1,290 repeated Normal decisions passed. Eight actual
banked fixtures verify route clearing and scouting for both armies and both
levels, including preserved masked views and bank 22/23/24 restoration.

`make check` passes tactics, strategy fixtures, rules/presets, 15,163 hidden-rank
comparisons across all levels and 64 rule combinations, 3,836 Silent Defense
inventory comparisons, and native disclosure/casualty bookkeeping. Address and
undefined-behaviour sanitizers pass; leak detection was disabled because the
host's ptrace environment cannot run LeakSanitizer. Sound, demo, save/difficulty
compatibility and packaged distribution boot checks pass.

Integrated code matched the validated prototype on 1,378 decisions across
six complete games. The frozen coordinated baseline matched another six games
on 1,378 decisions, and a 12-game paired integrity run scored exactly 50%.

## Frozen milestone and resume

Keep these snapshot files unchanged:

```text
0e2f81ad7ce5634d0becf6259fc44445b9f5885ca13df9d8884ca2d1afb63aa3  ai_coordinated_20261014.c
6d20e7e6bc84ef97ddb70ef42e096139e3a6ec59fc3abc1df819f503bb994a63  ai_mission_20261014.c
```

Both are under `tests/baselines/` and use the frozen `ai_level_20261014.c`.
The coordinated build needs `AI_MISSIONS`, as supplied by the Makefile target.
Older baseline targets intentionally omit that flag.

```sh
make check
make test-ai-missions test-ai-levels test-sound test-demo test-dist
make native-coordinated-baseline
make benchmark-ai-progress AI_BENCHMARK_FLAGS='--record-moves --phase development'
python3 tools/benchmark_ai.py --adaptive --difficulty hard --record-moves
python3 tools/parity.py --difficulty normal --positions 100
python3 tools/parity.py --difficulty normal --positions 10 --repetitions 129
```

`benchmark-ai-progress` now compares against coordinated missions (`--missions`).
Earlier reference selectors remain stable: `--previous`, `--progress`, and
`--adaptive`. `make native-missions` builds the same current mission policy as
`make native`. Archive each completed run with `tools/archive_ai_run.py` and
use fresh seed offsets for held-out validation.

The next architectural opportunities are richer beliefs about the suspected
flag sector, remembering that sector after a guard is removed, and explicit
specialist preservation/escort decisions. The current planner remembers a
target square and handles the first route obstruction; it does not yet track
individual enemy probability distributions or complete multi-step mission
completion histories. Deeper search should use these improved strategic
features rather than expanding the old material-only reply check alone.
