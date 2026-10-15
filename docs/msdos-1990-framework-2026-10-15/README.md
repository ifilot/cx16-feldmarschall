# Fast MS-DOS Stratego 1990 opponent

The original 1990 AI can now play named Feldmarschall policies in headless,
parallel tournaments. Select **MS-DOS Stratego 1990 v2 / Colonel (fast)**
(`msdos-1990-v2-normal`) in the compiled Qt6 desk. Its preserved predecessor,
`msdos-1990-v1-normal`, is the instruction-counted execution reference.
Production Feldmarschall AI is unchanged.

The main [saved tournament](reference.fmtour) contains **140 match attempts**
across all seven layout families, with swapped policy sides and common armies.
There are **138 scored games and two unscored reference errors**. The desk can
review every legal trace, including the two failures. See the captured
[ordinary match](review-match.png) and [reference error](review-error.png). It visibly identifies the
DOS AI's access to hidden ranks; errors are excluded from win rates.

```sh
make desktop
# Select MS-DOS Stratego 1990 v2 / Colonel (fast) and an existing opponent.

# Or open the saved evidence directly:
build/desktop/feldmarschall-desk \
  docs/msdos-1990-framework-2026-10-15/reference.fmtour

# Run a new 140-match batch; output files must be new:
python3 tools/tournament.py run student-guard-v1-normal msdos-1990-v2-normal \
  --backend openmp --jobs 4 --rounds 10 --seed 20261016 \
  --out build/tournaments/versus-dos-1990.fmtour
```

## What runs

