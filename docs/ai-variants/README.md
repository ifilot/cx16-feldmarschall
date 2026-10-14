# Optional variant strength benchmarks

The suite evaluates the retained production policy separately at Normal and
Hard, against five fixed opponents and seven layout families. The referee uses
the game's C rules for legal moves, combat, moving-Flag victory and rescues.
Both engines receive only their permitted observations.

## Conditions and controls

| Mask | Rules |
| --- | --- |
| 0 | Classic control |
| 1 | Attacker wins ties |
| 2 | Silent Defense |
| 4 | Exploding Bombs |
| 8 | Moving Bombs, including their explosion rule |
| 16 | Moving Flag |
| 32 | Rescue |
| 3 | Attacker wins ties and Silent Defense |
| 10 | Silent Defense and Moving Bombs |
| 48 | Moving Flag and Rescue |
| 63 | All six options |

Individual variants precede the combined conditions. Every condition uses ten
paired deployment rounds per family and five opponents: original v0.2.0,
planned, adaptive Normal, production Easy and a variant-aware greedy bot.
The reference league remains fixed when the candidate changes difficulty.
Seven families times ten rounds times five opponents times two sides gives
700 games per condition, or 15,400 across both levels and all eleven masks.

The final plan uses seed offset 94,000,000. It freezes executable and referee
identities before play and checks them before each condition. Policy and
referee source hashes are pinned too. Every rule/level condition shares the
same deployments and move seeds. Scores therefore support comparisons over
complete matched blocks containing all five opponents and both sides.

Classic Normal uses the adopted cooperation-guard student; other rules retain
mission scoring. Classic-versus-variant differences measure these actual
production configurations. They do not isolate a rule's effect independently
of policy and opponent interactions. League differences between Normal and
Hard also do not replace a direct head-to-head difficulty comparison.

## Referee and information checks

The truth referee calls unmodified `rules_targets`, `rules_apply`,
`rules_flag_arrived` and `rules_rescue` through a retained native library.
The native engine and Python bot separately maintain masked positions.
Before each decision and at the end, the referee checks both boards,
disclosed enemy casualties, legitimate own casualties, public rescue counts
and two-square histories against the permitted true-state projection.

Silent defenders are sent as `?` with an observable combat outcome, except
when already disclosed or attacked by a Scout. A private returning rescue
rank is supplied only to its owner. Own casualty and rescue bookkeeping lets
the native engine use the same rescue incentives as the X16 runtime without
receiving the opponent's private inventory. The native additions affect the
host protocol; the retained game policy and X16 sources remain unchanged.

Both armies use the X16 demo rescue policy: restore the strongest available
ordinary casualty into the first vacant home square nearest the front.
This benchmarks computer play; a human can choose a different rescue or skip it.
Rescue requires an actual surviving mover's arrival. The first validation
attempt was discarded after an audit found that its wrapper lacked this guard
following a failed attack. Source pins stopped the attempt when corrected.
The final cohort uses fresh seeds, and a regression test checks this edge case.
Superseded smoke and discarded runs remain archived without supporting strength
claims.

Tests compare Classic legal moves and board outcomes with the independent Python
implementation, check the special rules explicitly, compare masked observers
under all 64 masks and exercise real native/greedy protocol games. Every retained
final trace is also replayed against its frozen C library, checking legality,
combat disclosure, private/public rescues, terminal outcomes and event counts.
Variant games are excluded from the Classic diagnostic and training replay path.

## Final results and tuning decision

Every row contains 700 games per level. Parentheses contain the complete-block
95% score interval. Capped counts are Normal/Hard out of 700 each.

| Mask | Normal score | Hard score | Capped games |
| --- | --- | --- | --- |
| 0 | 68.7% (66.1–71.4) | 66.1% (63.3–69.1) | 8 / 38 |
| 1 | 63.5% (60.9–66.0) | 61.1% (58.6–63.7) | 19 / 131 |
| 2 | 64.7% (61.6–67.8) | 63.4% (60.4–66.4) | 8 / 48 |
| 4 | 66.5% (63.9–69.2) | 60.6% (57.8–63.4) | 1 / 37 |
| 8 | 65.4% (62.9–68.0) | 65.0% (62.2–67.8) | 0 / 22 |
| 16 | 72.1% (68.6–75.4) | 66.2% (63.5–69.0) | 1 / 20 |
| 32 | 63.1% (60.1–66.1) | 62.3% (59.3–65.2) | 4 / 4 |
| 3 | 65.1% (62.6–67.5) | 61.1% (58.5–63.6) | 17 / 139 |
| 10 | 66.9% (64.6–69.1) | 62.7% (59.6–65.8) | 1 / 18 |
| 48 | 65.2% (62.6–67.8) | 62.8% (60.2–65.3) | 14 / 14 |
| 63 | 62.1% (58.7–65.4) | 59.1% (56.6–61.8) | 26 / 30 |

Targeted variant work is justified. Retain the current production policies while
developing and independently testing those changes. The next priorities are:

1. **Hard endings with attacker-wins-ties.** Caps rise to 131 games with this
   option alone and 139 with Silent Defense, versus 38 in the matched Classic
   control. First distinguish unavoidable blocked positions from avoidable
   repetition and lost specialist routes; cap counts alone do not prove mistakes.
2. **Hard exploding-Bomb decisions.** Its league score is 5.86 percentage points
   below Normal (paired interval -9.36 to -2.50) and 5.50 below its own Classic
   control (-9.00 to -2.07). Controlled blast/exchange and reply-assessment cases
   are a useful next experiment; these results do not identify a proven fix.
3. **All-options and rescue interactions.** All-options scores fall 6.57 points
   for Normal and 7.00 for Hard relative to their matched Classic controls,
   with intervals -10.64 to -2.64 and -10.50 to -3.64. Rescue alone also declines,
   by 5.64 points for Normal and 3.86 for Hard. Prioritize public rescue knowledge,
   arrival incentives and cooperation under changed mobility in diagnostic work.

These are development priorities from a fixed computer league, with multiple
comparisons. They do not establish a successful tuning rule or human strength.
Future policies need new development cases and fresh independent validation;
the current validation cohort must not become their final strength test.

The referee audited 7,207,368 permitted views. All 15,400 traces replay exactly,
covering 3,588,284 plies, 448,718 combats, 97,229 hidden-defender observations,
6,067 rescues (247 private), 85,448 Bomb moves, 26,837 Flag moves, 554 Flag arrival
wins, 21,818 bomb blasts and 38,992 Silent Defense Scout disclosures. No illegal
decisions, mismatched observations or replay failures occurred in the final cohort.

The [manifest](manifest.json) links the final summary, complete family/opponent
results, matched contrasts, trace verification, frozen plans and sources. All
individual game archives, including superseded and rejected runs, are retained
in the [experiment ledger](../ai-experiments.json).

## Reproduction

```sh
make native native-variant-rules native-baseline native-planned native-adaptive-baseline
make check test-variant-arena
python3 tools/run_variant_benchmarks.py --out NEW_RUN --rounds 10 \
  --seed-offset NEW_OFFSET --phase validation --jobs 4
python3 tools/analyze_variant_benchmarks.py NEW_RUN --out NEW_SUMMARY
python3 tools/verify_variant_traces.py NEW_RUN --out NEW_TRACE_REPORT --jobs 4
```

Use a new output directory and seed offset for new claims. The 95% intervals
resample complete opponent-and-side blocks within each family, using 10,000
bootstrap samples and seed 8,675,309. They describe each predeclared comparison
separately, without correcting for multiple comparisons.
