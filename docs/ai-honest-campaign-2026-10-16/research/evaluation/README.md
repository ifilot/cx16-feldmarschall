# Follow-up evaluation plan

The two-hour follow-up starts a new campaign. Old campaign cycles and validation
results are references; they are not new evidence. The primary question is
whether a cheap public-information mechanism improves the frozen Fortress plus
source-template policy against the original DOS deployment population.

Use `tools/new_campaign_cycle.py` with cycles 101 and later. It reuses the
existing Classic engine/referee, immutable catalog, complete replay and Qt6
review. It writes only the new campaign directory. Every experiment first saves
`plan.json`, then freezes policy identities and sources, then plays its entire
fixed sample. `checks.log` must contain completed meaningful unittest results
before `audit`. Preserve plan, registration, results, errors, source archives,
both replay receipts and Qt6 captures; commit after each completed cycle.

For the first DOS screen, compare each distinct mechanism with
`student-fortress-template-flag-bomb-v1-normal` against `msdos-1990-v2-normal`:
64 paired rounds, `families=["original-dos"]`,
`setup_mode="policy-owned-rotated-v1"`, 1,000 plies, OpenMP four workers.
All arms share a prospective seed and same DOS armies. For move-only additions,
own setup should also remain unchanged. This is 128 attempts per arm. Larger
samples must be declared before they start, not extended until a favorable
interval appears. Add fresh-seed confirmation only for frozen policies.

Generality is a separate endpoint. For promising frozen candidates and the
same baseline, use the new corpus `development` split, offset zero, eight paired
records per family (96 attempts per arm), first against
`student-guard-v1-normal`, then independently against `missions-v1-normal`.
Use `setup_mode="referee"`; the six plan families must be exactly those in the
dataset manifest. Plans add:

```json
"dataset": {
  "path": "tests/datasets/classic-generalization-v1",
  "split": "development",
  "offset": 0
}
```

The corpus can be used for development diagnostics while both validation splits
remain unplayed. A development win is not a held-out generalization claim.
Reserve `seed-validation` and `generator-holdout` for a prospectively declared
final study of an unchanged selected policy. Repeated move seeds on the same
stored armies do not make fresh layout validation.

Example commands after writing a complete standard campaign plan:

```sh
python3 tools/new_campaign_cycle.py freeze docs/ai-honest-campaign-2026-10-16/cycle-101-idea
python3 tools/new_campaign_cycle.py run docs/ai-honest-campaign-2026-10-16/cycle-101-idea
python3 tools/new_campaign_cycle.py audit docs/ai-honest-campaign-2026-10-16/cycle-101-idea
python3 tools/new_campaign_cycle.py overview
python3 docs/ai-honest-campaign-2026-10-16/research/evaluation/test_runner.py
```

Scores count wins plus half draws and exclude engine errors. For arm comparisons,
keep each side-swapped pair indivisible; compare only pairs complete in both arms
for sampling intervals. Separately retain finite all-attempt error-score bounds
with all scheduled pairs in the denominator. Family-specific standings and
contrasts accompany aggregate results. Equal planned family counts do not imply
equal complete-case weights if errors differ: inspect family results and missing
outcomes rather than treating the pooled score as a robust equal-family effect.
Intervals are exploratory and do not adjust for selecting among the campaign's
ideas. Multiple hypotheses, sparse changed pairs and frozen baseline uncertainty
must remain visible. Never pool unlike opponents or own-setup and fixed-army
contexts. Target cost and desktop strength are separate qualification questions.
