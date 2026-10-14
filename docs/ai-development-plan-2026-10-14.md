# Next AI development cycle

The requested order is benchmark diversity, diagnostic positions, individual
enemy history, an offline teacher with a compact runtime policy, then deployment
optimization. Steps 1–3 are implemented and verified as development components;
the tracker is an opt-in native/X16 prototype. Step 4 has been tried through
a fitted and hardware-tested model, with promotion rejected. Step 5 is complete
with a retained deployment portfolio and independent setup-only confirmation.

## 1. Broader benchmark

`make benchmark-ai-broad` adds seven equally weighted layout groups without
altering the historical suite: fortified, uniform, unguarded rear flag, forward
flag, rear bomb decoy, presets, and a mixture of those families. Uniform layouts
shuffle the full legal inventory with no flag-location constraint. Decoy layouts
enclose a mobile piece with three rear bombs while placing the actual unguarded
flag in a different forward sector. All layouts preserve the legal 40-piece
inventory; 2,500 generator samples and reproducibility checks pass.

The opponent league contains original v0.2.0, the initial planned AI, the adaptive
predecessor at the candidate's level, current Easy, and the independent greedy
bot. Each deployment pair is played twice with the engine sides swapped. Native
programs, the Python interpreter and all bot imports are retained; archived
script opponents are replayed from their snapshots. A 70-game smoke test had no
illegal decisions. Independent reference runs then played 2,800 games per level,
40 pairs per group/opponent, using seed offset 18,000,000.

| Opponent | Normal score, paired 95% interval | Hard score, paired 95% interval |
| --- | --- | --- |
| Original v0.2.0 | 70.1%, 66.4–73.7% | 64.9%, 62.0–67.9% |
| Initial planned | 57.6%, 54.4–60.9% | 51.2%, 47.9–54.5% |
| Adaptive predecessor | 53.0%, 50.4–55.7% | 52.0%, 49.1–54.9% |
| Current Easy | 75.3%, 72.0–78.7% | 75.3%, 72.1–78.4% |
| Greedy bot | 79.3%, 76.1–82.4% | 79.9%, 76.8–83.0% |

The earlier 80.1%/75.8% results against original v0.2.0 used a more restricted
deployment distribution. The broader result proves an overall advantage on
this new mixture, but the margin depends on layouts. For example, Normal scores
53.8% on decoys versus original v0.2.0, compared with 75.6% on fortified layouts.
Hard scores 45.0% against adaptive Hard on decoys (40.0–48.8%). This is a selected
subgroup among many comparisons, so it is a diagnostic signal, not a definitive
causal conclusion. It motivates independent decoy testing and position analysis.

All 5,670 new games are in the experiment ledger. `--suite broad --league`
selects the new infrastructure; leaving both flags out preserves historical
comparisons. `tools/verify_ai_archives.py` now lives in the repository and checks
all archive/source/program/script hashes, game counts and trace lengths.

## 2. Diagnostic collection

The first retained collection samples 1,074 losses and capped games from 42
archived runs, with extra coverage for the expanded suite. It contains 1,587
positions, selected deterministically across layout and outcome buckets.
The [retained ZIP](ai-diagnostics/positions-20261014.zip) and
[manifest](ai-diagnostics/manifest.json) preserve the collection and its generator.
The collection is retrospective diagnostic/training material; its selection
cannot serve as an independent strength test or estimate population frequencies.

| Observed symptom | Positions |
| --- | ---: |
| Quiet repetition after 100 plies without battle | 171 |
| Scout sacrifice against an already disclosed rank | 153 |
| Mining a rear bomb while the real flag is elsewhere | 171 |
| Concealed flag could have been captured by another legal move | 26 |
| Last own turn before a loss | 860 |
| Last own turn before the game cap | 215 |
| No optimistic route to the opposing flag at the selected final turn | 196 |

Labels overlap. They indicate symptoms, not automatically inferior choices.
For example, a Scout sacrifice may defend a flag; the AI cannot be expected to
identify a concealed flag from referee knowledge. Sixteen of the 171 quiet
repetition snapshots have no optimistic flag route even when mobile blockers
are ignored; the others require further tactical analysis before calling their
cycles avoidable. There were no observed missed *disclosed* flag captures.

