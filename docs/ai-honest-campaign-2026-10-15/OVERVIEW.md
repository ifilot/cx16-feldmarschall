# Honest AI campaign: cumulative DOS results

Scores count wins plus half of draws; original DOS errors are excluded. Compare policies within their matched cycle. Screening results do not establish promotion.

| Cycle / hypothesis | Policy | W / D / L | DOS score | Errors |
|---|---|---:|---:|---:|
| 1 | teacher-context-v1-normal | 70 / 9 / 198 | 26.9% | 3 |
| 1 | teacher-calibrated-beliefs-v1-normal | 82 / 2 / 191 | 30.2% | 5 |
| 1 | teacher-context-worlds32-v1-normal | 66 / 4 / 209 | 24.4% | 1 |
| 1 | teacher-calibrated-worlds32-v1-normal | 57 / 5 / 213 | 21.6% | 5 |
| 2 | teacher-context-v1-normal | 114 / 6 / 291 | 28.5% | 9 |
| 2 | teacher-latin-worlds-v1-normal | 111 / 5 / 296 | 27.5% | 8 |
| 2 | teacher-army-activation-v1-normal | 108 / 14 / 291 | 27.8% | 7 |
| 2 | teacher-paired-confidence-v1-normal | 115 / 8 / 288 | 29.0% | 9 |
| 3 | teacher-context-v1-normal | 118 / 4 / 295 | 28.8% | 3 |
| 3 | teacher-capture-quiescence-v1-normal | 107 / 4 / 305 | 26.2% | 4 |
| 3 | teacher-sparse-depth-v1-normal | 114 / 7 / 298 | 28.0% | 1 |
| 3 | teacher-recurrence-escape-v1-normal | 116 / 2 / 300 | 28.0% | 2 |
| 3 | teacher-uniform-worlds-v1-normal | 118 / 3 / 295 | 28.7% | 4 |

**Cycle 1 hypotheses:** More public-compatible enemy armies reduce decision noise at four times rollout work.; Calibrated beliefs benefit more from 32 armies than from eight; test the model-by-budget interaction.

Evidence: [cycle-01-sampling-budget](cycle-01-sampling-budget/result.json).

- teacher-context-worlds32-v1-normal minus teacher-context-v1-normal: -2.2 percentage points; 95% paired interval [-7.5, +3.1].
- teacher-calibrated-worlds32-v1-normal minus teacher-calibrated-beliefs-v1-normal: -8.4 percentage points; 95% paired interval [-14.5, -2.5].
- teacher-calibrated-beliefs-v1-normal minus teacher-context-v1-normal: +3.2 percentage points; 95% paired interval [-2.6, +9.0].
- teacher-calibrated-worlds32-v1-normal minus teacher-context-worlds32-v1-normal: -2.6 percentage points; 95% paired interval [-7.8, +2.6].
- model by sampling-budget interaction: -7.3 percentage points; 95% paired interval [-14.6, +0.0].


**Cycle 2 hypotheses:** Latin-hypercube random coordinates spread eight count-consistent worlds without additional native searches.; Bounded quiet-move potential rewards opening teammates routes to central crossings; enemy ranks unused.; Require paired corrected advantage over native move to exceed one jackknife standard error; no extra rollouts.

Evidence: [cycle-02-cheap-mechanisms](cycle-02-cheap-mechanisms/result.json).

- teacher-latin-worlds-v1-normal minus teacher-context-v1-normal: -0.4 percentage points; 95% paired interval [-5.0, +4.1].
- teacher-army-activation-v1-normal minus teacher-context-v1-normal: -0.8 percentage points; 95% paired interval [-5.5, +4.1].
- teacher-paired-confidence-v1-normal minus teacher-context-v1-normal: +0.5 percentage points; 95% paired interval [-3.4, +4.5].


**Cycle 3 hypotheses:** Finish policy-selected exchanges beyond four plies, stopping before a quiet move, with at most four extra masked decisions.; Spend eight plies only when public root mobility has at most twelve legal actions, retaining four otherwise.; Remember repeated friendly formations across actors and escape long quiet loops when a similarly valued fresh continuation exists.; Ablate handwritten approach/retreat weights while retaining exactly the same IID count-consistent world proposal; negative-control belief test.

Evidence: [cycle-03-horizons-and-memory](cycle-03-horizons-and-memory/result.json).

- teacher-capture-quiescence-v1-normal minus teacher-context-v1-normal: -2.9 percentage points; 95% paired interval [-7.0, +1.1].
- teacher-sparse-depth-v1-normal minus teacher-context-v1-normal: -0.7 percentage points; 95% paired interval [-5.0, +3.6].
- teacher-recurrence-escape-v1-normal minus teacher-context-v1-normal: -1.0 percentage points; 95% paired interval [-1.9, -0.2].
- teacher-uniform-worlds-v1-normal minus teacher-context-v1-normal: -0.1 percentage points; 95% paired interval [-2.2, +2.1].

