# Template-prior target feasibility: research only

The fixed source prior can be represented much more cheaply than the desktop Python history model. A complete public history needs only one compatibility bit per template, the rank counts of all disclosed origins (including captures), and the count of undisclosed moved origins. Each compatible point template has likelihood one under these hard constraints. With N compatible templates and uniform-background event probability E, each compatible template has posterior weight 1/(N+2E), and the background has weight 2E/(N+2E). This preserves the 0.8 template / 0.2 background prior and ignores opponent action likelihood, exactly as the desktop model does.

For public known-rank counts k[r], K=sum(k), and M unknown moved origins:

    E = product_r falling(COUNTS[r], k[r]) / falling(40,K)
        * falling(remainingMobile,M) / falling(40-K,M)

Captured origin ranks matter for template compatibility, while the background uses their rank counts only. No actual enemy setup or seed is needed.

## Existing history is sufficient during an uninterrupted game

`src/core/ai_memory.h` exposes `origin`, current `square`, `owner`, `moves` and `known_rank` for up to 84 identities. `ai_memory.c` keeps captured identities after setting their square to NOWHERE. `rules_apply()` reveals Classic combatants, updates capture counts, then calls `ai_memory_observe()` before changing either square. That observer syncs disclosures and infers a long-range Scout. A read-only bank-24 exporter can therefore pack 40 known-rank/moved bytes and 40 origin-to-current-square bytes for the enemy. A fresh compatibility mask can be computed from all retained identities every decision; no additional capture callback or persistent mask is required.

`board[100]` is in MAIN RAM. `play.c:computer_think()` copies the referee board to its private truth buffer, masks concealed enemy ranks, invokes the AI, then restores the board. Bank-25 inference can consume this already permitted board directly. It must never inspect the play truth buffer. The native GCC implementation should use the same explicit masked/public contract and hidden-nibble invariance tests.

History validity must be sticky from the first memory sync: all 80 legal initial pieces, correct deployment rows, no MOVED or REVEALED flags. A reset first observed after the opening cannot establish original identities. `play_resume()` calls `begin()` and `ai_reset()`; GAME.DAT currently stores board/rules/scene only, not the public origin history. Custom positions have the same issue. A first research version should disable the template prior and fall back to unchanged native expectations after load/custom/missing history. It must not relabel current positions as initial origins. No save-format change is needed for that limited prototype.

## Measured bank budgets

An isolated compile of the current untouched production source gives:

| Area | Free bytes |
|---|---:|
| MAIN, including code/data/BSS before the 1 KiB software stack | 585 |
| AI bank 23 | 45 |
| Mission/history bank 24 | 680 |
| Play bank 22 | 160 |

Sound banks are allocated through 21; play is 22, AI 23, mission 24. Bank 25 is unallocated by this program. `src/ui/sound.c` already loads required code banks and restores the previous selection, while the sound ISR preserves banking. No claim about arbitrary hardware RAM expansion is needed to identify the next program allocation.

Real cc65 object probes measured a 200-byte MAIN union plus 2 state bytes, 43 bytes of MAIN wrapper code, 60 bytes of gateway code plus 2 bank-save bytes, and a bank-24 history exporter/initial-board scan of 348 code bytes plus 5 scratch bytes. These are interface budget probes, not a completed validity implementation.

A full isolated game link with these interfaces and an explicitly NONFUNCTIONAL inference-bank stub succeeds. It uses a 320-byte template reservation, 400 bytes for per-square Q12 arrays, 2,400 bytes for an all-rank expected-gain cache and 256 bytes of scratch in bank 25. No executable from this experiment was run. Remaining space is:

| Area | Free bytes after interface/stub link |
|---|---:|
| MAIN | 154 |
| AI bank 23 | 85 |
| Mission/history bank 24 | 327 |
| New inference bank 25 | 4,724 |

Moving the small expected-value selection wrapper into MAIN reduces AI-bank code enough for the new prepare/per-actor-row calls. The shared MAIN union holds 80 history bytes during preparation and one 100-square signed gain row during scoring; those lifetimes do not overlap. The inference bank retains the full cache. Known captures retain the existing direct combat table, and a disabled prior uses the existing expectation table.

This proves the proposed interfaces and conservative data reservations can link, not that the inference algorithm fits or matches the desktop policy. The remaining roughly 4.7 KiB must cover posterior arithmetic, marginal construction, quantization, gain computation, validity handling and scratch. MAIN has only 154 bytes left, so further helpers should remain banked. All probes alter temporary source copies only; hashes prove workspace src is unchanged. The first failed compile (missing stdint inclusion in the copied probe header) is preserved separately.

## Proposed opt-in implementation boundary

1. A strict new compile guard owns inference bank 25, its required loader entry and distinct assembly gateway save bytes. Default builds preserve their existing bytes and bank loads.
2. Add a guarded initial-history-valid flag in bank-24 memory reset/sync and a compact public-history exporter. Its validity persists until reset, and late/custom/load resets leave the source prior disabled. Preserve all existing memory behavior.
3. After public memory sync, export the enemy history, compute E and the eight compatibility bits in bank 25, construct Flag/Bomb marginals, and quantize with exact global inventory and per-row capacity constraints.
4. Reproduce the desktop native policy's functional approximation: Flag/Bomb probabilities are spatial; remaining hidden mobile ranks remain exchangeable. Do not silently introduce template-conditioned mobile ranks.
5. Compute the same Q12 expected capture values with Flag value 2000, existing dynamic Miner/Spy worth and signed final truncation. Cache all attacker rows in bank 25. Before planning/scoring each own mobile piece, copy its 200-byte row into the shared MAIN union. This avoids a bank switch for every target evaluation.
6. Keep known targets, Classic legality, nonlinear score guards and persistent-goal behavior intact. Gate normal Classic only. No production change or selectable ID is implied by this budget experiment.

Q24 E is a practical numerical research approximation, not exact real arithmetic. There are at most K+M<=40 sequential factors in [0,1], so floor-at-each-step absolute error is less than 40/2^24. With at least one compatible template, background-weight error is less than 80/2^24, under 0.02 Q12 units. A rounding boundary may still change a Q12 integer by one. When no templates survive, the background weight is exactly one even if Q24 E underflows. A future fixed-point port needs a new immutable policy ID and explicit numerical-parity tests rather than claiming bit-for-bit equivalence to the float driver. The global two-column Flag/Bomb rounding constraint must be preserved; independent nearest rounding is insufficient.

Before registration: compare all marginal arrays and selected moves on public historical roots, include captures/equal exchanges/long Scouts/both sides/reset/custom/load fixtures, prove hidden-nibble invariance, preserve macro-off byte parity, link the actual algorithm, and run a banked emulator test that verifies 22→23→25→24 calls restore every bank with audio active. Measure target cycles and stack high-water use. Validate strength on fresh seeds if numerical differences create a new policy. C28 honest-opponent generality remains relevant: a source-specific DOS prior can be misspecified for human formations.
