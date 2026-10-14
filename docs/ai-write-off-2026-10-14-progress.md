# AI progress handoff

14 October 2026

This is the preceding progress milestone. The latest implementation is the
[coordinated missions handoff](ai-write-off-2026-10-14-missions.md).

The retained improvement is adaptive progress pressure for Normal. Its penalty
for quiet moves by pieces without a reachable objective grows from 12 to 44
when the visible piece count stays unchanged. It resets on a count change,
saturates safely, and keeps independent state for each army. Easy and Hard
retain their previous decision policies.

All implementation, test, baseline, tool, and documentation changes remain
uncommitted. No push or publication was performed. The runtime and distribution
ZIP and local browser package have been rebuilt.

## Evidence and rejected experiments

- The earlier fixed Normal penalty scored 54.8% against the initial three-level
  milestone over 600 held-out games (paired 95% interval 50.9–58.8%).
- Adaptive Normal scored 50.5% against fixed Normal over a further 600 held-out
  games (49.0–52.0%). It ended five of six selected previously capped games:
  three candidate wins and two losses. This is progress on a selected corpus,
  not proof of a population-wide draw reduction or additional strength gain.
- Eight-candidate Hard search scored 51.6% over 600 held-out games
  (48.1–55.0%) and was rejected. A crowded-position Hard progress penalty
  scored 47.5% in development and was also rejected.
- Final difficulty validation played 1,800 games. Normal scored 86.6% against
  Easy, Hard 84.9% against Easy, and Hard 48.8% against Normal (44.8–52.7%).
  Hard superiority over improved Normal is not established; the preset subgroup
  favored Normal. All strength measurements use classic rules.

The [milestone record](ai-milestones.md) explains the policies, evidence and
limitations. The [experiment ledger](ai-experiments.json) contains 16 archived
runs covering 4,794 games, with each decision, reason and source hash. Archives
under `docs/ai-runs/` preserve full game traces and deployments where recorded.
Rejected historical evaluator sources were recovered and verified against
their original hashes. New runs retain whole source snapshots and executable
copies. [Archive integrity](ai-runs/archive-integrity.json) verifies all ledger
archives, evaluator hashes and retained executable hashes.

## Frozen opponents

- Original pre-upgrade v0.2.0: `tests/baselines/ai_v020.c`.
- Planned evaluator: `tests/baselines/ai_planned.c`.
- Initial three levels: `tests/baselines/ai_levels_20261014.c`.
- Validated fixed Normal penalty: `tests/baselines/ai_normal_progress_20261014.c`.
- Adaptive Normal: `tests/baselines/ai_adaptive_progress_20261014.c`.

Keep these unchanged. The current evaluator has source SHA-256
`12b27367845a83448ba0a1ebbefa15aaebb7618af96db5b15dc2e1cbb514358f`.
It differs from the adaptive snapshot only in comments and a test-only counter
accessor; three complete Normal games matched on 943 decisions. Hard matched
the initial three-level snapshot on 1,079 decisions across three games.

## Verification and memory

`make check` passes rules, presets, counter saturation/reset/independence/state
restoration, 15,163 hidden-rank permutations, 3,814 Silent Defense inventory
comparisons, and native disclosure/casualty bookkeeping. These fairness checks
cover all difficulties and all 64 rule combinations. `make test-ai-levels`
passes controls, save compatibility, actual banked execution, and masked ranks.

Normal native/X16 parity passes 100 fresh positions (maximum 24 frames,
0.40 seconds) plus 1,290 repeated decisions over 10 fixed views. Hard parity
passes 100 positions with all optional rules enabled (maximum 49 frames,
0.82 seconds). The new repeated-call bridge initially exposed a cc65 scratch
pointer cache problem in its loop; reading the army before the loop fixed it.
The production AI was not the cause of that mismatch.

AI bank use is 8,099/8,192 bytes, leaving 93 bytes. Main RAM retains 126 bytes
below the reserved 1 KB stack. Further production code growth needs savings.

## Resume

```sh
make check
make test-ai-levels
make benchmark-ai-progress AI_BENCHMARK_FLAGS='--record-moves --phase development'
make benchmark-ai
make benchmark-ai-levels
python3 tools/parity.py --difficulty normal --positions 100
python3 tools/parity.py --difficulty normal --positions 10 --repetitions 129
python3 tools/archive_ai_run.py build/ai-benchmarks/RUN \
  --decision keep --reason 'Explain evidence and decision'
```

`benchmark-ai-progress` now compares against the adaptive milestone. Direct
benchmark selectors `--previous`, `--progress`, and `--adaptive` retain stable
references to the initial, fixed, and adaptive milestones respectively. Use
fresh `--seed-offset` values and `--phase validation` for final strength claims.
Existing output directories and archive files are never overwritten.

`make compare-ai` still compares current decisions to the historical planned
evaluator; intentional policy changes can diverge. Use an explicit frozen
baseline with `tools/compare_ai.py` when testing copies or pure optimizations.

Next work should improve Hard's strategic priorities, study sparse Marshal/Spy
endgames with protected flags, and extend the independent strength referee to
optional variants. Free X16 bank space before adding larger search machinery.
