# AI deployment selection and next development cycle

14 October 2026

Classic Normal and Hard now select varied deployments from CORNER FORTRESS,
Evolved 2 and Evolved 3. The frozen mixtures passed independent validation
against protected random deployment. Classic Normal now adds a validated compact
student with a cooperation guard to the mission evaluator. Other levels and
variants retain mission scoring. Easy and optional variants retain protected
random deployment.

## Deployment policy and independent results

Fresh development used all four retained fixed layouts plus protected random,
1,400 games per level. Mixture weights maximize the measured development score
on an integer grid of tenths, with at least three positive weights and no layout
above 50%. Each level's weights were frozen before validation began.

| Level | CORNER FORTRESS | Evolved 2 | Evolved 3 |
| --- | ---: | ---: | ---: |
| Normal | 50% | 40% | 10% |
| Hard | 40% | 50% | 10% |

Evolved 1 was included in development and received zero weight on both levels.
Development seeds were 51,261,014 and 52,261,014; validation seeds were
53,261,014 and 54,261,014. Each validation played 5,040 games: mixture, fortress
and random control each played 1,680. Seven equally weighted opponent-layout
families each supplied 24 fresh layout blocks. Every block includes five
opponents and both engine sides. Mixture selection is independent of the
opponent and shared by both sides and all five opponents in its block.

| Level and deployment | Score | Capped games |
| --- | ---: | ---: |
| Normal mixture | 90.09% | 7 |
| Normal fortress | 90.86% | 9 |
| Normal protected random | 87.35% | 11 |
| Hard mixture | 91.43% | 50 |
| Hard fortress | 91.04% | 52 |
| Hard protected random | 87.08% | 114 |

| Frozen mixture comparison | Difference in percentage points | Block 95% interval |
| --- | ---: | --- |
| Normal versus random | +2.74 | +0.39 to +5.18 |
| Normal versus fortress | -0.77 | -1.90 to +0.33 |
| Hard versus random | +4.35 | +2.38 to +6.31 |
| Hard versus fortress | +0.39 | -1.01 to +1.82 |

The predeclared promotion gate requires the mixture-minus-random block interval
to exclude zero in its favour, with the diversity constraints above. Both levels
pass. Neither comparison establishes a difference from fortress alone.
Intervals resample complete blocks within each family, bundling all opponents,
both sides and matched controls. The scores describe Classic play against this
fixed engine league; they do not measure human strength. Capped-game counts
are reported descriptively, without a separate significance claim.

Full per-family scores and capped counts, opponents, trials, actual selections,
frozen policies, source and executable snapshots, moves and integrity reports
are retained in four `selection-*-20261014.zip` archives under `ai-runs/` and
the experiment ledger. Normal validation selected fortress/Evolved 2/Evolved 3
in 88/64/16 blocks; Hard selected them in 67/86/15 blocks.

## Runtime implementation and verification

`src/core/ai_deploy.c` holds three 40-byte rank arrays and the selection function
in mission bank 24. The existing bank gateway restores the caller's bank.
Rejection sampling maps the 65,535 nonzero xorshift outputs onto ten equally
likely tickets. Normal uses 5/4/1 tickets and Hard uses 4/5/1. The layout mapping
preserves front-row-first order and columns a-j on both armies. Only the selected
army's home squares change; each inventory has the legal 40 pieces.

The pre-game opponent and new-game/demo paths use `setup_ai`; the player's Random
button still uses `setup_random`. Easy, invalid levels and non-Classic games
use the existing protected random function with its original RNG consumption.
Save formats and public-history handling do not change.

Native tests exercise all 65,535 seeds on both levels and both orientations,
including rejected draws, untouched opposing home squares and exact RNG
continuation. Fallback tests cover all 63 nonzero rule combinations. Another
150 actual banked calls match native layouts and RNG, covering every ticket,
all five rejected first draws, both armies, Easy and representative variants.
The gateway restores bank 22 after each call.

The current production tactical bank remains 8,147/8,192 bytes. After student
integration and relocation of random deployment into bank 24, mission bank use
is 7,512/8,192 bytes. The first free main-RAM address is 0x98B7, leaving 585 bytes before the
reserved 1 KB stack at 0x9B00. No stack reservation was reduced.