[Unicorn](https://www.unicorn-engine.org/docs/tutorial.html) executes the original
16-bit x86 instructions. The adapter loads the original resident image, MZ
relocation table and overlay 5, applying the original segment relocations. It
calls original initialization (`0078` / `02FB`), selection (`13C4`) and physical
move synchronization (`134B` / `04E1`), retaining their original helper routines,
knowledge, caches, compaction, history and counters between turns.

The host supplies the Classic referee and a physical-board bridge. It omits DOS
startup, graphics, sound, menus and animations. This is an original-AI coprocessor,
not a complete emulation of the interactive DOS program. Its setup screen and
procedural army generator are not exercised: both opponents receive the same
referee-generated armies, as in existing policy comparisons.

The final [framework source snapshot](framework-source.zip) preserves the runner,
storage, desktop and import/build tools separately from the immutable AI versions.

The [import manifest](../../ai/msdos1990/manifest.json) pins the source repository,
commit and input hashes. The four imported images total approximately 193 KiB;
original graphics and music are unnecessary. Both named policies have immutable
source ZIPs, recipes and runtime hashes in the catalogue. The default difficulty
is the original **Colonel, level 3**. The recipe fixes Scout move-and-attack on,
ordinary combat and the original repetition gate. Source comments record the
exact configuration bytes; automatic no-move rule/mode cycling is omitted.

A real-mode CPU and the original globals belong to one AI process. The OpenMP
worker reuses processes between games, sending a fresh seed, `new`, own army and
explicit original physical opponent army for every match. Each game constructs
an entirely new emulated address space. Worker threads do not share AI memory.
DOS notifications are acknowledged before another move is requested.

## Hidden information and fidelity limits

The physical board contains both true armies, as the original software expects.
The original initializer keeps the opponent's Flag and Spy identities; other
original routines can also consult physical ranks. This behavior is preserved,
not presented as fair inference. Only the explicitly registered DOS adapter
receives the `opponent-setup` extension. Feldmarschall policies continue to receive
only their own setup and public events.

The adapter checks original pointer-grid occupancy, positions, ownership and own
ranks against the host referee after every nonterminal public event. The fast and instruction-counted
backends produce identical CPU state in targeted history tests and identical
complete match traces in the benchmark. These checks do not prove equivalence to
every state reached by the full original DOS UI/game loop, particularly around
original uninitialized-memory contracts and caller setup.

The score in this small reference cohort is descriptive. Original privileged
knowledge and the two errors prevent interpreting it as a clean fair-information
strength comparison. Repeated benchmark executions below are not independent
strength games.

## Measured speed

The [140-attempt report](stress-report.json) records **22,691 plies**:

| Four-worker run | Measured time / throughput |
| --- | ---: |
| Match execution, including per-game result commits | 23.40 seconds |
| Match execution throughput | 970 plies/second |
| Complete run, including portable source/runtime packaging | 33.43 seconds |
| Complete-run throughput | 251 match attempts/minute |

These are measurements on this machine and these deployments, not guaranteed
rates for every position. Average recorded length was 162 plies; the limit was
1,000. Runtime packaging is a fixed cost that is substantial for tiny batches.

The [initial benchmark](benchmark/report.json) compares instruction-counted,
fast serial, fast four-worker and Python-reference execution on the same 14 games.
The first four-worker run was slower than serial. After adding process reuse,
the [pooled benchmark](pooled-benchmark/report.json) measured 14 games / 2,015 plies
in 2.02 execution seconds on four workers, versus 5.90 seconds on one worker.
End-to-end times were 12.34 and 28.79 seconds respectively; packaging and host
I/O variability are included, so the execution timings are the clearer scaling
comparison. All eight benchmark executions have identical moves and outcomes.
They represent 14 distinct games, repeated eight times for correctness and speed.

V2 removes instruction-by-instruction budget counting so Unicorn can run native
translated blocks. A two-second per-call watchdog remains. No AI instruction or
scoring rule was patched for acceleration.

## Reference failures are explicit

The larger correctness run exposed an original call into the fatal-exit service
from `ovl5:2511`, reached through the post-battle updater. A ranked helper
consumes a null reference and obtains out-of-range coordinates. The original
inline dispatch targets `ovl2:0174`, whose body requests process exit with code 1.
The [diagnostic](checks/reference-error.json) and compressed CPU/history
[reproduction](checks/reference-error.zip) preserve the evidence.

This is an original fatal-exit path reached under this headless bridge. It does
not prove that the unmodified interactive game would fail identically, nor justify
silently adding a strategy guard. The original code remains unchanged.

The framework records `result=error`, the legal move prefix and the diagnostic;
it excludes that attempt from wins, draws and losses, clears the failed process
pool and continues subsequent games. Startup/configuration failures still stop
a run. The original failed batch is retained in the evidence archive.

New tournaments use **`.fmtour` schema 2** to distinguish unscored errors from
game outcomes. Schema 1 remains readable. Both Python and compiled replay verify
every recorded move; an error record is explicitly a nonterminal trace prefix.
The cycle strength-gate helper refuses error-containing cohorts. A regression
checks failure, a successful swapped-side game, then the same failure again,
with matching Python/native traces and no process-state leakage.

## Installation, preservation and checks

Unicorn is isolated under `build/msdos1990/deps`, pinned to **2.1.4**:

```sh
make msdos1990-deps
make msdos1990
make test-msdos1990
python3 tools/test_msdos_framework.py
python3 tools/audit_msdos1990.py
```

The imported original images are already preserved in the source snapshots.
To verify/import them again from the supplied decompilation checkout:

```sh
make msdos1990-import MSDOS1990_SOURCE=/path/to/stratego-decompilation
```

Each portable `.fmtour` includes the original images, adapter, emulator bindings,
shared library, source recipes and referee provenance. The emulator
makes this a roughly 8.4 MiB fixed archive cost, amortized over the games; move
traces remain two bytes per ply before compression. Rebuilding on another host
requires that host's pinned Unicorn package. Replay needs only Qt6 and the file.

The nine original benchmark/failed-run SQLite files are preserved byte-for-byte
in [benchmark-evidence.tar.xz](benchmark-evidence.tar.xz). A shared compression
window avoids storing the same emulator repeatedly. The [archive manifest](benchmark-archive.json)
records each original file hash. The current 140-attempt reference is directly
openable outside that archive. To extract the older runs:

```sh
mkdir -p build/msdos1990-evidence
tar -xJf docs/msdos-1990-framework-2026-10-15/benchmark-evidence.tar.xz \
  -C build/msdos1990-evidence
```

Verification covers original geometry/RNG instructions, initialization/orientation,
Flag/Spy knowledge, CPU checkpoints, both armies' long histories, exact fast/reference
state equality, transport failure isolation, old/new storage, compiled Qt review,
Python/native/OpenMP parity and ordinary production regressions. The
[completion audit](audit.json) binds sources, runtime artifacts, match traces,
reports and the compressed evidence. No X16 policy, default model or game rule
was changed by this framework.
