# Compact native back-row prior: DOS screening

The minimal honest prior raised score from 19.34% to 31.06% for the compact native implementation on this fixed original-DOS population. The three frozen arms completed 3,000 attempts with 190 unscored DOS errors. Scores count wins plus half draws among scored games.

| Policy | W / D / L | Errors | Score |
| --- | --- | ---: | ---: |
| Native baseline |138 /83 /707 |72 |19.34% |
| Python pure back-row prior |231 /125 /586 |58 |31.16% |
| Compact native back-row prior |229 /126 /585 |60 |31.06% |

Compact minus native baseline is +11.46 percentage points over 395 complete matched pairs: 95% paired interval [+7.59,+15.25]pp and 98.3333% interval [+6.71,+16.14]pp. Assigning all missing outcomes adversarially gives finite-cohort effect bounds[+4.05,+17.25]pp; these are sensitivity bounds, not confidence intervals. Python minus baseline is +11.22pp,95% [+7.39,+15.10], missing bounds[+4.20,+17.20].

The compact-minus-Python bridge is +0.23pp,95% [-0.90,+1.41] and 98.3333%[-1.19,+1.70], over 442 complete pairs. It detects no difference; it is not an equivalence test. Missing-outcome bounds[-5.95,+5.85]pp further limit that comparison. The distinct implementations intentionally differ in rounding and evaluator integration.

This is positive strategic screening evidence for an honest, small population prior. A fresh independent validation is required before promotion; the frozen honest-opponent stress cohort is separate. No source-template-policy comparison occurs in this cohort, and results from other seeds cannot substitute for a matched comparison.

Every saved state passed Python/native replay, and all three Qt6 captures are preserved. Separate source/target evidence establishes the compact policy links on the CX16, including 80 real banked decision comparisons; this tournament is desktop strength evidence. Production is unchanged. See audit.json for terminal rebuild and exact own/original-DOS deployment audits.
