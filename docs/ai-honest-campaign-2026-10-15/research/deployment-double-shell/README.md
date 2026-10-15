# Double-shell own deployment hypothesis

An opponent that knows our Flag can route a Miner directly to it. A second
unavoidable Bomb layer may make that attack less reliable: the Miner must survive
and clear two Bombs in separate contact turns. This is a structural deployment
change, not an evaluation score adjustment. It is honest: only our own board,
difficulty, Classic rules and ordinary setup RNG enter the placement function.

There is an important limitation. A Miner advances when it defeats a Bomb.
Two Bomb layers do **not** necessarily add movement tempo relative to an equally
long clear route, and one surviving Miner can clear both. The intended benefit is
redundancy and another contact turn on which a mobile defender can intervene.
Concentrating five of our six Bombs near the Flag also surrenders distant barriers.
Only fresh matches can measure the net effect.

## Existing designs and exact change

`setup_random` already puts the Flag on the back row with Bombs on every adjacent
home square. The validated `ai_deploy` mixture uses Fortress/Evolved2/Evolved3
with normal weights50/40/10 and hard40/50/10. All three fixed layouts have exactly
one unavoidable Bomb on their least-Bomb path from the home front row to Flag.
The Fortress Flag is at a1, with inner Bombs a2,b1. Its i1 Lieutenant is permanently
trapped by i2,h1,j1 Bombs until an opponent removes a Bomb.

The proposed candidate starts from **Fortress only** and exchanges three pairs:
a3↔i2, b2↔d1, c1↔h1. Flag, Spy, complete front row, rank inventory and all other
cells are unchanged. This puts Bombs on a3,b2,c1, outside the existing a2,b1 shell.
The final sixth Bomb remains j1. All33 mobile pieces now have a path to the front
through mobile/emptyable squares; the original Fortress has32. The Spy remains
at h2, with the same shortest potential front access distance2. This proposal
makes no claim to solve Spy exposure separately.

Two disjoint vertex cuts certify the new property. Removing either `{a2,b1}` or
`{a3,b2,c1}` disconnects a1 from **every** front-row entry in the home-board graph.
Every orthogonal enemy path must cross both, so at least two distinct Bombs must
be cleared. A shortest-path calculation with cost1 on Bomb entry and0 otherwise
independently confirms minimum2 versus1 for all three existing fixed layouts.
This calculation treats mobile defenders as eventually cleared, and certifies a
geometric barrier, not a tactical result. Scouts cannot jump an occupied Bomb.

| Deployment | Minimum Bomb captures | Mobile pieces with front access | Sum of potential exit distances |
| --- | ---: | ---: | ---: |
| Fortress control | 1 | 32 | 38 across32 reachable pieces |
| Double-shell Fortress | 2 | 33 | 43 across33 reachable pieces |
| Mobility-only descriptive control | 1 | 33 | 40 across33 reachable pieces |

The third row merely swaps i2↔i1 to release the trapped Lieutenant. It is preserved
as a geometry control in the research JSON, without a registered policy or engine
flag. A two-arm Fortress/double-shell match tests the complete three-swap package;
its outcome cannot distinguish the double cut from the simultaneous mobility
improvement. A later mobility-only arm would separate these if strength evidence
warrants that investigation. The candidate also increases aggregate potential
exit distance, so “no trapped pieces” does not mean free mobilization.

## Historical public failure audit

Only the two earlier development tournaments were read (source hashes and all
records are in `geometry-and-history.json`), never new campaign/validation data.
Of418 scored games,88 began with a structurally Bomb-screened own Flag;62 of those
lost the Flag. In56/62, the final capturer was an enemy Miner whose rank was
publicly disclosed by that actual Flag battle. In56/62, exactly one of our Bombs
within two initial home steps of the Flag had been removed; the other6 required
two. This supports studying repeated-Bomb contact as a plausible failure channel,
but is not evidence the candidate wins more. Both historical armies were generated
from the same stress family, and historical setups are not the proposed fixed
control. Most other historical games had unscreened Flags and are not representative
of current protected deployment. Overall286 Flag losses should not be pooled as a
causal comparison of guarded/unprotected designs.

The audit reads our own initial ranks and occupancy/move history; an enemy rank
is recorded only on the actual terminal public Flag battle. It does not derive a
feature from hidden enemy ranks or use their private deployment to build our army.

## Cheap implementation and strict control

`AI_DEPLOY_FORTRESS_ONLY` fixes the existing validated setup choice to Fortress,
while retaining the original RNG ticket draw and consumption. Add
`AI_DEPLOY_DOUBLE_SHELL` for the candidate's three fixed in-place swaps.
Compiling that flag without `AI_DEPLOY_FORTRESS_ONLY` is rejected. The default
normal/hard mixture and easy/optional-rule fallbacks remain unchanged when these
flags are absent. The implementation changes only `src/core/ai_deploy.c`, adds
no storage, graph computation, opponent inspection or extra random draw, and
executes a bounded three swaps once at setup. The same mapping handles both sides.

