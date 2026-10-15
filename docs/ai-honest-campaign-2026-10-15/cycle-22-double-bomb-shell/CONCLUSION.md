# Cycle22: double Bomb shell rejected in the DOS screen

The three-swap double-shell deployment did not improve results against the DOS
engine. It scored below the matched Fortress-only control on this fresh cohort.
The geometric certificate remains correct: every route to its corner Flag crosses
two disjoint Bomb cuts, and all33 mobile pieces can potentially mobilize. Those
properties did not translate into greater strength for this complete deployment
package. No policy was promoted or modified after the results.

The comparison held the honest native move policy fixed. Each arm used200 matched
side-swapped pairs (400 attempts), original DOS-generated opponent armies and
seed2320001. Only own deployment differed. All1200 attempts were retained and
independently replayed in Python/native workers, including preserved errors;
Qt6 captures and own/opponent setup audits accompany the artifacts.

| Own deployment | Wins / draws / losses | Scored score | Unscored errors |
| --- | ---: | ---: | ---: |
| Existing validated mixture | 57 / 32 / 279 | 19.84% | 32 |
| Fortress only | 78 / 28 / 271 | 24.40% | 23 |
| Double Bomb shell | 60 / 22 / 310 | 18.11% | 8 |

Scores count wins plus half of draws, excluding errors. These standalone scores
use different scored subsets; the prespecified paired contrasts below are the
appropriate within-cohort comparisons.

| Prespecified paired contrast | Complete pairs | Mean difference | 95% interval | 98.3333% interval |
| --- | ---: | ---: | ---: | ---: |
| Double shell − Fortress (primary) | 172 | −5.81pp | [−11.63, −0.15] | [−12.94, +1.16] |
| Double shell − mixture | 166 | −1.81pp | [−7.38, +3.61] | [−8.58, +4.82] |
| Fortress − mixture | 161 | +3.88pp | [−0.31, +8.23] | [−1.40, +9.16] |

Intervals use20,000 whole matched-pair bootstrap replicates; the wider intervals
account for the three prespecified contrasts within this exploratory screen.
The primary95% interval is negative, while its wider interval includes zero.
The missing-error sensitivity bounds for double shell minus Fortress are
[−11.00,−3.25]pp over all200 planned pairs: even assigning every missing result
in the candidate's favor leaves a negative finite-cohort effect. These bounds
are not population confidence intervals. Other contrasts' missing-error bounds
include zero. All63 errors remain unscored; they are not quietly treated as wins,
losses or draws.

This result rejects the tested package as a DOS improvement. It does not prove
that every two-layer Flag defence is inferior. The package also frees one trapped
Lieutenant, shifts three mobile pieces, and concentrates Bombs at the expense of
remote barriers. We did not isolate which tradeoff caused the decline. Miners
capture and advance, so two Bomb layers never guaranteed an extra movement turn.
No tuning on these outcomes is authorized by this screen.

The prespecified cycle23 honest-opponent comparison uses the same frozen arms and
an independent seed, separating move-opponent context from original-army
population. It is auxiliary evidence, not an additional DOS result. Its absolute
50% score is not a fair-null benchmark because own and opponent deployment
populations differ. A future deployment candidate would require a new immutable
ID, a distinct hypothesis and fresh validation before promotion.

Both guarded deployments also passed full isolated CX16 production links. The
candidate adds282 code bytes, no additional data/BSS, and leaves395 bytes in its
MISSION bank. This establishes target fit for the audited source/toolchain,
not strength. Production remains unchanged. Source snapshots, recipes, checks,
portable qualification, target evidence and rejected policy IDs are preserved.
