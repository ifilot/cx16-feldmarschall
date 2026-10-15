# Classic tournament desk

Choose two named AI versions, run paired Classic games, and review the results
and individual matches in the compiled C++ Qt6 companion. The native tournament
worker evaluates independent matches with OpenMP. The X16 game has no new
dependency and its playing policies are unchanged.

## Start the companion

From the repository root:

```sh
make desktop
```

This builds and starts `build/desktop/feldmarschall-desk`. To compile without
launching, run `make desktop-build`. Subsequent launches can use the executable
directly, including from another directory:

```sh
build/desktop/feldmarschall-desk
build/desktop/feldmarschall-desk build/tournaments/example.fmtour
```

Build requirements are CMake 3.21+, a C++17 compiler with OpenMP, Qt6 development
packages (Core, Gui, Widgets, Sql and the SQLite driver), zlib, and Python with
Pillow and NumPy for embedding the game's artwork. These dependencies are
already available in the current environment. PySide6 and its temporary virtual
environment are no longer needed for this GUI.

Reviewing tournaments runs entirely in the compiled GUI, using its embedded
artwork. Launching tournaments also needs Python's standard library and GCC for
the existing immutable-source builder, layout generation and compact file
writer. Match execution, legality checks and combat run in the compiled OpenMP
worker. The implementation is tested on Linux/WSL; native Windows packaging
has not been validated.

The equivalent direct build commands are:

```sh
cmake -S desktop -B build/desktop -DCMAKE_BUILD_TYPE=Release
cmake --build build/desktop --parallel 4
```

`--project PATH` locates a different project checkout and `--python PROGRAM`
selects the interpreter used for source builds and storage. The worker executable
must remain beside the GUI executable. The earlier Python GUI remains available
through `make desktop-python`; only that legacy interface needs
`requirements-desktop.txt`.

The top controls select AI A, AI B, paired rounds per layout family, a seed and
the number of **Workers**. Workers sets how many independent matches OpenMP can
evaluate simultaneously. The initial value respects `OMP_NUM_THREADS` when set,
otherwise it uses up to four workers.
**Run tournament** asks for a new `.fmtour` filename, builds the preserved policies
and runs games in a background process while the window remains responsive.
Existing files are never replaced. Both desktop teachers are selectable, but
their searches take more time than the X16-sized policies.

The result panel gives wins, draws, losses and score, with a breakdown by layout
family, game endings and average length. Its tooltip includes participant provenance. Select
a match in the table to inspect its starting position and complete move history.
Use Start, Previous, Next, End, the slider or Play/pause to review it. Clicking a
move jumps to the resulting position. Filter to decisive games, draws or games
that reached the move limit.

The board reuses the game's procedural campaign terrain, Prussian portraits,
classic rank labels and red/blue palettes. It keeps Blue at the top, Red at the
bottom and a10 at the upper left. The perspective selector shows either both
armies or the public board from one army's viewpoint. Battles and long Scout
moves reveal ranks as in Classic. The move list remains an analyst's complete
combat history; it is not an AI input.

For a reproducible review screenshot, the compiled viewer can open a saved match
at a specified ply and exit after capture. `--view` uses 0 for both armies, 1 for
Red and 2 for Blue. Ply zero is the starting position:

```sh
build/desktop/feldmarschall-desk --capture-review saved.fmtour \
  --match 30 --ply 104 --view 1 --screenshot review.png
```

Use `QT_QPA_PLATFORM=offscreen` when capturing without a display. The
[15 October review](ai-cycle-2026-10-15/README.md) includes two examples from real
saved tournaments.

## Command-line tournaments

```sh
python3 tools/tournament.py list
python3 tools/tournament.py run student-guard-v1-normal missions-v1-normal \
  --backend openmp --rounds 10 --seed 20261015 --jobs 4 \
  --out build/tournaments/student-vs-missions.fmtour
python3 tools/tournament.py show build/tournaments/student-vs-missions.fmtour
python3 tools/tournament.py verify build/tournaments/student-vs-missions.fmtour
build/desktop/feldmarschall-desk \
  build/tournaments/student-vs-missions.fmtour
```

Each paired round gives the same starting Red and Blue armies to both policies,
then exchanges which policy plays which army. Its two matches share the random
seed. The seven families are fortified, uniform, unguarded, forward, decoy,
preset and broadly mixed. Ten rounds per family produce 140 games. `--families`
selects a subset; `--max-plies` defaults to 1,000 individual moves.