Recommended first comparison: the same honest move policy with Fortress-only
versus Fortress-only+double-shell, identical opponent armies, move seeds and sides.
Fix the hypothesis and immutable source/build IDs before any saved games. This is
a matched mechanistic screen; it does not establish improvement over the existing
validated mixture. A separate fresh comparison against that mixture is required
before promotion. Avoid changing both the deployment and move evaluator together.

The tests cover the real setup routine, exact inventory/six changed cells,
unchanged Flag/Spy/front row, both independent cut certificates, no trapped mobile
pieces, both sides/normal+hard across100 seeds, identical post-setup RNG behavior
with forced common armies, default binary identity against frozen prechange setup
source, and unchanged easy/optional-rule fallback. A direct compiled setup-function
probe varies every enemy-board byte while holding honest inputs fixed and requires
identical own output and untouched non-own squares. Existing deployment regression
tests also run. No candidate strength games or policy registrations were created.

`checks-initial-harness-failure.log` preserves an initial binary-comparison harness
failure: the temporary original source had a different basename, changing ELF
source-file metadata. Giving both source files the same basename fixes that
comparison; the actual default executable is byte-identical. This was a test-harness
issue, not a policy change.

## Measured 8-bit target cost

The installed cc65/cl65/ca65 toolchain reports V2.18 (Ubuntu2.19-1). An isolated
`-O -t cx16` compile+assemble of the actual frozen deployment source succeeds
with both production `BANKED_AI`/`AI_MEMORY` pragmas and ordinary nonbanked mode.
Compared with Fortress-only, the candidate adds **282 code bytes** and **zero
additional data, read-only data, BSS or zero-page bytes**. Banked code correctly
lands in `MISSIONCODE`; both arms retain120 bytes of `MISSIONRODATA` and7 bytes
of `MISSIONBSS`. The control function occupies247 bytes; the candidate529.
This is cheap once-per-game work, but the code-size increase is real.

A separate sim65c02 harness calls the real nonbanked setup routine1,000 times per
side with the same deterministic RNG stub. Candidate minus control total CPU
cycles divided by1,000 are348.487 for Red and1,611.486 for Blue. The asymmetry
comes from the own-square mapping paths in generated65C02 code. At a nominal
8MHz these differences are approximately0.044ms and0.201ms per setup. They are
harness averages, not hardware measurements or exact instruction-level bounds;
link placement/page crossing can contribute small differences. Existing setup
and RNG work is common to both arms. No extra random draw or data storage appears.

`tools/audit_double_shell_target_cost.py` reproduces the audit without writing any
production build output. `target-cost.json` retains tool versions, commands,
segment sizes, source hashes, cycle results and limitations; `target-cost-build.zip`
retains generated assembly, objects, simulator harness/binaries and segment dumps.
Full production linking, remaining bank capacity, and physical CX16 runtime were
not tested. No frozen source, policy ID, registry or gameplay evidence changed.

## Full production link follow-up

A subsequent complete production link closes the bank-capacity question above.
Both Fortress-only and double-shell builds succeeded in separate copied `/tmp`
source trees with the actual `src/Makefile` full C/assembly source set, cc65 `-O`
CX16 target, all production AI features, bank pragmas, vendor sound library,
original linker configuration and1024-byte C stack. Generated headers were copied
from the current working tree and pinned by hash. All workspace source/build file
hashes were identical before and after; no production output was overwritten.

| RAM bank | Fortress used / free | Double shell used / free |
| --- | ---: | ---: |
| PLAY (8192 bytes) | 8032 / 160 | 8032 / 160 |
| AI (8192 bytes, including BSS) | 8147 / 45 | 8147 / 45 |
| MISSION (8192 bytes, including BSS) | 7515 / 677 | 7797 / 395 |

Both `FELDMARS.PRG` files are35,096 bytes. `MISSION.BIN` grows from6134 to6416
bytes, exactly282 bytes; BSS occupies additional RAM without bytes in the file.
`PLAY.BIN` (8032 bytes) and `AI.BIN` (6943 bytes) are byte-identical between arms.
This is a RAM-bank program with loadable bank files, rather than a new system ROM.
The candidate fits its intended MISSION bank with395 bytes remaining. The separate
AI bank already has only45 bytes free in both arms; this deployment change does
not consume that bank's remaining space.

`full-target-link.json` preserves exact commands, diagnostics, all C/assembly/header
hashes, per-segment/linker sizes, capacity and output hashes. Per-arm logs and
`full-target-link-build.zip` retain full maps, symbols and linked program/bank files.
`tools/audit_double_shell_full_link.py` reproduces the isolated build. Static link
success establishes fit for this exact source/toolchain combination; startup and
hardware gameplay were not exercised by this follow-up.
