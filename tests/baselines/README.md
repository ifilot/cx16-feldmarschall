# Frozen comparison opponent

`ai_v020.c` is the exact pre-upgrade `src/core/ai.c`, preserved for repeatable
comparisons. Do not update it when changing the current AI. `make
native-baseline` compiles it against the same native protocol and rules as the
current engine; `make benchmark-ai` compares the two with side-swapped pairs.

`ai_planned.c` freezes the stronger planned evaluator before speed work and
difficulty levels. `make compare-ai` compares complete games against it,
including persistent goals and histories; `make bridge-planned` builds its
X16 mailbox program for measurements on the same positions.

`ai_levels_20261014.c` and `ai_level_20261014.c` freeze the evaluator and
level configuration from commit `dd702bdc` before endgame work. Keep both
unchanged. `make native-milestone` builds all three levels as
`build/feldmarschall-ai-20261014`. Compare the current engine to this milestone
with `python3 tools/benchmark_ai.py --previous`. Add `--difficulty hard` or
`--difficulty easy` to choose a level.

These snapshots share the current rules, protocol, headers and random generator
to isolate evaluator changes. Rebuild the original Git revision when reproducing
the complete historical engine. Game release numbers and evaluator milestones
are separate identifiers; see [the milestone record](../../docs/ai-milestones.md).

`ai_normal_progress_20261014.c` freezes the independently validated fixed Normal
idle penalty (`make native-progress-baseline`; benchmark with `--progress`).
`ai_adaptive_progress_20261014.c` freezes its successor, whose pressure increases
during quiet turns (`make native-adaptive-baseline`; benchmark with `--adaptive`).
Both snapshots use `ai_level_20261014.c`. Keep all frozen files unchanged.

`ai_coordinated_20261014.c` and `ai_mission_20261014.c` freeze the integrated
cooperative evaluator and mission module. Build with `make
native-coordinated-baseline` or compare with `--missions`.
`make benchmark-ai-progress` now compares against this coordinated milestone.
The coordinator needs `AI_MISSIONS` defined, as in its Makefile target; older
baseline targets intentionally omit that flag.
