# Cycle23: double shell also fails against an honest opponent

The same frozen double-shell deployment package performed substantially worse than
Fortress-only against the honest native guard opponent. This reinforces rejection
of the package: the negative result is not confined to playing against the DOS
engine. Fortress-only also outscored the existing mixture in this auxiliary cohort,
which is a separate signal requiring fresh validation before promotion.

Both players were honest. The opponent used `student-guard-v1-normal` moves with
its own army drawn from the original DOS deployment distribution. Our three arms
kept the same guarded native move policy and their previously frozen own setups.
This separates move-opponent context from army population. No private enemy setup,
referee rank, private deployment seed or DOS move engine entered either player.
These are **honest-opponent results, not additional DOS strength results**.

The plan was frozen before cycle22 outcomes. Seed2330001 supplied200 side-swapped
matched pairs per arm,400 games each,1200 total. All games completed without error
and were independently replayed in Python/native workers. Full public protocol,
setup provenance and Qt6 review artifacts are preserved.

| Own deployment | Wins / draws / losses | Score | Errors |
| --- | ---: | ---: | ---: |
| Existing validated mixture | 186 / 20 / 194 | 49.00% | 0 |
| Fortress only | 216 / 18 / 166 | 56.25% | 0 |
| Double Bomb shell | 145 / 7 / 248 | 37.125% | 0 |

Own and opponent deployment populations differ, so **50% is not a fair-null
benchmark** for these absolute scores. The prespecified within-cohort paired
contrasts isolate the deployment comparison.

| Prespecified paired contrast | Complete pairs | Mean difference | 95% interval | 98.3333% interval |
| --- | ---: | ---: | ---: | ---: |
| Double shell − Fortress (primary) | 200 | −19.125pp | [−25.625, −12.750] | [−27.000, −11.125] |
| Double shell − mixture | 200 | −11.875pp | [−18.750, −5.000] | [−20.250, −3.625] |
| Fortress − mixture | 200 | +7.250pp | [+2.375, +12.125] | [+1.375, +13.375] |

Intervals use20,000 whole matched-pair bootstrap replicates. The wider intervals
account for the three prespecified contrasts within this exploratory cohort.
Every contrast retains all200 pairs; missing-error sensitivity bounds equal the
observed effects because there are no errors. No outcomes were used for retuning.

The extra Bomb-cut certificate and released Lieutenant remain real geometric
properties, but do not imply better defence overall. This package concentrates
Bombs near the Flag and shifts three mobile pieces; the experiment does not
separate those effects or identify which tradeoff caused the loss. It also does
not prove every layered Flag defence is bad. Preserve the rejected immutable IDs
and evidence, and do not promote this candidate.

Fortress-only's positive comparison with the mixture is specific to this honest
opponent/original-army context. Cycle22 showed a smaller, inconclusive paired
Fortress-minus-mixture DOS difference. A new prespecified fresh DOS comparison and
appropriate honest-head validation would be needed for any promotion decision.
Production and all frozen policies remain unchanged.
