# Retain an inner Flag guard after a Miner breach

Hypothesis: replace Fortress's common inner Miner guard with a Sergeant, so a
successful defensive recapture removes the attacking Miner while retaining our
guard. This tests defensive composition, rather than adding another Bomb layer,
more search or a score bonus. One fixed swap exchanges own origins21 and34;
all Bombs, Flag, Spy, front ranks, rank inventory and RNG tickets remain fixed.

The Flag at30 has inner Bombs20 and31. Post21 is adjacent to both. Its baseline
Miner7 exchanges with a breaching Miner7; candidate Sergeant6 survives. Sergeant
is the weakest ordinary soldier that strictly beats a Miner. The displaced Miner
goes to34, preserving the army's offensive resource count. This has an opportunity
cost: different ranks occupy the two posts, and the relocated Miner's geometrical
front-access path is one step longer. Nothing proves dominance over full games.

The incremental weakness is clearest at right gate31: baseline neighbors21 and32
are both Miners and can only exchange. Left gate20 already has a Lieutenant at10
with a surviving recapture. The proposal does not claim that both baseline gates
lack a stronger defender. After capturing at31, the surviving Sergeant is no
longer adjacent to gate20; returning to common post21 takes another move.
Simultaneous breaches, escorts and other attacker coordination remain outside
the local certificate.

## Relationship to prior work and literature

[Arts, Competitive Play in Stratego (2010), section2.3.1](https://project.dke.maastrichtuniversity.nl/games/files/msc/Arts_thesis.pdf)
describes Bomb-protected Flags as requiring Miner attackers. The relevant thesis
passage was available through the search index; the PDF host timed out during
this preflight. This motivates matching a defense to the specialist that can
breach it, but does not validate this particular swap.

Our previous [home-interception component study](../../../ai-honest-campaign-2026-10-15/research/home-miner-interceptor-v1/CONCLUSION.md)
already demonstrated the distinction between a trading Miner and a surviving
Sergeant. The present hypothesis is therefore not a new combat discovery. It
changes their **initial assignment** while leaving the move policy unchanged,
rather than adding the old scheduling interceptor. The earlier C22 double-shell
deployment moved three pairs and added a second disjoint Bomb cut; this swap
changes no Bomb square or cut. No prior saved test of this exact assignment was
found in the inspected deployment plans and preflights.

## Implemented component

`tools/new_campaign_inner_guard_deploy.c` is a dedicated copy of the existing
deployment source. `AI_FORTRESS_INNER_GUARD` requires
`AI_DEPLOY_FORTRESS_ONLY`, excludes `AI_DEPLOY_DOUBLE_SHELL`, and enables the
single swap only in Classic Normal. Existing easy/random and hard behavior
remain the control's. The move evaluator, public prior, missions and scoring
are unchanged. No enemy square is read to choose the deployment.

Suggested immutable ID: `student-fortress-inner-guard-template-v1-normal`.
Clone `student-fortress-template-flag-bomb-v1-normal`, replace only source
`src/core/ai_deploy.c` with this dedicated source and add
`AI_FORTRESS_INNER_GUARD`. Registration, source snapshot and frozen recipe must
precede saved strength games. The parent owns that qualification decision.

## Evidence and scope

`python3 tools/test_new_campaign_inner_guard.py` passes six tests. The
[source-bound component artifact](component.json) includes sixteen actual native
defense decisions: both colors, both horizontal reflections, both breach gates,
and control/candidate. At the right breach the native control trades a Miner;
the candidate actually selects the Sergeant recapture and retains it. Both
layouts have a surviving left-breach response. These are synthetic public
response components, not a played legal opening prefix. The right fixture clears
own32, assuming that Miner left earlier, so it does not simultaneously occupy
the invader's approach square. Natural occurrence and conversion require games.

Full rank inventory is legal. All permanent Bomb/Flag blocker geometry is
identical, including the one-Bomb minimum cut and front connectivity. Both
formations retain32 of33 mobile pieces with potential front access; origin38's
Lieutenant is already isolated by Bombs28/37/39 in the control. The proposal adds
no new isolated mobile, and does not fix that separate preexisting limitation.

Native setup tests check both colors and multiple seeds/difficulties. Actual RNG
state is equal after setup, and forcing a common own army afterward yields
identical native decisions. The macro-disabled source matches the control's
setups and decisions. A separate compiled boundary test varies every other board
cell: the generated own ranks remain identical and every outside square remains
untouched. Reflection tests retain guard adjacency and combat outcomes.

Cost is one fixed swap at deployment, using existing local variables. No extra
per-turn work, protocol packet, array, search or random draw is introduced.
The [separate CX16 component qualification](TARGET-COMPONENT.md) finds 74 added
MISSION code bytes, no extra storage, and 52 real banked setup calls matching
native boards and RNG. It qualifies the ordinary production deployment alone;
it does not qualify the full desktop template adapter. The component result
proves a different retained defensive resource in a controlled response, not
stronger Stratego play or a guaranteed successful Flag defense.
