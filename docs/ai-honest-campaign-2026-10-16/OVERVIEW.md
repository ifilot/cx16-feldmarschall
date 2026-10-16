# Two-hour honest Classic AI campaign

Each row belongs to its own matched study. Score is wins plus half draws; errors remain unscored. DOS and honest opponents are separate endpoints. Screening intervals do not establish promotion or correct for selecting hypotheses.

| Cycle | Opponent and setup population | Policy | W / D / L | Score | Errors |
|---|---|---|---:|---:|---:|
| 101 | msdos-1990-v2-normal; original-dos / policy-owned-rotated-v1 | student-guard-v1-normal | 15 / 18 / 212 | 9.8% | 11 |
| 101 | msdos-1990-v2-normal; original-dos / policy-owned-rotated-v1 | student-target-assignment-v1-normal | 16 / 16 / 212 | 9.8% | 12 |
| 102 | missions-v1-normal; development corpus | student-guard-v1-normal | 51 / 3 / 42 | 54.7% | 0 |
| 102 | missions-v1-normal; development corpus | student-target-assignment-v1-normal | 49 / 3 / 44 | 52.6% | 0 |
| 104 | missions-v1-normal; development corpus | student-fortress-template-flag-bomb-v1-normal | 53 / 1 / 42 | 55.7% | 0 |
| 104 | missions-v1-normal; development corpus | student-fortress-template-mobile-goals-v1-normal | 51 / 0 / 45 | 53.1% | 0 |

**Cycle 101:** Reassign one redundant capable pursuer to an uncovered disclosed mobile target while retaining the original primary attacker. Previously registered but never benchmarked; this campaign tests its first full-policy outcomes.

[Results and family breakdown](cycle-101-public-task-allocation/result.json).
- student-target-assignment-v1-normal minus student-guard-v1-normal: +0.00 points; 95% paired interval [-0.85, +1.07].
[Interpretation](cycle-101-public-task-allocation/CONCLUSION.md).

**Cycle 102:** Does capability-aware public target reassignment improve move play against an honest missions opponent on unfamiliar synthetic deployment families, rather than only exploiting original DOS formations?

[Results and family breakdown](cycle-102-task-allocation-generality/result.json).
- student-target-assignment-v1-normal minus student-guard-v1-normal: -2.08 points; 95% paired interval [-5.21, +0.52].
[Interpretation](cycle-102-task-allocation-generality/CONCLUSION.md).

**Cycle 103:** Retain already computed token-specific mobile-rank beliefs when choosing pursuit goals, rather than discarding that information before long-range routing. Immediate capture and danger values remain unchanged.

No completed strength result. [Frozen plan](cycle-103-mobile-pursuit/plan.json).

**Cycle 104:** Retain already computed token-specific mobile-rank beliefs when choosing pursuit goals, rather than discarding that information before long-range routing. Immediate capture and danger values remain unchanged.

[Results and family breakdown](cycle-104-mobile-pursuit-generality/result.json).
- student-fortress-template-mobile-goals-v1-normal minus student-fortress-template-flag-bomb-v1-normal: -2.60 points; 95% paired interval [-10.42, +5.21].
