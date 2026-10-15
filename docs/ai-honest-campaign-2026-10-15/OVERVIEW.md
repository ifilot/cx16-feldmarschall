# Honest AI campaign: cumulative DOS results

Scores count wins plus half of draws; original DOS errors are excluded. Compare policies within their matched cycle. Screening results do not establish promotion.

| Cycle / hypothesis | Policy | W / D / L | DOS score | Errors |
|---|---|---:|---:|---:|
| 1 | teacher-context-v1-normal | 70 / 9 / 198 | 26.9% | 3 |
| 1 | teacher-calibrated-beliefs-v1-normal | 82 / 2 / 191 | 30.2% | 5 |
| 1 | teacher-context-worlds32-v1-normal | 66 / 4 / 209 | 24.4% | 1 |
| 1 | teacher-calibrated-worlds32-v1-normal | 57 / 5 / 213 | 21.6% | 5 |

**Cycle 1 hypotheses:** More public-compatible enemy armies reduce decision noise at four times rollout work.; Calibrated beliefs benefit more from 32 armies than from eight; test the model-by-budget interaction.

Evidence: [cycle-01-sampling-budget](cycle-01-sampling-budget/result.json).

- teacher-context-worlds32-v1-normal minus teacher-context-v1-normal: -2.2 percentage points; 95% paired interval [-7.5, +3.1].
- teacher-calibrated-worlds32-v1-normal minus teacher-calibrated-beliefs-v1-normal: -8.4 percentage points; 95% paired interval [-14.5, -2.5].
- teacher-calibrated-beliefs-v1-normal minus teacher-context-v1-normal: +3.2 percentage points; 95% paired interval [-2.6, +9.0].
- teacher-calibrated-worlds32-v1-normal minus teacher-context-worlds32-v1-normal: -2.6 percentage points; 95% paired interval [-7.8, +2.6].
- model by sampling-budget interaction: -7.3 percentage points; 95% paired interval [-14.6, +0.0].