The runner compares move policies using common deployments. It does not measure
the production deployment mixtures. All games use Classic rules; variant options
are not exposed. Both engine processes receive only legitimate observations.
The referee is frozen for each run, and every review reconstructs the match
from its starting armies and moves.

## OpenMP execution

The compiled GUI uses the OpenMP backend. The command line explicitly selects it
with `--backend openmp`; `--backend python` retains the previous Python reference
implementation and remains the command-line default for backward compatibility.
Build the worker with `make desktop-build` before selecting OpenMP.

OpenMP dynamically schedules complete games. Each game has its own board,
two-square histories and two separately seeded AI processes. The actors' legacy
static variables are therefore isolated by process. We do not attempt concurrent
turns within a match. Python writes completed games through one database
connection; game IDs are assigned by the precomputed schedule, so completion
order does not change match numbering or pairings.

`--jobs N` sets the OpenMP team size. If omitted, the CLI uses `OMP_NUM_THREADS`
(the first value if it is a list), otherwise four. OpenMP runtime limits such as
`OMP_THREAD_LIMIT` can reduce the actual team size; requested and actual workers
are retained in the tournament metadata. For example:

```sh
OMP_NUM_THREADS=8 python3 tools/tournament.py run original-v1 missions-v1-normal \
  --backend openmp --rounds 10 --out build/tournaments/eight-workers.fmtour
build/desktop/feldmarschall-tournament-worker --info
```

The native backend checks legal moves and combat with a C++ Classic referee.
Its complete traces are cross-checked against the independent Python referee.
The worker executable, its build-time source snapshot and compiler receipt are
embedded in each native tournament. The Python verifier also checks the
presence and hashes of those artifacts. Existing schema-1 `.fmtour` files remain
readable by both viewers.

Scores count a win as one point, a draw as half and a loss as zero. A small
tournament is useful for exploring behavior, but should not support a promotion
claim by itself. Use the existing paired-confidence benchmark tooling for formal
strength claims, freeze the candidate first and reserve fresh validation seeds.
The GUI does not present an Elo rating or infer human strength.

## Compact, portable files

`.fmtour` schema 1 is a single SQLite database. Match metadata is indexed for
browsing. Each move occupies two bytes before zlib compression: its source and
destination squares. We store the two initial 40-piece armies once per match,
not a complete board image or JSON object for every move. A 1,000-ply game thus
needs 2,000 uncompressed move bytes before compression and database overhead.

The file embeds participant source ZIPs, compiler/build receipts, exact runtime
files and frozen referee sources. Content hashes deduplicate shared artifacts.
This adds a fixed provenance cost, amortized over the tournament. Viewer access
is read-only and needs neither the original executables nor original build
directory. Native executable portability is platform dependent; preserved
sources allow rebuilding on another host.

Each completed match commits independently. A normal failure records `failed`;
a caught keyboard interruption records `interrupted`. Abrupt process termination
may leave `running` metadata, but committed matches remain reviewable. Automatic
resume is not implemented. `verify` checks embedded hashes, source/runtime
presence, legal moves, terminal outcomes, move limits and paired-round integrity.

The SQLite tables are `metadata`, `artifacts` and `games`. Artifacts and move
payloads use zlib; all other fields are ordinary JSON/text/integers. See
[`tools/tournament_store.py`](../tools/tournament_store.py) for the schema and
[`ai/README.md`](../ai/README.md) for naming, registration and restoring policies.

## Verification

```sh
make test-tournaments
make test-native-desktop
make check
```

The storage checks run real engines, verify paired storage and complete legal
replays, detect corrupt traces/results/artifacts, reproduce moves from fixed
seeds and exercise a desktop teacher.

The native suite compares all moves/results in 14 matched games from the Python
reference, a one-worker OpenMP run and a four-worker run. It compares every
replayed board with Python, compares legal move sets including history, checks
process-start errors, exercises the desktop teacher with OpenMP, and drives the
compiled GUI through opening a Python-generated tournament, launching a new
parallel tournament, filtering and replaying matches. It writes
`build/native-desk.png` and `build/desktop/test-report.json`. The small timing
sample in that report is diagnostic, not a general scaling guarantee.
