# Two-hour honest Classic AI campaign

Each row belongs to its own matched study. Score is wins plus half draws; errors remain unscored. DOS and honest opponents are separate endpoints. Screening intervals do not establish promotion or correct for selecting hypotheses.

| Cycle | Opponent and setup population | Policy | W / D / L | Score | Errors |
|---|---|---|---:|---:|---:|
| 101 | msdos-1990-v2-normal; original-dos / policy-owned-rotated-v1 | student-guard-v1-normal | 15 / 18 / 212 | 9.8% | 11 |
| 101 | msdos-1990-v2-normal; original-dos / policy-owned-rotated-v1 | student-target-assignment-v1-normal | 16 / 16 / 212 | 9.8% | 12 |
| 102 | missions-v1-normal; development corpus | student-guard-v1-normal | 51 / 3 / 42 | 54.7% | 0 |
| 102 | missions-v1-normal; development corpus | student-target-assignment-v1-normal | 49 / 3 / 44 | 52.6% | 0 |
| 103 | msdos-1990-v2-normal; original-dos / policy-owned-rotated-v1 | student-fortress-template-flag-bomb-v1-normal | 83 / 43 / 125 | 41.6% | 5 |
| 103 | msdos-1990-v2-normal; original-dos / policy-owned-rotated-v1 | student-fortress-template-mobile-goals-v1-normal | 68 / 61 / 122 | 39.2% | 5 |
| 104 | missions-v1-normal; development corpus | student-fortress-template-flag-bomb-v1-normal | 53 / 1 / 42 | 55.7% | 0 |
| 104 | missions-v1-normal; development corpus | student-fortress-template-mobile-goals-v1-normal | 51 / 0 / 45 | 53.1% | 0 |
| 107 | missions-v1-normal; development corpus | student-fortress-template-flag-bomb-v1-normal | 53 / 1 / 42 | 55.7% | 0 |
| 107 | missions-v1-normal; development corpus | student-fortress-template-missed-background-v2-normal | 54 / 1 / 41 | 56.8% | 0 |
| 109 | missions-v1-normal; development corpus | student-fortress-template-flag-bomb-v1-normal | 49 / 1 / 46 | 51.6% | 0 |
| 109 | missions-v1-normal; development corpus | student-fortress-template-regime-reset-v1-normal | 48 / 1 / 47 | 50.5% | 0 |

**Cycle 101:** Reassign one redundant capable pursuer to an uncovered disclosed mobile target while retaining the original primary attacker. Previously registered but never benchmarked; this campaign tests its first full-policy outcomes.

[Results and family breakdown](cycle-101-public-task-allocation/result.json).
- student-target-assignment-v1-normal minus student-guard-v1-normal: +0.00 points; 95% paired interval [-0.85, +1.07].
[Interpretation](cycle-101-public-task-allocation/CONCLUSION.md).

**Cycle 102:** Does capability-aware public target reassignment improve move play against an honest missions opponent on unfamiliar synthetic deployment families, rather than only exploiting original DOS formations?

[Results and family breakdown](cycle-102-task-allocation-generality/result.json).
- student-target-assignment-v1-normal minus student-guard-v1-normal: -2.08 points; 95% paired interval [-5.21, +0.52].
[Interpretation](cycle-102-task-allocation-generality/CONCLUSION.md).

**Cycle 103:** Retain already computed token-specific mobile-rank beliefs when choosing pursuit goals, rather than discarding that information before long-range routing. Immediate capture and danger values remain unchanged.

[Results and family breakdown](cycle-103-mobile-pursuit/result.json).
- student-fortress-template-mobile-goals-v1-normal minus student-fortress-template-flag-bomb-v1-normal: -1.88 points; 95% paired interval [-8.54, +4.79].
[Interpretation](cycle-103-mobile-pursuit/CONCLUSION.md).

**Cycle 104:** Retain already computed token-specific mobile-rank beliefs when choosing pursuit goals, rather than discarding that information before long-range routing. Immediate capture and danger values remain unchanged.

[Results and family breakdown](cycle-104-mobile-pursuit-generality/result.json).
- student-fortress-template-mobile-goals-v1-normal minus student-fortress-template-flag-bomb-v1-normal: -2.60 points; 95% paired interval [-10.42, +5.21].
[Interpretation](cycle-104-mobile-pursuit-generality/CONCLUSION.md).

**Cycle 105:** An opponent declining an available unprotected winning capture provides weak evidence about that concealed piece rank; exact rank-level conditioning may improve public Flag/Bomb risk estimates even after fixed templates are eliminated.

No completed strength result. [Frozen plan](cycle-105-missed-capture-beliefs/plan.json).

**Cycle 106:** Test the same single missed-capture rank hypothesis with corrected public source-vacancy geometry: protected captures must not be interpreted as free opportunities.

No completed strength result. [Frozen plan](cycle-106-missed-capture-source-vacancy/plan.json).

**Cycle 107:** Test the same single missed-capture rank hypothesis with corrected public source-vacancy geometry: protected captures must not be interpreted as free opportunities.

[Results and family breakdown](cycle-107-missed-capture-generality/result.json).
- student-fortress-template-missed-background-v2-normal minus student-fortress-template-flag-bomb-v1-normal: +1.04 points; 95% paired interval [-2.08, +4.17].
[Interpretation](cycle-107-missed-capture-generality/CONCLUSION.md).

**Cycle 108:** When public evidence eliminates all previously plausible opening templates, discard the old pursuit goals once so stale source-specific commitments do not outlive the belief model that selected them.

No completed strength result. [Frozen plan](cycle-108-belief-regime-reset/plan.json).

**Cycle 109:** When public evidence eliminates all previously plausible opening templates, discard the old pursuit goals once so stale source-specific commitments do not outlive the belief model that selected them.

[Results and family breakdown](cycle-109-regime-reset-generality/result.json).
- student-fortress-template-regime-reset-v1-normal minus student-fortress-template-flag-bomb-v1-normal: -1.04 points; 95% paired interval [-3.12, +0.00].
[Interpretation](cycle-109-regime-reset-generality/CONCLUSION.md).

**Additional hypotheses evaluated before tournaments**

These mechanism and incidence checks supply no DOS score. Rejected preflights remain visible.

- **Use declined public captures to reweight only source templates** (rejected preflight: inert consumer): Evidence appeared in 188 of 200 side histories from 100 old screening games, but no component posterior changed above 1e-12. Public facts had resolved or eliminated those components. Zero new tournament games; no strength claim. [Evidence 1](research/information/README.md). [Evidence 2](research/information/activation.json).
- **Preserve an undisclosed Marshal or General when a disclosed actor has an equally good safe capture** (rejected preflight: no eligible actions): Zero eligible choices in 356 fixed sampled roots from 48 old screening games, both colors. All 6,520 intervening baseline decisions reproduced. Even the same-victim alternative gate failed, so relaxing only exact score equality would not establish incidence. Zero new tournament games; no strength claim. [Evidence 1](research/objectives/SECRECY-CONCLUSION.md). [Evidence 2](research/objectives/secrecy-result.json).
