# Cycle 38: mobile capture inference has no established honest-opponent gain

Retaining per-piece mobile-rank capture expectations did not establish a strength
gain in this honest-opponent screen. The paired effect was **+0.536 percentage
points, 95% interval [−1.429, +2.589]**. Positive and negative pair directions were
balanced. This is an inconclusive exploratory result, not evidence for promotion
or a guarantee that the change is harmless.

The baseline and candidate played honest `student-guard-v1-normal` moves with the
same seven Classic referee deployment families, fresh seeds and side-swapped
pairs. All 1,120 planned attempts completed with zero errors and were independently
replayed in Python and native workers. Qt6 reviews, qualification evidence and
immutable source recipes are preserved. These results are against an honest
opponent and must not be added to DOS strength scores.

| Policy | Wins / draws / losses | Score | Errors |
| --- | ---: | ---: | ---: |
| Template Flag/Bomb baseline | 280 / 10 / 270 | 50.893% | 0 |
| Per-piece mobile capture inference | 281 / 14 / 265 | 51.429% | 0 |

The single prespecified contrast uses all 280 matched pairs, 40 per family, with
20,000 whole-pair bootstrap replicates. Its additionally reported 98.3333% interval
is [−1.875, +3.036]pp. Missing-score sensitivity bounds equal the observed +0.536pp
because no game is missing. Pair directions were 17 positive, 17 negative and 246
tied; the sign-symmetry diagnostic is supplementary and does not test the mean
effect. No source, model, coefficient or sample size was tuned on these outcomes.

The mechanism reuses the existing honest template posterior to retain conditional
mobile-rank information in hidden-capture values, rather than averaging all mobile
pieces exchangeably. The Flag/Bomb prior, native danger estimate, goal choice and
search budget are held fixed. Source-informed prior overconfidence on other army
populations remains possible. Predictive or arithmetic correctness does not by
itself show that changed captures improve complete games.

The independent DOS screen is separate evidence. A positive result there would
not turn this interval into proof of generalization; fresh final validation and
review of both contexts would still be needed. This is a desktop prototype with
no CX16 fit claim. Production and all frozen policy IDs remain unchanged.
