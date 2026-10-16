The corrected module remains `tools/campaign_home_reserve.py`, with `VERSION='public-home-reserve-v2'` and the unchanged pure `evaluate(cells, army, lost, histories, moves, shuttle)` API. The v1 registered source and evidence are preserved; no saved v1 matches were run. Root owns rejection records, new immutable IDs, driver/registry packaging and qualification games.

The correction changes enemy ETA legality only. The former simple BFS could miss a legal two-step detour returning to the moving Miner's vacated source before taking an initially shuttle-banned edge. It could report no route, or a longer route than the actual legal minimum. The new search distinguishes the initial source node from later nodes and permits that source revisit. Only the initial edge observes the current ban; after a legal detour resets the shuttle, a shortest continuation needs no further cycle. All other blockers and exact own-rank capture constraints remain unchanged.

The stationary-piece enemy ETA now includes the legal shuttle-reset detour. Guard deployment remains a conservative simple quiet path, with current first-edge shuttle and disclosed tactical threats checked. This may miss a usable guard route; it does not promise a shorter deployment than that checked legal path. No hidden-rank, opponent seed, prior, coefficient, strategic gate or capture/tactical exception changed.

`shuttle-detour-certificate.json` preserves both public counterexamples: v1 reports no route or seven actions, while actual legal transitions and v2 both give five. Fifteen mechanical tests include independent breadth-first enumeration through `Position.moves`, actual fight outcomes and shuttle transitions; they compare 15 count/capture combinations and the rotated detour position. The four adapter protocol tests also pass. Neither the unit oracle nor the corpus audit is a playing-strength experiment.

`REVISION.json` was written before code changes. `immutable-v1/` preserves the exact old module, tests, screening evidence and qualification records, with hashes in `immutable-v1-files.json`. The new screening audit reads only the already completed C21 archive. Actual terminal labels remain offline annotations, and original native score vectors are absent, so chosen-action incidence is an eligibility diagnostic rather than a native-ranking replay or changed-outcome estimate. There is no CX16 fit or execution claim.

Run tests from the repository root:

```sh
PYTHONPATH=tools python3 -m unittest tools/test_campaign_home_reserve.py tools/test_home_reserve_adapter.py -v
```

Reproduce the screening-only timing and eligibility audit:

```sh
python3 docs/ai-honest-campaign-2026-10-15/research/home-reserve-runtime-v2/benchmark.py
```
