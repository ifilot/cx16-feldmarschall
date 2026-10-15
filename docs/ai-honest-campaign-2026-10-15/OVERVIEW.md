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
| 4 | student-guard-v1-normal | 115 / 17 / 283 | 29.8% | 5 |
| 4 | student-public-flag-threats-v1-normal | 115 / 17 / 283 | 29.8% | 5 |
| 4 | teacher-context-v1-normal | 109 / 7 / 299 | 27.1% | 5 |
| 4 | teacher-public-flag-threats-v1-normal | 116 / 6 / 288 | 29.0% | 10 |
| 5 | teacher-context-v1-normal | 146 / 9 / 394 | 27.4% | 11 |
| 5 | teacher-calibrated-beliefs-v1-normal | 157 / 3 / 393 | 28.7% | 7 |
| 5 | teacher-flag-row-control-v1-normal | 157 / 8 / 381 | 29.5% | 14 |
| 5 | teacher-joint-setup-v1-normal | 162 / 13 / 372 | 30.8% | 13 |
| 7 | student-guard-v1-normal | 123 / 21 / 271 | 32.2% | 5 |
| 7 | student-exact-contact-risk-v1-normal | 142 / 12 / 261 | 35.7% | 5 |
| 7 | teacher-context-v1-normal | 116 / 7 / 288 | 29.1% | 9 |
| 7 | teacher-exact-contact-risk-v1-normal | 123 / 5 / 284 | 30.5% | 8 |

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

Recurrence caveat: only five pair scores changed. The exact two-sided direction test is p=0.0625; its sparse bootstrap interval alone does not establish a regression.


**Cycle 4 hypotheses:** Correct a public logical omission in native Flag defence, without identifying the concealed rank.; Test the same deduction in the Context Teacher observer and masked continuations.

Evidence: [cycle-04-public-flag-defence](cycle-04-public-flag-defence/result.json).

- student-public-flag-threats-v1-normal minus student-guard-v1-normal: +0.0 percentage points; 95% paired interval [+0.0, +0.0].
- teacher-public-flag-threats-v1-normal minus teacher-context-v1-normal: +1.7 percentage points; 95% paired interval [-0.1, +3.7].


**Cycle 5 hypotheses:** A cheap learned setup-style mixture can exploit public Flag/Bomb dependencies missed by independent rank tables.; A control with identical trained Flag-row priors and zero spatial coupling separates positional prior from cross-piece inference.

Evidence: [cycle-05-joint-setup-beliefs](cycle-05-joint-setup-beliefs/result.json).

- teacher-joint-setup-v1-normal minus teacher-flag-row-control-v1-normal: +0.7 percentage points; 95% paired interval [-3.6, +4.8].
- teacher-joint-setup-v1-normal minus teacher-context-v1-normal: +4.0 percentage points; 95% paired interval [+0.2, +7.8].
- teacher-flag-row-control-v1-normal minus teacher-context-v1-normal: +2.8 percentage points; 95% paired interval [-1.4, +7.1].
- teacher-joint-setup-v1-normal minus teacher-calibrated-beliefs-v1-normal: +2.7 percentage points; 95% paired interval [-1.4, +6.8].

Exploratory signal only: the joint-minus-Context interval at 98.3333% is [-0.8, +8.6] points and includes zero. Spatial coupling did not clearly beat the simpler Flag-row control.


**Cycle 7 hypotheses:** Replace maximum of individual hidden-contact mean risks by expected lethal opportunity across contacts, respecting unique ranks and movement constraints.; Test the same cheap probability model in native play and the Context Teacher continuations.

Evidence: [cycle-07-exact-contact-risk](cycle-07-exact-contact-risk/result.json).

- student-exact-contact-risk-v1-normal minus student-guard-v1-normal: +3.3 percentage points; 95% paired interval [-1.3, +8.0].
- teacher-exact-contact-risk-v1-normal minus teacher-context-v1-normal: +1.4 percentage points; 95% paired interval [-2.6, +5.5].


**Preflight failures, without DOS strength results:**

- Cycle 13: Missing AI_TEST in native observer recipe; public query returns unknown command. No saved tournament executed. [Preserved evidence](cycle-13-native-belief-objectives/CONCLUSION.md).
- Cycle 15: AI_TEST alone did not enable public queries; missing outer AI_DIAGNOSTICS guard. No saved tournament executed. [Preserved evidence](cycle-15-native-belief-objectives-v2/CONCLUSION.md).

