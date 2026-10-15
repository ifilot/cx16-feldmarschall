# Retained-label diagnosis

The earlier failure is reproducible, but zero correction was an incomplete offline baseline. Those labels target the **sum** of the production model correction and a teacher delta. The frozen production tree achieves held-out MAE 9.346, versus 11.178 for zero and 11.733 for the rejected replacement. Keeping the existing correction is therefore a meaningful starting point.

The retained 15,508 rows represent only 320 public positions and 50 complete seed groups. The held-out portion has 53 positions in 10 groups. Legal actions and full/cold history copies are correlated observations; they must not be counted as 15,508 independent training situations or 2,492 independent validation situations.

An exploratory capacity check using the existing mean-squared-error tree fitter gives held-out MAE 11.38, 11.73, 11.97, 12.32 and 12.81 for depths 2, 4, 6, 8 and 10. This uses the already-examined holdout and is diagnostic only. More depth with the same target/objective does not repair this dataset's generalization. The fitter minimizes squared error, so increasing depth need not lower absolute error.

There is substantial feature aliasing: 11,502 rows share a 16-feature vector with differing targets, and 122 of 640 position/history groups contain same-vector actions with differing correction targets. This does **not** prove optimal action choice is unrepresentable: differing native scores can resolve the choice. Full/cold copies with identical features have mean absolute target difference only 0.31, so cold/full context changes alone are not the dominant numerical discrepancy among those matched copies.

## Practical next measurement

Retain each legal action's native score, production correction, effective guarded score, teacher value, and the selected actions. The old archive omits native scores and chosen actions, so decision regret cannot honestly be recovered from it alone.

Measure actual runtime choice regret: teacher value of its best action minus teacher value of the student's selected action. Compare against production regret, with roots equally weighted and uncertainty grouped by entire seed pair. Report all held-out roots plus the separately identified disagreement subset. Exact action agreement and top-k inclusion are useful secondary metrics; near ties should not count as equally bad as large mistakes.

A useful learner predicts residual improvements to production and learns within-root action ordering. A pairwise or listwise objective can account for native score gaps and teacher preference margins. Predicting the correction alone, or ranking corrections alone, does not match the deployment decision. Apply runtime guards in offline evaluation. Independent sampled-world labels should measure preference stability and evaluate decisions separately from the batch that supplied training targets.

Offline teacher agreement is a transfer check, not a strength claim. Fresh, fixed-budget full games remain necessary, with matched league improvement over production as the primary endpoint and inconclusive results explicitly retained.

Files: `evaluation-labels.json`, `evaluation-capacity.json`. Reproduce retained-label statistics with `python3 tools/diagnose_transfer_labels.py`. No policy or production behavior was changed by this diagnostic.
