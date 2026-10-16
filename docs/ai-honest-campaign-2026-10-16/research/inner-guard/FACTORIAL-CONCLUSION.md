The preregistered factorial comparison **does not establish an interaction between
the inner-Sergeant placement and source-template inference**. On97common four-arm
complete pairs, the interaction `(bookGuard-bookBase)-(nativeGuard-nativeBase)`
is **-7.990percentage points**, with exploratory95% paired bootstrap interval
**[-18.041,+2.320]**. Arbitrary-error finite-cohort bounds over all128planned
scenarios are **[-14.0625,+1.9531]points**. Both intervals include zero and concern
different uncertainties; neither is evidence of equivalence.

The four actual executions contain1024attempts. Errors are bookBase5, bookGuard5,
nativeBase15 and nativeGuard16, leaving31scenarios with at least one missing
score. Their unknown outcomes remain unscored. The bootstrap uses only the same97
complete eight-game blocks for all four cells. The finite-cohort bounds retain
all128planned blocks and allow every missing score any value in[0,1]. No two
contrasts from differently filtered cohorts are subtracted.

The helper confirms identical own armies for book/native within each placement
level, differing armies between placement levels, and identical opponent armies,
move seeds, scenario IDs, rules and game limits across all four cells. The same
frozen DOS source/runtime is used. Four distinct policy IDs, physical files and
file hashes prevent reused controls from being counted as independent executions.
The protocol was frozen before C110/C114 outcomes were inspected.

C110 separately rejects this placement as a DOS improvement with source inference
on its fixed screen; C114 supplies no established effect with native counts.
Those individual findings do not establish that inference causes the difference
between placement effects. Local surviving-guard recapture fixtures remain
mechanically correct, but do not identify why a complete setup wins or loses.
No policy is promoted, no placement is retuned and no final validation is claimed.

The independent review reconstructs SQL outcomes in integer half-point units and
reproduces the interaction, all128pair bounds and the20,000-replicate interval
exactly, without importing helper analysis functions. All1024saved games/prefixes
were independently replayed in Python, and native all-state verification receipts
and frozen own/DOS setup reproductions were checked.

Evidence: `FACTORIAL-PROTOCOL.json`, `factorial-result.json`,
`factorial-analysis.log`, `factorial-tests.log`, and
`../evaluation/inner-guard-factorial-independent-review.json`.
