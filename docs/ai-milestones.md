# AI milestones and benchmark records

The starting strength baseline is the pre-upgrade v0.2.0 evaluator. Game
release versions do not uniquely identify subsequent evaluator changes.

| Milestone | Preserved implementation | Evidence |
| --- | --- | --- |
| Pre-upgrade v0.2.0, commit `802ee65` | `tests/baselines/ai_v020.c` | Starting opponent; historical 600-game rating was already recorded under v0.1.0, not a direct release comparison. |
| Planned evaluator before optimization | `tests/baselines/ai_planned.c` | `ai-benchmark.json`: 69.8% against the starting opponent over 1,800 games. |
| Three levels, 2026-10-14, commit `dd702bdc` | `tests/baselines/ai_levels_20261014.c` and `ai_level_20261014.c` | `ai-level-benchmark.json`, `ai-speed.json`, and `ai-comparison.md`. |
| Fixed Normal objective progress | `tests/baselines/ai_normal_progress_20261014.c` | Held-out 600-game comparison and full move records in `ai-runs/20261014-normal-progress-validation.zip`. |
| Adaptive Normal progress | `tests/baselines/ai_adaptive_progress_20261014.c` | Held-out strength comparison, selected stall corpus, and difficulty ordering; see the experiment ledger. |
| Coordinated missions | `tests/baselines/ai_coordinated_20261014.c` and `ai_mission_20261014.c` | Normal 57.4% and Hard 56.3% against adaptive predecessors, 600 held-out games each. |

The three-level snapshot hashes are:

```text
0ce3aadea07736cd3768ae6e0a2e122a199c45221b349e579b6ada3fc76639ab  ai_levels_20261014.c
2f7f5f3c7acbda776c655974ea097c9dbcf3ea3aca3cf12be8e7f333a0bb4c48  ai_level_20261014.c
```

The fixed Normal evaluator has SHA-256
`518ff6b6882b83974b006c6e20ea92e4c3202214623814d2af2cf2c8d2787e34`.
The adaptive snapshot has SHA-256
`464b6f4ff341bc47686ea08fb0ac5bb7d4477b3d7492387c506830320a13b01f`.
The pre-mission evaluator added a test-only counter accessor and comments;
its production decisions matched that snapshot. The current evaluator also
includes coordinated missions.

## Running comparisons

```sh
make benchmark-ai                         # current versus starting baseline
make benchmark-ai-progress                # current versus preceding milestone
make benchmark-ai-progress AI_BENCHMARK_FLAGS='--difficulty hard'
make benchmark-ai-levels                  # current difficulty ordering
make benchmark-ai-levels AI_BENCHMARK_FLAGS='--record-moves'
```

Default runs create a unique directory under `build/ai-benchmarks/`, containing
`provenance.json`, `games.jsonl`, and `summary.json`. An explicit `--out` must
name a new directory; reruns refuse to overwrite existing records. Override
rounds, jobs, and output with `AI_BENCHMARK_FLAGS`.
Use `--seed-offset` to select fresh deployment sequences while keeping the
same paired match design.
New runs also retain `sources.zip` and private executable copies in `engines/`;
matches execute these copies, so rebuilding during a run cannot change its
participants. Source archives include dirty and untracked implementation files.

Provenance records the Git revision and worktree status, hashes of tracked
core/protocol/tool/baseline sources and Makefile, evaluator and level hashes,
engine commands and executable hashes, seeds, deployment groups, ply cap, and
confidence method. A dirty revision alone cannot reconstruct changes: retain
the corresponding source changes when archiving a development result.
Native build flags are specified in the recorded Makefile; executable hashes
identify the actual builds. These records do not archive compiler binaries.

Runs use identical deployments with engine sides swapped. Draws count as half
a point; confidence intervals resample complete pairs. Development sampling
must not be mistaken for independent validation. Benchmark seeds remain fixed
for comparability; use fresh held-out seeds for final strength claims.

`build/` is ignored by Git. Unique directories prevent local overwrites but
are not backups. Commit milestone summaries in `docs/` and archive the matching
full run directories with `tools/archive_ai_run.py` for long-term evidence. The detailed
3,600-game historical records referenced by the previous handoff are absent
from this checkout; the committed summary survives.

## Endgame investigation

Generate complete move traces with `--record-moves`, then run:

```sh
python3 tools/analyze_ai_endgames.py build/ai-benchmarks/RUN/games.jsonl
```

The analyzer replays capped classic-rule games, checks every move, and reports
remaining ranks, the number of plies since the last battle, and distinct moves
in the last 100 plies. These are stall symptoms, not proof that a game was
winnable. Inspect representative positions before changing evaluator behavior.

### Initial diagnostic sample

