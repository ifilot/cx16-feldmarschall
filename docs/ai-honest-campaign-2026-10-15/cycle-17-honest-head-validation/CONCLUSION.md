# Fresh honest head-to-head validation

All 4,200 prespecified Classic games completed with zero errors. Each comparison
used 700 paired rounds across seven setup families, fixed fresh seeds, honest
policies and the same referee army population with swapped sides. Here 50% is a
fair null. None of these scores is a score against DOS.

| Candidate and honest opponent | W / D / L | Score | Paired advantage over 50%, percentage points | 95% interval | 98.3333% interval |
| --- | --- | --- | --- | --- | --- |
| Flag-row prior vs Context Teacher | 700 / 23 / 677 | 50.82% | +0.82 | [-1.39, +2.96] | [-1.86, +3.46] |
| Joint Flag/Bomb prior vs Context Teacher | 714 / 15 / 671 | 51.54% | +1.54 | [-0.61, +3.68] | [-1.07, +4.14] |
| Exact-contact risk vs native guard | 748 / 25 / 627 | 54.32% | +4.32 | [+2.32, +6.36] | [+1.86, +6.79] |

The 98.3333% intervals were prespecified for the three-comparison family. The
teacher prior changes do not demonstrate an honest-opponent gain here. The native
exact-contact change does demonstrate a gain against this honest guard population,
including under the familywise intervals. That does not establish a gain against
DOS: independent cycle 14 found only +0.37 percentage points versus guard against
DOS, with a 95% interval of [-1.62, +2.36] and 52 errors. This is opponent-dependent
evidence, not grounds for a general strength or production promotion claim.

The native/Python replay verified every saved state of all 4,200 games. Frozen
policy archives, cached runtime receipts, the original catalog prefix and all
seven frozen analysis files passed the terminal audit without rebuilding policies.
Qt6 review captures are retained for all three matches. Five prelaunch tests and
their source provenance, earlier preflight revisions, prepared plans, exact results
and score intervals remain available. There are no missing-score cases. Production
is unchanged.

See `result.json`, `audit.json`, each `*.report.json`, `checks-provenance.json` and
`analysis-receipt.json` for the machine-readable evidence.
