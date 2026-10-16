# Independent honest head-to-head validation

Status: completed and audited: 4,200 games, zero errors. See `CONCLUSION.md`.
No interim policy selection or tuning.
The original preparation note is preserved in `preparation-README.md`.

Three direct comparisons each use 100 paired rounds across seven Classic setup
families (1,400 games): Flag-row prior versus Context Teacher, joint Flag/Bomb
prior versus Context Teacher, and native exact-contact risk versus native guard.
The fresh seeds, immutable policy IDs and fixed sample sizes are in `plan.json`.

`analysis-sources.zip` and `analysis-receipt.json` froze the shared runner and
analysis files before the first game. Final prelaunch checks passed five tests;
previous preflight revisions are retained. The cohort audit verifies the prepared
plan, catalog prefix, policy archives and unchanged analysis source hashes.

These are direct comparisons against honest opponents with a fair-null score of
50%, using the same referee deployment population and swapped sides. Report all
three endpoints with 95% and 98.3333% paired intervals, every error and missing-score
bounds. These results alone cannot justify promotion; independent DOS validation,
correctness and target cost require joint review. Production remains unchanged.
