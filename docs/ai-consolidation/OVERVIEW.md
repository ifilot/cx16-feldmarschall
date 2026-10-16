# Frozen AI release-port validation

Each row belongs to its own matched study. Score is wins plus half draws; errors remain unscored. DOS and honest opponents are separate endpoints. Screening intervals do not establish promotion or correct for selecting hypotheses.

| Cycle | Opponent and setup population | Policy | W / D / L | Score | Errors |
|---|---|---|---:|---:|---:|
| 201 | msdos-1990-v2-normal; original-dos / policy-owned-rotated-v1 | student-fortress-template-flag-bomb-v1-normal | 310 / 199 / 494 | 40.8% | 21 |
| 201 | msdos-1990-v2-normal; original-dos / policy-owned-rotated-v1 | production-fortress-template-q24-cache-v1-normal | 310 / 198 / 496 | 40.7% | 20 |
| 202 | missions-v1-normal; seed-validation corpus / opponent-only-v1 | student-fortress-template-flag-bomb-v1-normal | 322 / 3 / 59 | 84.2% | 0 |
| 202 | missions-v1-normal; seed-validation corpus / opponent-only-v1 | production-fortress-template-q24-cache-v1-normal | 322 / 3 / 59 | 84.2% | 0 |

**Cycle 201:** The frozen cached Q24 Normal-only Fortress port retains the floating champion playing behavior closely enough for release without adding search or hidden information.

[Results and family breakdown](cycle-201-release-port-dos/result.json).
- production-fortress-template-q24-cache-v1-normal minus student-fortress-template-flag-bomb-v1-normal: -0.05 points; 95% paired interval [-0.15, +0.00].
[Interpretation](cycle-201-release-port-dos/CONCLUSION.md).

**Cycle 202:** The frozen cached Q24 Normal-only Fortress port retains the floating champion playing behavior closely enough for release without adding search or hidden information.

[Results and family breakdown](cycle-202-release-port-honest/result.json).
- production-fortress-template-q24-cache-v1-normal minus student-fortress-template-flag-bomb-v1-normal: +0.00 points; 95% paired interval [-1.04, +1.04].
[Interpretation](cycle-202-release-port-honest/CONCLUSION.md).
