# Named Classic AI policies

Every selectable AI has an immutable ID in [registry.json](registry.json), a
descriptive name, an explicit difficulty, a build recipe and a SHA-256-addressed
source archive under `sources/`. The archives contain actual C sources, headers,
fitted models and Python adapters. Rebuilding does not use the current working
tree's evaluator or an ignored historical build directory.

The catalog has 49 policies: historical milestones, current guarded
Normal, retained experimental alternatives and desktop reference teachers. Rejected
experiments are clearly marked; being selectable does not imply acceptance.
Existing experimental run names and results remain intact in
[`docs/ai-experiments.json`](../docs/ai-experiments.json). Earlier one-off policies
that exist only in those evidence archives must be registered before new use.

The main progression is:

| Name / ID | What changed |
| --- | --- |
| Original v1 / `original-v1` | Pre-upgrade v0.2.0 evaluator: local gains, danger and forward movement. |
| Planned v1 / `planned-v1` | Persistent objectives, routing and specialist values. |
| Levels v1 / `levels-v1-{easy,normal,hard}` | Optimized planning and three difficulty policies. |
| Progress v1 / `progress-v1-normal` | Fixed penalty for unproductive quiet moves. |
| Progress v2 / `progress-v2-normal` | Increasing penalty during quiet play. |
| Missions v1 / `missions-v1-{normal,hard}` | Evidence-triggered Miner approach with clearing and scouting support. |
| Guarded Student v1 / `student-guard-v1-normal` | Production learned corrections, protecting assigned support jobs. |
| Material Teacher v1 / `teacher-material-v1-normal` | Desktop sampled-world material search, with mission corrections. |
| Rollout Teacher v1 / `teacher-rollout-v1-normal` | Desktop masked-policy rollouts with strategic utility and mission corrections. |
| Priorities v1 / `priorities-v1-normal` | Rejected priority-class experiment; breaks Scout cooperation. |
| Reconsidered Plans v2 / `plans-v2-normal` | Rejected stalled-sector reconsideration experiment; independent strength and hardware gates fail. |
| Context Rollout Teacher v1 / `teacher-context-v1-normal` | Desktop rollout with guarded-student future policies and retained root strategic state. |
| Context Student v2 / `student-context-v2-normal` | Rejected single compact fit from the context teacher; actual model has 27 nodes / 162 bytes. |
| Linked Scouting v1 / `linked-scouting-v1-normal` | Rejected public information-value experiment requiring a legal conditional follow-up attack. |
| Reply-Aware Teacher v1 / `teacher-replies-v1-normal` | Desktop experiment averaging up to three plausible masked-policy replies; rejected at its development gate. |
| Ranking Student v1 / `ranking-student-v1-normal` | Rejected offline desktop residual ranker; shortlisted training left other legal actions unconstrained. |
| Ranking Student v2 / `ranking-student-v2-normal` | Rejected offline all-action coverage repair; same capacity and features, no demonstrated learning gain. |

The [15 October cycle](../docs/ai-cycle-2026-10-15/README.md) records development,
independent validation and acceptance decisions. `teacher-cold-control-v1-normal`
is the context teacher's diagnostic control without root-state transfer;
`guard-diagnostics-v1-normal` adds forced-history diagnostics to production.
The failed, unbuildable Plans v1 source remains in the cycle's build-failure
record and is absent from the selectable list. Registry status describes the
policy type; the cycle report records whether an experiment passed its gates.
The subsequent [linked-scouting experiment](../docs/ai-linked-scouting-2026-10-15/README.md)
retains one frozen candidate, 1,400 development games and a public follow-up
analysis. It did not pass the gate for independent validation or adoption.
The [reply-aware desktop trial](../docs/ai-reply-teacher-2026-10-15/README.md)
tests multiple plausible first replies against Context Teacher v1 with the same
sample count and horizon. Its 980 development games do not establish a strength
gain over that teacher; no student fit followed.

The [teacher-transfer investigation](../docs/ai-transfer-2026-10-15/README.md)
retains two native desktop ranking models and their offline diagnostics. Neither
passed its learning gate, so no new strength tournament or compression followed.

These names identify **move policies**. Tournaments deliberately give both
participants common referee-generated starting armies to compare their play.
The production game's deployment mixtures are a separate policy; their strength
results must not be attributed to these move-only comparisons.

```sh
python3 tools/ai_registry.py list
python3 tools/ai_registry.py build original-v1 student-guard-v1-normal
build/ai-catalog/student-guard-v1-normal/engine --identity
```

For a new policy, copy an existing catalog entry into a new JSON specification,
give it a new ID/name and description, update its sources, defines, difficulty,
status and model include directories, then register it:

```sh
python3 tools/ai_registry.py register /path/to/new-policy.json
python3 tools/ai_registry.py build missions-v2-normal
```

`register` refuses duplicate IDs, freezes source inputs immediately and compiles
the frozen recipe before publishing it to the selectable list. It does not edit
or regenerate models. Supply generated model headers in an explicit
`include_dirs` directory before registration. A changed model, compilation
define, adapter configuration or difficulty needs a distinct ID. Never edit an
existing entry or overwrite a source archive. Commit the registry and its new
source archive together. Compiler version and executable hashes are recorded at
build time; identical compiler binaries are not included.

A portable tournament embeds the participant recipes and source archives, so
even a policy absent from a later checkout can be restored and rebuilt:

```sh
python3 tools/ai_registry.py restore saved-tournament.fmtour
python3 tools/ai_registry.py build restored-policy-v1-normal
```

Restore refuses conflicting identities. It restores source and metadata, without
executing embedded binaries. See the [tournament desk guide](../docs/tournament-desk.md).
