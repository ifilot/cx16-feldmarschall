# AI cycle completion audit

The requested cycle is complete. Classic Normal uses the validated compact
student with a cooperation guard, both deployment mixtures are retained, and
optional-rule strength has been measured separately for Normal and Hard.
The [original objective](objective.txt) is preserved alongside the
[machine-checked audit](audit.json).

| Original requirement | Result and authoritative evidence |
| --- | --- |
| Define and validate varied deployment selection | Frozen three-layout mixtures pass independent Normal and Hard validation, 5,040 games per level, against random and Fortress controls across seven families and five opponents. [Selection handoff](../ai-next-cycle-2026-10-14.md), [runtime manifest](../ai-selection/manifest.json). |
| Integrate the successful deployment policy | Actual banked selection, legal inventories, both orientations, RNG continuation, deployment flow, demo and packages pass. Later integration also verifies 180 banked selection/random calls. [Production evidence](../ai-student-production/manifest.json). |
| Produce actionable public diagnostics | Eighteen distinct cases cover decoys, repetition, Miner approaches, specialist losses and blocked controls, with legal alternatives and oracle exclusion. [Focused cases](../ai-mission-cases/README.md). |
| Test isolated mission improvements and retain a successful change | Seven isolated versions, 3,920 games, remain rejected. The subsequent guarded student avoids two disclosed specialist losses and scores 54.0% against frozen missions in 1,400 fresh games, interval 51.8–56.2%. [Development and adoption](../ai-teacher/README.md). |
| Validate accepted changes on X16 | Both armies match native over 80 persistent turns; cold parity, fairness, timing, stack guards, bank restoration, saves and package checks pass. Current game source identity matches the tested build. [Runtime manifest](../ai-student-production/manifest.json). |
| Establish a stronger public-input teacher | Frozen masked-policy rollouts score 71.0% against missions and 54.0% against the earlier material teacher, each over 1,400 independent games. Search, public observations and limits are retained. [Teacher handoff](../ai-teacher/README.md). |
| Train and independently evaluate a compact student | Full/cold labels, disjoint grouped splits, the 31-node/186-byte model, rejected alternatives, fresh strength and target gates are retained. [Student evidence](../ai-student-production/manifest.json). |
| Benchmark individual and combined variants and decide on tuning | Six individual variants, four combinations and Classic each receive 700 games per level. All 15,400 final games and 3,588,284 plies replay exactly; tuning priorities are documented. [Variant results](../ai-variants/README.md). |
| Preserve reviewable checkpoints | Sources, executable identities, seeds, traces, models and acceptance/rejection decisions are retained. The ledger verifies 135 archives and 76,686 games, including earlier cycles and discarded work. [Ledger](../ai-experiments.json), [integrity report](../ai-runs/archive-integrity.json). |

Accepted checkpoints include `100ca19` for deployment integration, `a8667b3` for
diagnostics and mission experiments, `d3d4cb7` for teacher/student evidence, and
`8aa0b46` for the adopted student. The repository commit containing this audit
closes the variant stage and the full requested cycle.

The deployed student occupies 186 bytes of model data. Mission bank use is
7,512/8,192 bytes, tactical use 8,147/8,192, and main RAM leaves 585 bytes before
the reserved 1 KB stack. The retained production sample reaches 39 frames per
cold decision and matches the browser/distribution artifacts. None of the
rejected mission heuristics or inventory-feature experiments is enabled.

The measured gains concern the stated Classic distributions and computer
opponents. The student establishes no overall gain in its separate matched
league check, and decoys remain a weakness. The variant results justify future
experiments on Hard tie-rule endings, exploding-Bomb decisions and all-options/
rescue interactions. Designing and promoting those policies is future work;
the requested benchmarks and tuning decision are complete.

To repeat the completion audit in the retained workspace:

```sh
python3 tools/audit_ai_cycle.py --variants build/ai-variants/validation-r1 \
  --out NEW_AUDIT.json
```

The individual handoffs provide commands for new experiments and restoring
retained evidence. Use fresh output directories and seeds for future strength
claims, and preserve the current final cohorts as validation records.