A 90-game sample (five paired rounds per deployment group and level pairing)
produced seven capped games. Four had no battle in the last 100 plies; their
last battles were 319, 759, 892, and 909 plies before the cap. Both armies still
had miners in these four games. The last 100 plies contained 48–68 distinct
directed moves, so the symptoms extend beyond a single two-square chase.
The other three capped games had battles within their last seven plies.

This is a development diagnostic, not a new strength estimate. In particular,
Hard/Normal stalls can begin while substantial armies remain: investigate
objective selection, blocked routes and unwillingness to engage before treating
all caps as late endgame problems. The replay below examines goals and move
scores in one such position using public knowledge.
Losing all miners does not explain the four long quiet tails in this sample.

The [sample archive](ai-runs/20261014-initial-sample.zip) preserves deployments,
seeds, full move traces, provenance, the benchmark summary and replay analysis.
The frozen milestone also matched the current engine on 2,955 decisions across
six complete games (two per difficulty). A 12-game Normal/milestone smoke
comparison scored exactly 50%; this verifies the comparison setup, not strength.

The recorded mixed-deployment Hard/Normal game with seed 33476 can be replayed
through all 1,000 plies. In the original evaluator, around ply 180 several
front pieces had reachable enemy goals, but their approach moves scored below
quiet moves by rear pieces with no goal. The [trace](ai-runs/20261014-stall-trace.txt)
records goals, move scores, and choices for plies 180–189. For future traces:

```sh
make native-trace
python3 tools/replay_ai_game.py build/ai-benchmarks/RUN/games.jsonl \
  --seed SEED --comparison COMPARISON --red ENGINE \
  --trace-start 180 --trace-end 190
```

Replay requires the evaluator binary that generated the recorded moves; it
checks every choice and stops at the first divergence. The trace build emits
candidate scores and goal choices only while explicitly enabled by the replay
tool, preserving the native engine's normal line protocol.

## Normal objective progress experiment

The replay showed Normal choosing quiet moves by pieces without a reachable
enemy objective while approach moves scored poorly under local danger and
random variation. Normal now subtracts 12 from a quiet move by such a piece.
Attacks, moves by pieces with a reachable goal, and Easy keep their previous
scoring. Hard keeps its previous scoring and reply search: an early attempt to
apply the penalty to Hard displaced a safe defensive move, and the existing
reply tactic test caught it.

The held-out comparison used 100 side-swapped rounds in each deployment group,
with deployment seed offset 2,000,000. Normal scored 54.8% against the frozen
Normal milestone: 326 wins, 6 draws, 268 losses over 600 games. The paired 95%
interval was 50.9–58.8%. The random-deployment group scored 60.2%; mixed and
preset groups scored 52.2% and 52.0%, with intervals including 50%. Six games
reached the 1,000-ply cap; four had at least 100 plies since the last battle.
The sample establishes a modest strength gain overall. It does not establish
that the change reduces long stalls, and the remaining capped games merit more
work. The [validation archive](ai-runs/20261014-normal-progress-validation.zip)
contains all deployments, seeds, moves, provenance, per-game results, and
endgame replay analysis.

Easy and Hard matched the frozen three-level milestone on 2,386 and 1,079
complete-game decisions respectively. Native and X16 Normal decisions matched
on 200 positions (maximum 24 frames, 0.40 seconds). `make check` passed
15,163 concealed-rank comparisons and 3,814 Silent Defense inventory
comparisons across all levels and 64 rule combinations. The X16 AI bank uses
7,941 of 8,192 bytes after this change.

## Adaptive progress and Hard experiments

Normal's idle penalty now grows from 12 to 44 over quiet turns, and resets
when the visible board piece count changes. The state is independent for each
army, saturates after 128 quiet decisions, and is included in fairness
snapshots. The policy uses public occupancy counts; concealed ranks provide
no additional input.

On the six capped games selected from the preceding validation, the adaptive
candidate ended five games: three candidate wins and two losses. One remained
capped. The reference engines reproduced all six original caps exactly. The
[probe record](ai-runs/adaptive-stall-probe.json) preserves every move and
deployment. This selected corpus demonstrates progress in those positions,
not a population-wide draw-rate reduction. The remaining game had no miners
and no route to either flag even after ignoring mobile blockers; victory by
eliminating enemy movers remains possible. See the
[classification](ai-runs/original-stall-classification.json).

A fresh 600-game comparison against fixed Normal scored 50.5% (302 wins,
2 draws, 296 losses; paired 95% interval 49.0–52.0%). The change is retained for
its progress behavior; a further strength gain was not established. An
eight-candidate Hard reply search scored 51.6% over 600 fresh games, interval
48.1–55.0%, and was rejected. A crowded-position Hard idle penalty also failed
to improve development results and was rejected. Hard retains six candidates.

