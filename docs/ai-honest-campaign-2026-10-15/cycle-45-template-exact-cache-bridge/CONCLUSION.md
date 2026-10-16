# Exact inference cache preserves every observed bridge trajectory

All 400 matched games had identical setups, complete move sequences, results
and error reasons between native Q24 V1 and exact-cache V2. This includes the
18 matching error prefixes in each arm. Both frozen policies scored 39.66%
against DOS: 109 wins, 85 draws, 188 losses and 18 unscored errors per arm.
The full fixed sample contains 800 attempts. This is a numerical regression
bridge, not a new strategic-strength result or a universal equivalence proof.

The 183 complete pairs have zero score differences and degenerate zero bootstrap
intervals. Those intervals do not establish statistical equivalence. Allowing
each missing outcome any score in [0,1] leaves finite-cohort difference bounds
[-4.50, +4.50] percentage points, separate from sampling intervals. Exact matching
error prefixes do not recover their missing continuations. All 36 errors remain
preserved and unscored.

An unexpected SIGTERM ended the original first-arm writer after eleven games.
Recovery extracted only hash-verified frozen runtimes, worker and setup records,
then appended the 389 missing original game IDs without generating new setups
or seeds. All eleven original rows and packed move traces remained byte-identical.
The snapshot, original metadata, source bindings and independent final check are
retained under `recovery/first-arm-missing-v1/`. The second full 400-game arm ran
in parallel after capacity became available. No game was discarded, replaced
or played again for a new outcome; the original policy IDs and models remain
unchanged. The interruption cause is unknown.

The first arm's recorded 361.33 seconds measures recovery of missing games only;
its original interrupted duration is unavailable. The second arm's full batch
took 350.64 seconds. These differently scoped times must not be compared as a
cache speedup. Separate banked retention fixtures measured approximately
16–21 ms preparation on cache hits and about 0.98–1.10 seconds on misses at
8 MHz; those measurements are not tournament-average or complete-turn latency.

All 800 games pass Python and native every-state replay, with two Qt6 captures,
frozen own-setup/original-generator audits and an exact V2 runtime rebuild.
Eleven preflight tests and three recovery schedule/rotation/privacy checks pass.
The recovery helper is qualified here for these native/DOS participants, not
all driver types. These desktop games do not replace actual bank, stack, reset,
audio and whole-turn target qualification. The experimental target relocation
recipe and tight memory limits remain separate evidence. Artwork and orientation
are preserved, and production remains unchanged.
