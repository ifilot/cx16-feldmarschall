# Named Classic AI policies

Every selectable AI has an immutable ID in [registry.json](registry.json), a
descriptive name, an explicit difficulty, a build recipe and a SHA-256-addressed
source archive under `sources/`. The archives contain actual C sources, headers,
fitted models and Python adapters. Rebuilding does not use the current working
tree's evaluator or an ignored historical build directory.

The catalog has 56 policies: historical milestones, current guarded
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
| MS-DOS Stratego 1990 v1 / `msdos-1990-v1-normal` | Original 16-bit Colonel AI under instruction-counted headless emulation; original hidden-rank access. |
| MS-DOS Stratego 1990 v2 / `msdos-1990-v2-normal` | Same original AI with faster native-block execution and a watchdog; recommended DOS reference. |
| DIAGNOSTIC Context Teacher v1 / `teacher-context-flag-spy-diagnostic-v1-normal` | Context Teacher with privileged enemy Flag/Spy identities; experimental information test only. |
| DIAGNOSTIC Flag-only Context Teacher v1 / `teacher-context-flag-diagnostic-v1-normal` | Context Teacher with only the enemy Flag identified; Spy and other concealed ranks remain hidden. |
| DIAGNOSTIC Context Teacher v1 / `teacher-context-truth-diagnostic-v1-normal` | Context Teacher with every surviving enemy rank known; experimental information test only. |
| Information Lifetime Teacher v1 / `teacher-info-lifetime-v1-normal` | Fair desktop experiment preserving Scouts and Sergeants for future disclosures. |
| Flag Corridor Recon Teacher v1 / `teacher-info-corridor-v1-normal` | Fair desktop experiment routing weak investigators toward supported uncertain Flag approaches. |
| Response-Aware Probe Teacher v1 / `teacher-info-followthrough-v1-normal` | Fair desktop experiment pricing sacrificial probes against a conservative enemy response and continuation. |

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

The [MS-DOS 1990 framework](../docs/msdos-1990-framework-2026-10-15/README.md)
adds a fast original-code opponent. Its original privileged knowledge is explicit;
reference failures remain unscored, rather than being counted as wins or losses.

The [fresh desktop-versus-DOS comparison](../docs/ai-vs-msdos-2026-10-15/report.json)
records 420 Classic attempts on common armies and seeds. Guarded Student scored
28.9%, Rollout Teacher 30.4%, and Context Teacher 28.3%; six DOS errors were
unscored. Paired intervals establish no teacher improvement over production
against this opponent. The directory retains the frozen plan, analysis script,
three portable tournaments and Qt6 review captures.

The [information pilot](../docs/ai-information-pilot-2026-10-15/report.json)
compares the same Context Teacher with ordinary masked input, enemy Flag/Spy
identities, or all surviving enemy ranks. Across 840 attempts, pilot scores were
31.8% / 54.7% / 67.9%; fresh validation scores were 29.6% / 47.5% / 61.8%.
The Flag/Spy validation gain over masked play was 16.5 percentage points on
matched complete pairs (95% interval +8.8 to +24.6). Seven DOS errors across
both cohorts were unscored. Both privileged policies are diagnostic-only;
production and all previously registered policies remain unchanged. The frozen
plan, policies, source snapshot, checks, six portable tournaments and labelled
Qt6 captures are retained alongside the report.

The [Flag-only diagnostic](../docs/ai-flag-only-2026-10-15/result.json) isolates
enemy Flag knowledge while leaving the Spy and other concealed ranks masked.
Across a fresh matched 840-attempt cohort, honest / Flag-only / Flag+Spy scores
were 27.2% / 43.9% / 41.9%. Flag-only gained 15.4 percentage points on complete
matched pairs (95% interval +10.2 to +20.6). Adding Spy knowledge changed score
by -1.5 points (95% interval -5.8 to +3.1), so this test found no additional
Spy benefit. Seven DOS errors were retained and unscored. The frozen diagnostic,
masking and hidden-Spy permutation tests, all-state replays and Qt6 captures
are preserved; production remains unchanged.

The [fair information-strategy comparison](../docs/ai-fair-information-2026-10-15/report.json)
preserves three independent desktop experiments and 2,030 Classic attempts.
Fresh DOS validation scored 30.0% for Context Teacher, 29.2% for Information
Lifetime, 23.9% for Flag Corridor Recon and 26.7% for Response-Aware Probing.
None passed the declared strength criteria, so none is promoted. Lifetime
reduced weak attacks into known losing fights; Corridor Recon gathered more
disclosures but significantly reduced DOS score. All candidates use public
enemy information only. Source snapshots, paired intervals, activity counts,
decisions, replay audits and all fourteen Qt6-reviewable tournaments remain
available in that directory; production remains unchanged.

These names identify **move policies**. Tournaments deliberately give both
participants common referee-generated starting armies to compare their play.
The production game's deployment mixtures are a separate policy; their strength
results must not be attributed to these move-only comparisons.

`teacher-calibrated-beliefs-v1-normal` is a separate Classic desktop experiment.
It replaces the Context Teacher's rough behavioral sampling weights with frozen
categorical likelihoods from public origin, movement and approach/retreat history.
Exact remaining rank counts and public masks constrain every sampled army;
sequential-proposal importance correction avoids treating greedy placement as
the desired posterior. Eight sampled armies, four-ply masked continuations,
root context and move evaluation are unchanged. The model is fitted on complete
development game pairs, calibrated on other pairs and frozen before fresh
strength validation. No opponent setup or referee labels enter the playing
policy. Its plan, fitted-model diagnostics and reviewable results are in
`docs/ai-calibrated-beliefs-2026-10-15`; run `python3 tools/belief_experiment.py
--help` for the reproducible stages. This is not a production replacement.
Fresh validation scored 30.5% against DOS versus 27.8% for the unchanged teacher;
the paired gain was +2.75 percentage points (95% interval -2.0 to +7.5).
Direct play scored 53.4% (95% interval 48.6% to 58.2%). Neither strength gate
passed, so the policy remains experimental. The model improved Flag/Spy
localization, while overall eight-world prediction quality did not improve.
See `docs/ai-calibrated-beliefs-2026-10-15/result.json` for the full decision.

`teacher-probability-control-v1-normal` and `teacher-kl-restrained-v1-normal`
isolate a different Classic hypothesis: short search may overfit the simulated
opponent. Both sample a move from probabilities based on the existing native
scores and rollout corrections. The restrained arm bounds KL divergence from
the native-score prior at each position; the control omits that constraint.
Both retain the original sampler, eight worlds, four-ply masked continuation,
root context, difficulty and immediate-winning-capture priority. Selection uses
a separate seeded random stream. Frozen settings were chosen from public
development prefixes, without win labels. This uses a score-derived native
prior and is not a reproduction of Ataraxos's neural networks. See
`docs/ai-restrained-search-2026-10-15/plan.json` and
`python3 tools/restrained_search_cycle.py --help` for the experiment stages.
Fresh validation found no DOS gain: baseline 29.5%, probability control 30.3%,
KL restrained 29.5%. Direct scores against the baseline were 43.4% for the
control and 41.6% for restraint; restraint scored 40.5% against the control.
All three direct 95% score intervals lay below 50%. Both new policies remain
experimental and are rejected for promotion. The complete 2,100-attempt
validation, paired intervals, mechanism diagnostics and verification evidence
are retained in `docs/ai-restrained-search-2026-10-15/result.json`.

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
