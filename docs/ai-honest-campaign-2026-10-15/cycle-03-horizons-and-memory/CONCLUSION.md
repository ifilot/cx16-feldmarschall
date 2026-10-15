# Cycle 3: horizon and memory changes did not improve DOS play

Five arms attempted 420 games each: 2,100 attempts, with 14 original DOS errors
retained unscored. The matched baseline scored 28.8%; capture quiescence 26.2%,
sparse-root depth extension 28.0%, recurrence escape 28.0%, and uniform world
weights 28.7%.

Matched differences were −2.9 percentage points for quiescence (95% interval
−7.0 to +1.1), −0.7 for sparse depth (−5.0 to +3.6), −1.0 for recurrence escape
(−1.9 to −0.2), and −0.1 for uniform weights (−2.2 to +2.1).

Recurrence's narrow negative bootstrap interval rests on very few changed pair
scores. See paired-direction-sensitivity.json for an exact direction-based
sensitivity check; do not treat a sparse percentile interval as decisive general
strength evidence. Recurrence reduces draws from four to two, but wins also fall
from 118 to 116 and losses rise from 295 to 300. Escaping a loop is not itself a
useful plan.

No candidate merits promotion or tuning on this cohort. Extra tactical depth
and changed sampling weights do not address the largest remaining limitations.
Retain all policies and evidence; continue with public deductions, correlated
beliefs, opponent modelling and translating beliefs into concrete capture value.
Production stays unchanged.
