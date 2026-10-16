# Secondary held-out robustness: no established inference gain against Guard

The unchanged source-inference champion scored **81.77%** against honest Guard,
versus **84.38%** for native Fortress without that bridge. The paired difference
was **−2.60 percentage points**, with a 95% interval **[−7.16, +1.82]**. This
predeclared secondary endpoint establishes no gain, reliable regression or
equivalence. All **768 attempts** completed without engine errors. Paired scores
improved 28 times, worsened 39 times and tied 125 times.

This complete plan and the exact immutable policies were frozen before the C112
complete result existed; `preregistration-order.json` preserves the timing check.
The 192 Army B records start at offset 32 in each of the same six generator
families, giving no layout overlap with C112. Both arms select the unchanged
Fortress deployment and face identical opponent armies and move seeds. Stored
Army A is unused. This supplies a secondary opponent-specific robustness test,
not another primary endpoint selected after seeing Missions outcomes.

| Opponent family | Native Fortress | Source inference | Difference |
|---|---:|---:|---:|
| Interior shell | 71.88% | 75.78% | +3.91 points |
| Flank Flag | 85.16% | 80.47% | −4.69 points |
| Double decoy | 95.31% | 93.75% | −1.56 points |
| Front fence | 81.25% | 82.03% | +0.78 points |
| Mobile squads | 84.38% | 78.13% | −6.25 points |
| Lane vanguard | 88.28% | 80.47% | −7.81 points |

Each family has 32 paired records; family uncertainty remains in `result.json`.
No favorable family, model parameter or larger sample was selected from these
outcomes. The [trajectory diagnostic](divergence.json) finds 359 changed complete
sequences out of 384; all first differences were by the candidate at an identical
preceding position. Of those changed sequences, 272 retained their outcomes.
Later choices are correlated consequences rather than additional independent
mechanism activations.

As in C112, this tests the complete inference bridge, including its uniform
background and count/movement conditioning, rather than isolating template
correlations alone. Absolute 50% is not a neutral null for these asymmetric own
and opponent deployment populations. The Guard and Missions endpoints use
different layouts and opponents: **do not pool their scores or infer a paired
same-layout opponent interaction**. Neither an unadjusted primary 95% interval
nor this secondary result establishes universal generality or substitutes for
DOS performance.

Both endpoints failed to establish a transferable gain for this unchanged policy
on their specified synthetic families. That is not evidence of an honest-AI
ceiling. The families are now exposed, and unused layouts do not make them unseen
again for a policy tuned from these results. The frozen policies, sample sizes
and stopping rules remained unchanged throughout.

Corpus/source provenance, all-state Python/native replay, repeated frozen own
setup reproduction and Qt6 captures are retained. No promotion follows from this
secondary study. Production remains unchanged.
