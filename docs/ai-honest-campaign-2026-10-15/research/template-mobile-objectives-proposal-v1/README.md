# Proposal: use inferred mobile ranks when choosing native objectives

This is a distinct strategic hypothesis, with no implementation, registered policy, opportunity count or strength claim. The current source prior retains information about mobile ranks in its Python posterior, but the native goal planner receives only Flag/Bomb probabilities. It therefore chooses long-range targets using exchangeable mobile ranks even when public disclosures make different enemy origins have very different mobile-rank probabilities. The hypothesis is that using those existing probabilities in objective selection improves route commitments before a capture becomes immediately legal.

## Existing controls and the actual gap

The frozen source-template model is unchanged: eight original Colonel templates/mirrors with total prior mass0.8, plus uniform legal-army background mass0.2. Public disclosures and movement update template compatibility and background evidence. `campaign_template_beliefs.py:rank_marginals` already returns all12 rank probabilities. `campaign_native_template.py` deliberately sends only Flag/Bomb marginals to native code. V1 and exact-cache V2 calculate a480-entry gain table whose mobile contribution remains exchangeable under remaining public counts. Cache V2 only reuses that same table; it is not this strategic idea.

C37's `student-template-mobile-captures-v1-normal` changes only immediately available hidden captures, including the existing own-Flag capture threshold. It preserves native goals and quiet scoring. C39's occupancy/mobile quiet-contact policies replace the old-minus-new contact danger component; their frozen descriptions explicitly preserve native goals and other tactical conditions. Neither lets a distant likely weak mobile target become a pursuit objective, nor lets likely superior mobile rank discourage an existing pursuit goal.

In `src/core/ai.c:plan`, target expectation enters utility as `24 + g/4`, a rejection test `g < -worth[a]/2`, the existing near-own-Flag context, distance cost and goal persistence. Thus replacing only a root capture bonus is not equivalent to changing the goal calculation. Existing coefficients, distances, persistence, routing, terminal handling, missions, own-Flag knowledge and native material values would remain fixed.

## Public-only expectation

For unknown live origin i, let p_i(r) be its rank marginal from the unchanged public posterior; moved origins still retain their tracked initial identity. Let F_i and B_i be the SAME existing constrained Q12 Flag/Bomb masses, M_i=4096−F_i−B_i, H the public remaining hidden mobile total, and n_r the corresponding mobile rank counts. Define:

- Baseline mobile expectation μ_count(a)=Σ_{r<10} n_r gain(a,r)/H.
- Inferred conditional mobile expectation μ_i(a)=Σ_{r<10} p_i(r)gain(a,r)/Σ_{r<10}p_i(r).
- Keep the existing counts fallback when that conditional denominator is zero; this must be explicit because fixed Q12 rounding can leave tiny mass discrepancies.
- G_full(a,i)=trunc_toward_zero[(F_i×2000 + B_i×gain(a,Bomb) + M_i×μ_i(a))/4096].

G_FB uses μ_count in the same expression. Known targets keep exact disclosed combat; terminal values and directly known Flag wins remain unchanged. There is no rank argmax, sampled guessed identity, enemy setup input, private setup seed, action-likelihood learning, new information reward, or extra rollout. The expectation uses all compatible possibilities before selecting a goal; it does not select a different ideal action separately in each hidden world.

A clean initial component experiment changes only `plan` from G_FB to G_full. Root capture scoring remains G_FB and danger remains native. A separate capture+objective treatment can compare against an equivalent capture-only control built with the SAME numerical expectation. Do not globally replace a shared helper and then call the change objective-only: that would also change capture scoring and nonlinear own-Flag thresholds. C37's existing exact treatment of that threshold is a useful reference.