The final difficulty comparison played 1,800 games, 600 per pairing. Normal
scored 86.6% against Easy; Hard scored 84.9% against Easy and 48.8% against
Normal (paired 95% interval 44.8–52.7%). **Hard superiority over improved Normal
is not established.** The preset subgroup favored Normal. Difficulty labels
therefore describe different policies, not guaranteed strength ordering across
deployments. These strength benchmarks use classic rules.

The [experiment ledger](ai-experiments.json) records each archived run, source
hash, results, decision and reason. Historical rejected evaluator sources were
recovered and verified against their original SHA-256 hashes before archiving.
Those older archives preserve `candidate.c`; newer archives contain the whole
source snapshot. For a completed future run:

```sh
python3 tools/archive_ai_run.py build/ai-benchmarks/RUN \
  --decision keep --reason 'Evidence and reason for retaining this candidate'
```

Final checks include counter saturation/reset/independence/snapshot tests,
15,163 hidden-rank comparisons, 3,814 Silent Defense inventory comparisons,
rules and native information bookkeeping, and real banked difficulty execution.
Normal matched native/X16 on 100 fresh positions (maximum 24 frames) and on
1,290 repeated decisions across 10 fixed views. Hard matched on 100 positions
with all optional rules enabled (maximum 49 frames). Repeated-call testing
found and fixed a cc65 scratch-pointer cache bug in the new bridge loop; it was
a test-harness issue. JSON parity evidence is archived under `ai-runs/`.
The AI bank now uses 8,099 of 8,192 bytes; main RAM headroom remains 126 bytes.

The next experiments should improve Hard's strategic priorities before further
reply expansion, test sparse Marshal/Spy endgames with protected flags, and
extend the independent strength referee to optional variants. Further X16 code
growth first needs bank-space savings. Retain the current adaptive snapshot as
the immediate comparison opponent, alongside the original v0.2.0 baseline.

## Coordinated missions (current)

Subsequent strategy exploration tested sector memory, dynamic capability values,
selective capture/recapture search, purposeful reconnaissance, occupancy beliefs,
and the inference/reconnaissance combination in 2,520 additional games. None
showed a reliable gain over this milestone, which remains current. Final direct
validation against original pre-upgrade v0.2.0 played another 1,200 games:
Normal scored 80.1% (77.2–82.9%) and Hard 75.8% (72.7–78.8%). See
[strategy research and results](ai-strategy-research.md) for the rejected
prototypes, primary sources, and larger architectural opportunities.

Normal and Hard now share an army-level approach mission. Revealed rear bombs
are evidence of a fortified area, rather than proof of a flag location. A
relaxed path identifies future cooperation jobs: clear a friendly blocker out
of the corridor, scout an unknown blocking enemy, or use a suitable piece to
remove a known defender. A strict path ensures the chosen support piece can
actually approach its assigned enemy. Tactical danger, immediate wins, and
flag defence remain in the existing evaluator. Remembered targets are tracked
independently for both armies and included in fairness snapshots.

The first prototype assigned missions to arbitrary hidden back-row targets.
It passed strategic fixtures but scored only 48.8% for Normal and 47.1% for
Hard in development, and was rejected. The retained policy waits for public
fortification evidence. Its held-out comparisons against the frozen adaptive
predecessor scored 57.4% for Normal (53.7–61.2% paired 95% interval) and 56.3%
for Hard (52.7–59.8%), over 600 games each. The source and executable snapshots
and every move are retained in the experiment ledger.

Final difficulty validation played another 1,800 games: Normal 85.1% against
Easy, Hard 81.8% against Easy, and Hard 51.2% against Normal (47.5–55.0%).
Both policies improved against their own predecessors; an advantage of Hard
over current Normal is still not established. All strength evidence is classic.

`MISSION.BIN` holds the coordinator in bank 24. Bank 23 holds tactical AI,
and assembly gateways preserve bank 22/23/24 nesting and 16-bit score returns.
The tactical bank uses 8,147 bytes, the mission bank 2,175 bytes, and main RAM
has 50 bytes below the reserved stack. Eight real banked cooperation fixtures
cover both jobs, both armies and both planned levels. Current Native/X16 parity
matched on 100 Normal positions (maximum 29 frames), 100 Hard positions with
all variants (maximum 49 frames), and 1,290 repeated Normal decisions. Native
information checks, all tactical/fairness tests, sound, demo, saves and packaged
distribution boot pass. Source integration matched the validated prototype
on 1,378 decisions across six complete games. Frozen copies matched another
1,378 decisions across six games.

`make benchmark-ai-progress` now uses the coordinated baseline. Select older
references directly with `--previous`, `--progress` or `--adaptive`; `--missions`
selects the current frozen coordinator. `make test-ai-missions` runs both native
strategy fixtures and the actual banked game checks.
