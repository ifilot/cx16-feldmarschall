The new module is `tools/campaign_home_reserve.py`; its only runtime entry point is `evaluate(cells, army, lost, histories, moves, shuttle) -> (adjustments, report)`. It imports the existing pure public board decoder and tactical helpers, with no tournament runner dependency. Inputs are unchanged; no state, randomness, seed, model or hidden enemy rank is consulted. The caller must use Classic rules and pass all native legal scored moves.

An intact two-Bomb screen beside a corner Flag and exactly one currently routed disclosed Miner initiate the check. Multiple currently routed Miners defer. After each quiet candidate, the evaluator recomputes the Miner's stationary-piece route and a capable guard's quiet deployment route. A missing invasion route is successful prevention, not a deadline failure. With one routed invader, guard deployment distance d and enemy Flag-capture time tau must satisfy d + 2 <= tau. Disclosed attacks that kill or exchange a prospective guard at its current source or along its route invalidate that deployment. An attacked candidate actor cannot certify a preferred alternative. Guard-source vacancy is included when testing Scout rays. Own Miners can intercept by trading; stronger guards can survive.

Only quiet moves can be demoted. Among certified quiet alternatives, every original score remains unchanged. Only a quiet move which fails raw schedule feasibility can be demoted below the highest-scoring certified quiet alternative. A risky actor move whose response schedule remains feasible is left untouched, so this experiment adds no independent tactical-risk correction. Captures, immediate wins, and current confirmed own Flag danger retain existing control; absent a safe quiet alternative, the evaluator changes nothing. This is a repeated public-state scheduling check, with no permanent garrison or persistent role variable.

The model does not prove global safety. It holds other units fixed, omits concealed threats and multi-turn offensive races, and cannot promise protection against sequential Miner breaches. A single diagonal guard can cover either Bomb entry individually but may be displaced or consumed by the first attack. It has not been measured for CX16 code size or execution, and is not ready for a target-fit claim.

Twelve mechanical tests pass, including both-side rotation, all hidden enemy nibble mutations, input immutability, exact own/enemy shuttle effects, captures/wins/urgent defense exceptions, absent routes, opened second routes, disclosed tactical attackers and the full 49-friendly-reply losing fixture with its successful alternative.

The frozen protocol predates implementation; `AMENDMENT.json` and `FINAL-AMENDMENT.json` document scope isolation and the guard-source safety correction before the final revision. Initial and intermediate pre-game source/results are preserved in their labeled subdirectories. The benchmark uses completed C21 screening only, never fresh validation. That retrospective archive preserves chosen actions rather than native score vectors. Therefore selected-action coverage is an eligibility diagnostic: a historical chosen quiet action fails while a certified alternative exists. It is not an exact native-ranking replay or a prediction that the recorded outcome would change. Runtime integration, immutable registration and fresh matches remain with the root agent.

Reproduce tests from the repository root with:

```sh
PYTHONPATH=tools python3 -m unittest tools/test_campaign_home_reserve.py -v
```

Reproduce screening-only timing/eligibility with:

```sh
python3 docs/ai-honest-campaign-2026-10-15/research/home-reserve-runtime-v1/benchmark.py
```

The root-owned adapter integration was independently reviewed and its four protocol tests rerun successfully. `audit-adapter-active.py` and `adapter-active-history.json` exercise 300 decisions over both armies in one completed C21 public history, including six actual reserve overrides. A reference native search is corrected to the same selected and then historical actual choice; both engines receive identical subsequent public events. This checks one-search correction continuity and public-state/next-choice compatibility, not a rollout under the new policy, exhaustive internal-state equality or playing strength. `played` restores pre-choice goals and commits the actual move without another search or random draw. Default-path rebuild/no-correction parity remains separate in `adapter-parity.json`.

The reviewed source base does not define `AI_PRIORITIES`; its candidate traces therefore preserve the native scalar ordering used by this adapter. Reusing the adapter with a separate priority ordering would require priority-aware traces or a new qualification. Portable packaging copies the reserve and public-guard modules only for the opt-in flag and requires native `AI_TRACE`. No driver, registry or core files were edited by this independent review.
