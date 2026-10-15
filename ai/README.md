# Named Classic AI policies

Every selectable AI has an immutable ID in [registry.json](registry.json), a
descriptive name, an explicit difficulty, a build recipe and a SHA-256-addressed
source archive under `sources/`. The archives contain actual C sources, headers,
fitted models and Python adapters. Rebuilding does not use the current working
tree's evaluator or an ignored historical build directory.

The initial catalog has 39 policies: historical milestones, current guarded
Normal, retained experimental alternatives and the two desktop teachers. Rejected
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

`register` refuses duplicate IDs and freezes source inputs immediately. It does
not edit or regenerate models. Supply generated model headers in an explicit
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
