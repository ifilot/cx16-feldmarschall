# Reflect or diversify the complete Fortress formation

Two hypotheses are fixed before saved play. First, test whether using the complete
horizontal mirror of Fortress changes end-to-end strength. Second, test whether
a symmetric two-formation ticket mixture improves robustness over the original
fixed formation. Both retain the exact move policy, public inference and existing
setup RNG stream. There is no new combat rule, information source, search or
post-hoc choice of individual piece placements.

The immutable candidates are:

- `student-fortress-mirror-template-v1-normal`: always mirror Classic Normal.
- `student-fortress-mirror-mixture-template-v1-normal`: original on accepted
  tickets 0–4, mirror on tickets 5–9.

Both use `tools/new_campaign_mirror_deploy.c`, replacing only the baseline
deployment source. Enable `AI_FORTRESS_MIRROR_ONLY` or
`AI_FORTRESS_MIRROR_MIX`, respectively, with the required existing
`AI_DEPLOY_FORTRESS_ONLY`. The flags are mutually exclusive and cannot be combined
with the double-shell experiment. Other difficulties and rules retain their
baseline setup behavior. No shared source or baseline ID is changed.

Reflect all 40 own ranks, including Flag, Spy and Bombs. The two shapes have
identical rank counts, Bomb-cut distance and mobile connectivity; the original
isolated Lieutenant at origin 38 maps to origin 31. This experiment does not
repair that isolation. A horizontal reflection of the complete Classic position
is a rule symmetry because lakes, movement and combat reflect together. Here
only our army is reflected while the opponent population is held fixed, so an
observed effect includes matchup differences and cannot isolate coordinate tie
ordering alone.

The [Ataraxos paper, sections 2.1 and 2.4](https://arxiv.org/html/2511.07312v1#S2.SS1)
models setup selection separately from movement and regularizes its learned
setup distribution with entropy. This motivates studying formation support
without changing move logic. Our fixed two-shape mixture is a small controlled
analogue, not that learning method, and the paper supplies no performance
guarantee for this pair of layouts.

## Exact randomization contract

No extra draw is made. Both candidates consume the same existing rejection loop
and accepted ticket as the Fortress control. Across accepted raw draw values
1–65,530, each ticket has exactly 6,553 values, giving 32,765 values to each
orientation. Deterministic retries preserve a small inherited distinction:
enumerating all 65,535 nonzero initial states gives 32,766 original and 32,769
mirrored mixture setups. Exact halves cannot hold for that odd population.
The claim is five of ten accepted tickets, not exactly equal counts in every
finite seed cohort. This documented effect is not corrected with new draws.

Six component tests cover exact complete reflection/inventory, structural
equivalence, the accepted ticket classes, every nonzero initial state for both
colors, all first-draw rejection seeds, real native setups and post-setup RNG,
forced-common-army move parity, macro-disabled and easy/hard/rule fallback
controls, flag exclusivity and independence from other board contents.
[Source-bound component results](component.json) and [test log](checks.log)
retain the checks.

## Fixed studies and composition check

C117 uses 128 side-swapped original-DOS pairs per arm, seed 3117001, four workers
and 1,000 plies. C118 uses Missions, seven familiar setup families, 16 pairs per
family per arm, seed 3118001 and two workers. Each has the original, fixed mirror
and ticket mixture arms, with both candidates contrasted against the original.
Both plans are frozen before the first outcomes. These are exploratory screens,
with paired intervals, family reporting and finite bounds for unscored errors;
they do not establish promotion or held-out generalization.

A preregistered composition audit compares each saved mixture game with the
fixed arm selected by its actual own setup. Identical opponent armies, move
seeds and movement code should produce identical trajectories, including error
prefixes. This checks that the mixture changes deployment only. It does not imply
that the observed mixture score must equal the arithmetic mean of the other
two arms: its orientation selection is attached to the existing setup tickets
within this particular finite cohort.
