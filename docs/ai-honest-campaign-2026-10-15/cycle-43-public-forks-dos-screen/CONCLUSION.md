# Public fork screen

The bounded public fork strategy did not demonstrate a DOS strength gain in this
fresh, fixed Classic screen. All 2,000 prespecified attempts completed and passed
Python/native replay. The 67 error games remain officially unscored. A
metadata-only frozen-worker actor audit attributes all 67 to the DOS side (63 interrupt faults and four
illegal returns), with no recorded native-policy failure; illegal-return root
cause is unresolved. `error-actors-review.json` preserves that check. This
attribution does not recover missing outcomes. Production is unchanged; this prototype is not promoted.

| Policy | Wins / draws / losses | Errors | Official scored score |
| --- | --- | --- | --- |
| Parent source-template policy | 275 / 209 / 482 | 34 | 39.286% |
| Public fork policy | 276 / 206 / 485 | 33 | 39.193% |

Each arm had 1,000 attempts and 500 paired rounds at frozen seed 2530001, using
original-DOS enemy armies and rotated policy-owned deployments. The opponent was
`msdos-1990-v2-normal`. An absolute 50% is not a fair-strength null against the
DOS information advantage.

Fork minus parent was -0.053 percentage points across 469 complete pairs. The
95% paired interval was [-0.640, +0.533] percentage points; the wider 98.3333%
interval was [-0.746, +0.693]. There were six positive, seven negative and 456
tied pair effects. This is no demonstrated improvement, and it is not an
equivalence or no-harm guarantee. Assigning every missing game outcome
adversarially gives finite-cohort effect bounds [-3.45, +3.25] percentage points;
these are not confidence intervals. Thirty-one of the 500 pairs had an error in
at least one arm.

The wider interval remains part of the interpretation because the prospective
`SHARED-CONTROL-AMENDMENT.md` planned a second tactical treatment using these same
1,000 parent games. That design is not an independent cohort. Its completion or
deferral does not retrospectively narrow this result's uncertainty family. No
validation outcomes were used to develop either tactical treatment.

The strategic idea was a quiet public double threat with a positive bounded
material-conversion certificate strictly better than the native common control.
Proofs account for count-feasible public enemy outcomes, collateral losses and
terminal counterwins; a transient exact-public-successor witness can execute the
certified capture on the next turn. Immediate Flag wins take priority, and an
incomplete proof at the shared 20,000-outcome limit falls back. This short
certificate does not prove long-term Flag safety or game value. The unchanged
opening posterior and native search use no enemy private ranks or setup. The
Python prototype has substantial eligible-root cost and no CX16 fit qualification.

To fit the fixed sample in the campaign window, the two full arms ran on separate
pools with unchanged IDs, seeds, sample sizes and deployment rules. The first outer
evaluator correctly rejected the still-running fork file after completing the
parent report. `parallel-incomplete-analysis.log` preserves that analysis-only
failure. After both files were complete, final analysis reran over existing saved
artifacts only: no games were restarted or duplicated. Final archive/runtime,
original-army, replay and Qt6 checks are recorded in `audit.json`; exact counts,
intervals and missing-outcome sensitivity remain in `result.json`.
