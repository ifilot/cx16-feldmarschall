# Full mobile beliefs for pursuit objectives

Hypothesis: use already available, public per-token mobile-rank inference to
choose profitable distant targets, rather than treating every concealed mobile
piece as exchangeable. This isolates route commitment from capture evaluation.
It follows the previous campaign's proposed but unimplemented objective bridge;
it does not repeat its capture-only or quiet-contact experiments.

The unchanged prior has eight public DOS deployment templates/mirrors at 80%
total mass and a uniform legal-army background at 20%. Public movement and rank
disclosures update it. No true enemy deployment, private seed, guessed rank,
extra rollout or action-likelihood learning is consumed. The same controlled
Q12 Flag/Bomb probabilities reach the existing capture evaluator. For each mobile
actor and concealed enemy, the new goal table replaces only the conditional
mobile mean in the expected combat gain. Revealed enemies retain exact gain.
Moved enemies receive their tracked original token's conditional mobile mean.

`plan()` uses the new gain for its existing rejection gate and utility term.
Distances, persistence, ties, native danger, own-Flag defence, missions, captures,
student model and RNG calls retain their source. This is a full persistent policy,
not post-hoc score correction. All legal candidates are still evaluated once.
The existing own deployment is Fortress, matching the comparator.

`tools/new_campaign_objectives.py` materializes three dedicated source files
without changing shared native/core sources. It embeds the helper implementation
in the existing template adapter. Register using the same `native-template`
driver, its usual dependencies and the opt-in `--mobile-goals` launcher switch;
replace `src/core/ai.c` and `src/native/engine.c` with
`tools/new_campaign_objectives_ai.c` and
`tools/new_campaign_objectives_engine.c`. Select
`tools/new_campaign_objectives_bot.py` as adapter entrypoint. Suggested immutable
ID: `student-fortress-template-mobile-goals-v1-normal`.

The numerical contract is the previous Python proposal: preserve existing Q12
immobile masses, condition full floating mobile marginals, truncate toward zero
with values within 1e-9 of integers snapped to that integer. Preserve exact native
integer output when the conditional reduces to exchangeability; zero conditional
mass falls back to exchangeable hidden counts. Negative integer division is
explicit. The baseline capture path remains byte-for-byte the existing function.
This is not the separate Q24 target arithmetic proposal.

Qualification uses synthetic rational-mixture oracles and previously designated
honest development history only, both colors. It checks default-off native move
parity, full persistent decisions, concealed-nibble invariance, one native go,
malformed/reset packets and unchanged root capture scores. The helper API cannot
consume enemy hidden identity bits. No validation trajectory is inspected.

Cost: at most 10 x 40 concealed-target calculations and one 4,000-character goal
packet per decision, then native table lookups. This adds a 2,000-byte desktop
native table and an 8,192-byte protocol line buffer, so it does NOT establish
CX16 bank fit. Desktop wall-time timing is host dependent and includes Python
model/protocol overhead. No extra search, game-tree expansion or sampling occurs.
Target streaming, bank crossings and exact wide arithmetic remain separate work.

Research motivation: [Cassandra, Kaelbling and Littman (AAAI 1994)](https://cdn.aaai.org/AAAI/1994/AAAI94-157.pdf),
pp.1024-1025, formulates control on a belief distribution and expected reward.
This motivates retaining uncertainty in objectives; our route heuristic is not an
optimal POMDP controller. [Stankiewicz (2009)](https://project.dke.maastrichtuniversity.nl/games/files/bsc/OMStratego.pdf)
uses public per-piece rank probabilities and original-neighbour correlations in
Stratego. Neither source tests this bridge or predicts a DOS score improvement.
The known risk is model misspecification: source-aware pursuit may amplify the
existing deployment prior's poor generalization to unfamiliar formations.

Before saved play, the parent campaign must register the source/model/recipe,
freeze the screening population/comparator/error handling and preserve all
results. A fresh validation cohort is required after choosing any candidate.