`make all check`, deployment selection tests, flow, demo, difficulty/save controls,
eight banked mission fixtures and distribution boot pass. The rebuilt browser
package has all 34 runtime files byte-identical to the X16 build, and its ZIP
download matches the distribution. The [runtime manifest](ai-selection/manifest.json)
links the original deployment checkpoint. The later
[student production manifest](ai-student-production/manifest.json) retains the
current runtime. Archive verification passes for 82 runs and 57,226 games.

## Reproduction

```sh
make native native-coordinated-baseline native-baseline native-planned native-adaptive-baseline
python3 tools/benchmark_ai_selection.py --out NEW_NORMAL_DEV --difficulty normal --seed 51261014 --rounds 4
python3 tools/benchmark_ai_selection.py --out NEW_HARD_DEV --difficulty hard --seed 52261014 --rounds 4
python3 tools/benchmark_ai_selection.py --out NEW_NORMAL_VAL --difficulty normal --seed 53261014 --rounds 24 --policy NEW_NORMAL_DEV/policy.json
python3 tools/benchmark_ai_selection.py --out NEW_HARD_VAL --difficulty hard --seed 54261014 --rounds 24 --policy NEW_HARD_DEV/policy.json
python3 tools/verify_ai_selection.py NEW_NORMAL_VAL
python3 tools/verify_ai_selection.py NEW_HARD_VAL
make all check test-ai-selection test-ai-selection-banked
make test-flow test-demo test-ai-levels test-ai-missions
make dist site test-dist
```

Use new seeds for further strength claims. Existing run directories and archives
must not be overwritten.

## Remaining work in the requested order

1. **Deployment selection:** development, frozen policy validation, runtime
   integration, distribution/browser checks and retained runtime evidence complete.
2. **Focused diagnostics:** complete. The [18-case set](ai-mission-cases/README.md)
   contains reconstructed permitted views, legal alternatives, public histories
   and two controls with permanent direct flag-route obstruction. It is quarantined
   from new strength games; diagnostic metadata never enters AI features.
3. **Mission experiments:** seven isolated versions tested in 3,920 development
   games, covering progress/reconsideration, contradictory fortification evidence,
   Miner preservation, escort and Scout preservation. None earned promotion.
   The subsequent guarded student avoids two specialist losses in the diagnostic
   set and scores 54.0% (51.8–56.2%) against the frozen mission baseline over
   1,400 independent Classic Normal games. Isolated failed heuristics remain off.
4. **Mission hardware gate:** complete for the adopted guarded student. Bank/main
   RAM, stack guards, hidden-information invariance, both armies with persistent
   histories, timing, bank restoration and cold history on save/load pass.
5. **Stronger desktop teacher:** Classic Normal strength gates passed. A frozen
   masked-policy rollout successor scores 71.0% against missions and 54.0%
   against the earlier material teacher in independent 1,400-game comparisons.
   Public-only history, quiet strategy and focused cases are covered. The
   [teacher and student handoff](ai-teacher/README.md) records mechanisms and limits.
6. **New student:** full/cold-history labels and grouped fits complete. The first
   fit scores 37.1%. Representative development data produces a compact model
   with independent score 56.25% (53.96–58.54%), but it fails an existing
   Scout-support tactic. Inventory features score 51.4%; removing quiet
   corrections passes tactics but scores 50.0%. A cooperation guard preserves the
   assigned actor's quiet priorities and retains a reliable 54.0% independent
   score. It passes diagnostics, fairness and X16 checks and is adopted for
   Classic Normal. The matched five-opponent league check establishes no overall
   gain; decoys remain a weakness. Sources, models and rejections are retained.
7. **Variant strength:** extend the referee and opponents to individual variants
   and representative combinations, test Normal and Hard independently and use
   results to decide whether variant-specific tuning is justified.
8. **Checkpoints:** retain sources, executable identities, seeds, traces and each
   acceptance/rejection decision; update the handoff and commit completed changes.

The full requested cycle remains in progress. Optional-variant strength benchmarks
must still extend the referee and opponents, then validate Normal and Hard using
the retained production policy and close that stage with its own checkpoint.