Expected examples are deliberately qualitative, not measured opportunities. A General could route toward a distant origin likely to contain a profitable Colonel while declining a similarly distant likely Marshal. A Miner could prefer a plausible Bomb/Flag corridor over a losing pursuit of a probable strong mobile piece. Its value still changes40→25 only through the existing public Bomb-loss rule; no generic Miner reserve bonus is added. The own Flag is legally known: existing immediate defence must remain decisive, and fixtures must check that probability-based goal rejection does not silently remove a necessary blocking response. A positive expected target value is not a proof that the path is safe: current routes remain geometric, and cooperative trades, adversarial responses and information acquisition are still approximated.

## Research rationale and limits

[Stankiewicz, *Opponent Modeling in Stratego* (2009)](https://project.dke.maastrichtuniversity.nl/games/files/bsc/OMStratego.pdf), sections4 and6, develops per-piece rank probabilities from public play and specifically proposes using original-neighbour correlations after a piece is revealed. This supports retaining token-specific rank inference, rather than discarding it when planning. It does not test this objective bridge or imply a gain against this DOS engine.

[Cassandra, Kaelbling and Littman, *Acting Optimally in Partially Observable Stochastic Domains* (AAAI1994)](https://cdn.aaai.org/AAAI/1994/AAAI94-157.pdf), pages1024–1025, defines rewards by expectation under a belief state and distinguishes belief-based control from pretending uncertainty disappears after one action. That motivates the expectation above; native pursuit remains a heuristic, not an optimal POMDP solution. Better prediction need not improve play under a misspecified procedural background or a weak route planner.

## Minimum reviewable investigation

First freeze a public-component diagnostic protocol and its opportunity definition before reading any C21 screening trajectories. No C26/C41/C46 or other final-validation trajectories have been inspected for this proposal. A possible diagnostic is: same actor has two reachable hidden goals, G_full changes their strict native utility ordering or changes the existing rejection gate, and first quiet moves to those goals differ. Record both old/new goals, full posterior, unchanged distance/persistence terms and actual quiet choice. Count unique games/actors as well as repeated roots; no score-labelled root selection. If strict opportunities are absent, report absence without relaxing the gate.

Next require exact tiny-enumeration expectation tests, reduction to counts when mobile marginals are exchangeable, same F/B probabilities, disclosed/quiet/terminal control parity, first quiet route divergence, own-Flag blocking, Miner Bomb/Flag and known-loss worth transitions, both side mappings, hidden-nibble mutations and public-history reset/load fallback. Prove goal-only capture components remain unchanged. Compare each nonlinear plan gate explicitly; negative integer division and stable tie handling need a declared numerical contract.

Only after incidence and mechanism evidence should new immutable IDs be registered for a fixed screening comparison: F/B-only reference; full-mobile goals only; and matched full-mobile capture-only versus capture+goals. C39 contact treatment can remain a separate control rather than being silently combined. Use identical own deployments/opponent formations/seeds, Classic, unchanged effort and source prior. Freeze one primary contrast for fresh independent validation, with paired score intervals, original-DOS error sensitivity, honest-opponent generality and full native/Python/Qt replay. No late tournament is proposed in this campaign.

## Target feasibility must be measured

The template arrays already reside in bank25, but full expected gains are not free. Keeping both480-entry caches adds960B before code and scratch; V2 has only974B inference space and66B MAIN free. A goal-only control may instead require per-actor on-demand computation and row restoration, which increases bank crossings and work. A single full-rank table could replace the old table for a combined treatment, but cannot then serve as an isolated goal-only control without recomputing the baseline values. No fit or speed claim follows from the current cache result.

Never multiply Q24 probability mass by2000 in signed32bit arithmetic: 2^24×2000 exceeds its range. Choose an explicitly bounded rational/fixed-point method, preserve signed truncation, prove all intermediate bounds and quantify any new rounding identity. Naively rounding each rank independently can break inventory/row mass. First establish the desktop component and exact arithmetic oracle; then measure a fresh full target link, relocated-runtime closure, reset validity, actual banked numeric/move/RNG parity, audio, stack and hit/miss cycles. Any new numerical approximation requires a new policy version and separate evidence.