Each position stores a masked board, public casualties and repetition state;
public notifications; the selected and legal moves; source archive identity,
game and ply; and a complete replay prefix. Referee truth and full deployments
are separate fields used only for evaluation/reproduction. A teacher's features
may use `input` and `public_history` only. They must never consume referee boards,
enemy deployments, oracle labels or oracle evidence as input features.

Examples in the retained collection:

- `872c1cc50467cdc41f21`: Hard decoy game, seed 51489, ply 204. Forty recent own
  turns use only four distinct moves after 100 plies without a battle.
- `da709d0a20dc3052804e`: Hard decoy game, seed 52030, ply 64. The chosen move is
  35→25; 35→34 would take the flag, whose identity was still concealed.
- `3939484e0d87cfb07f6b`: Hard decoy game, seed 36296, ply 905. A Miner takes a
  disclosed bomb at 84 while the concealed flag is at 79.

The validator reconstructs all 1,587 public states and legal moves from their
prefixes and checks that permuting concealed enemy ranks leaves the input
unchanged. Two full decoy games, against greedy and adaptive opponents, reproduce
105 and 100 plies exactly from retained programs. Historical records without
program snapshots are explicitly marked as unavailable for exact engine replay;
their referee positions remain reproducible from deployments and moves.

Rebuild with `tools/build_ai_diagnostics.py --out NEW_DIRECTORY`; verify with
`tools/test_ai_diagnostics.py NEW_DIRECTORY`. `tools/replay_ai_game.py` now
supports `--recorded-engines` for recent run directories.
`make test-ai-diagnostics` validates the retained ZIP directly; `make verify-ai-archives`
verifies the benchmark ledger and programs, including script dependencies.

## 3. Individual public histories and rank beliefs

`src/core/ai_memory.c` now retains stable identities, first observed square,
current location, movement/battle counters, certain rank candidates, and the last
approach/retreat relative to a disclosed opposing rank. Captured records remain
available; newly rescued pieces receive new identities. Eighty initial pieces
and four possible rescues fit in 84 records. Both armies share one public-history
tracker; private ranks of either army are excluded from the records.

Long Scout moves retain the same identity and become certain Scout records.
Movement excludes stationary Bomb/Flag possibilities only when the applicable
variants prohibit their movement. Combat disclosures and observed outcomes
constrain candidate ranks. Under Silent Defense, different undisclosed defender
ranks that produce the same public outcome produce identical history states.
Sometimes an outcome alone identifies a rank, such as a stationary Bomb beating
an attacking Marshal. Uncertain approach/retreat evidence changes relative rank
weights mildly without eliminating compatible positive-prior ranks, so bluffing
remains possible. These weights are heuristics, not calibrated probabilities.

The component is ready for teacher/student features, but the current production
move policy does not consume it. `make native-memory test-ai-memory` builds and
tests the opt-in native engine. Its `memory SQUARE` command reports the stable
identity and public record. AI_TEST snapshots preserve 941 bytes of history.
Existing GAME.DAT files do not store this history: restores begin a new observed
history from the public board. Counters mean observations since tracking began,
not a claim to reconstruct unrecorded moves. The learned policy must handle that
missing history explicitly before promotion.

`tools/build_ai_memory.py` builds a disposable X16 runtime under
`build/ai-memory-x16`, leaving production runtime files intact. The tracker uses
bank 24, with one observation gateway and the existing mission-reset gateway.
The prototype mission bank uses 4,935/8,192 bytes, and main RAM retains six bytes
below the reserved 1 KB stack. The first attempt exceeded main RAM by three bytes;
reusing mission reset resolved that without reducing the stack reservation.

Validation:

- 6,506 focused checks pass, including same-outcome privacy, all 64 options,
  identities, discoveries, captures, new pieces, counters, weights and snapshots.
- 15,163 hidden-permutation and 3,836 Silent Defense inventory checks pass.
- Address/undefined-behaviour sanitizers pass; leak detection is disabled for
  the host's ptrace environment.
- 24 actual banked events, Classic and all options, match 1,892 live native/X16
  piece histories and restore bank 22 after every observation.
- Native move decisions match production across six Normal games (1,672
  decisions) and six Hard games (1,809 decisions).
- All 21 swapped pairs in a 42-game broad integration run have identical full
  move traces; the score is exactly 50%, as expected for unchanged play.
- Prototype Native/X16 parity matches 100 Normal positions (maximum 29 frames)
  and 100 Hard positions with all options (maximum 49 frames).
- Default `make all check` still passes with the tracker disabled.

The [tracker manifest](ai-memory/manifest.json) links a retained source/program
bundle and banked/parity reports. Compiled source and runtime hashes were verified.
The integration run is in the benchmark ledger, now 43 runs and 17,718 games.

## 4. Offline tactical teacher and compact runtime policy

`src/native/teacher.c` implements exhaustive root actions with a three-ply,
eight-action material-ordered beam at subsequent turns, respecting combat and
two-square history. Each complete world is sampled from public inventories and
the tracker's candidate sets. Soft encounter evidence gives relative world
weights. The label estimates the future material consequence of a capture
relative to its immediate gain and a stand-pat reference, then compensates the
parent's one-ply capture-danger charge. Stand pat is an analysis reference,
not a legal pass proposed to the player. Labels are clipped to ±192.

The teacher sees hypothetical complete worlds, not the actual referee board.
This is approximate determinized beam minimax, with potential strategy fusion:
future choices may differ between sampled worlds even when the player could not
distinguish them. [Information Set Monte Carlo Tree Search](https://pure.york.ac.uk/portal/en/publications/information-set-monte-carlo-tree-search/)
instead searches information sets; that is a possible stronger successor to this
initial labeler, not an algorithm implemented by the current teacher.

A controlled General/Captain/Marshal/Spy exchange shows the extra horizon:
two-ply analysis values the General's capture at −155 and prefers moving the Spy;
three-ply analysis recognizes the recapture option, values the capture at +45,
and selects it. This proves a useful additional tactical analysis capability,
not globally stronger play by the teacher or its student.

`tools/train_ai_student.py` samples 32 worlds for each of 512 tactical positions,
searching 8,540,573 nodes and generating 1,736 move labels. Full-history and
missing-history variants remain in the same split group. Groups use layout
family and game seed, keeping sides and related positions together. A maximum
depth-four integer regression tree is fitted from 1,478 training rows and
evaluated on 258 grouped holdout rows. Its mean absolute error is 41.34 versus
42.57 for a zero correction. This small diagnostic improvement is not a strength
claim. The earlier 40-position infrastructure pilot overfit and was rejected.

The model has 25 nodes and 150 bytes of table data. `src/core/ai_student.c`
shares the exact integer feature implementation between fitting and runtime.
It adjusts capture scores only for Classic Normal; quiet strategic moves and
other rules/levels retain the parent evaluator. Four sampler/teacher tests
cover the extra horizon, inventory/movement consistency, split isolation and
the fact that changing oracle fields cannot change labels. Future producer runs
send workers only public inputs and retain source/program snapshots at startup.

The fitted policy passed tactical/fairness checks, including 15,163 hidden
permutations and 3,836 Silent Defense private-inventory comparisons. Independent
development used 280 new broad-suite games (offset 20,000,000) against frozen
mission Normal: 136 wins, two draws and 142 losses, 48.9% (43.9–53.9%). No reliable
gain was demonstrated, so the model remains opt-in and is not promoted.

The X16 prototype uses 6,477/8,192 bytes of the mission bank, retaining six bytes
below the reserved main-memory stack. Fresh parity matches 100 positions,
maximum 30 frames (0.50 seconds). Another 120 real banked decisions match both
native armies with accumulated history and identical per-turn random states.
A legal synthetic 12-move history exercises the learned age split: cold input
predicts +58, historical input +36, with both values matching inside bank 24.
The first bridge build omitted the model because cl65 encountered its flag too
late; this produced 21 mismatches. The flag placement was corrected, and builds
now verify the complete table's presence in both MISSION.BIN and BRIDGE.PRG.

[The student manifest](ai-student/manifest.json) retains the model, labels,
programs, sources, failed infrastructure check and successful hardware results.
`make native-student test-ai-student test-ai-teacher` builds and checks the
experiment. `tools/build_ai_memory.py --student` creates the disposable X16
runtime. `tools/test_ai_student_banked.py` checks complete native/X16 decision
sequences; `tools/test_ai_student_history.py` tests missing and full histories.

## 5. Separate deployment optimization

`tools/optimize_ai_deployments.py` searches legal inventories using rank swaps,
four generations, a 16-member population and diversity-preserving elitism. Every
move policy and bot import is snapshotted. The candidate always uses the frozen
coordinated evaluator with the student disabled. Its setup follows its engine
when sides are swapped; this differs deliberately from move-policy benchmarks.
The opponent league is original v0.2.0, initial planned, adaptive, Easy and greedy,
across the seven broad layout families. All experiments use Classic rules.

The search evaluated 52 unique layouts in 3,640 games (seed 41,261,014). It chose
three new layouts before validation, with pairwise Hamming distances 32, 32 and
35. Development scores were 93.6%, 89.3% and 87.9%, versus 88.6% for the strongest
existing preset, CORNER FORTRESS. These selected fitness estimates were optimistic.
Normal validation used seed 42,261,014; independent Hard transfer used 43,261,014.
Each played 2,800 games, 560 per layout/control, on 56 new opponent layouts.

| Deployment | Normal validation | Hard transfer |
| --- | ---: | ---: |
| Evolved 1 (`74e54c5129ea`) | 88.4% | 84.1% |
| Evolved 2 (`d83d63408255`) | 88.7% | 89.2% |
| Evolved 3 (`815ddb0df689`) | 89.6% | 85.6% |
| CORNER FORTRESS control | 90.5% | 90.4% |
| Protected random control | 89.1% | 84.8% |

No evolved layout established an advantage over the best existing preset.
Hard transfer suggested advantages over protected random for CORNER FORTRESS
and Evolved 2. Both were selected for fresh confirmation, before any confirmation
game was played. The primary endpoint was existing preset versus protected random;
the evolved layout was secondary. Seed 44,261,014 supplied 84 new opponent-layout
blocks, 12 per family: 840 games per tested layout and 2,520 games overall.

| Hard confirmation | Wins / draws / losses | Score | Difference versus protected random, block 95% interval |
| --- | --- | ---: | --- |
| CORNER FORTRESS | 760 / 19 / 61 | 91.6% | +3.0 points, +0.2–5.7 |
| Evolved 2 | 743 / 38 / 59 | 90.7% | +2.1 points, −0.4–4.6 |
| Protected random | 728 / 33 / 79 | 88.6% | reference |

Setup improvements are isolated from move-policy improvements: all candidate
and control games in a run use the same evaluator executable and difficulty.
Confidence intervals for differences bundle all five opponent policies, both
sides and controls for an opponent layout, resampling those blocks within family.
The first two run summaries also retain narrower match-pair intervals; the
separately archived `deployment-block-analysis.json` is authoritative for setup
generalization. An integrity tool checks every recorded setup follows the correct
engine, side pairs share their genotype and trials, inventories are legal, and
the retained program/script hashes match.

The [portfolio](ai-deployments/portfolio.json) retains all three diverse new
layouts, their measured strengths and the preferred existing control. Glyphs
can be supplied directly to the native engine's `setup` command. The
[deployment manifest](ai-deployments/manifest.json) links explicit trial,
portfolio, integrity and block-analysis records; full programs and moves are
retained in the benchmark ledger. The four deployment runs total 11,760 games.
The full ledger now covers 48 runs and 29,758 games.

This provides an independently confirmed way to strengthen Hard against the
tested fixed league through deployment selection, without changing its move
policy. It does not prove a gain against humans, a gain for every new layout,
or general superiority of Hard over Normal. Production still uses randomized
deployment; making a single predictable layout the default was not part of this
experiment. The retained portfolio supports varied future deployment selection.

Reproduce with `make optimize-ai-deployments`, then
`tools/optimize_ai_deployments.py --validate SEARCH --out NEW_DIRECTORY` and
`tools/analyze_deployment_validation.py NEW_DIRECTORY`.
`make test-ai-deployments` and `tools/verify_ai_deployments.py RUN_DIRECTORY`
check the operators, diversity, matched comparisons and actual side assignments.
