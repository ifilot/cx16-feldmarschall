# Quiet contact beliefs: mobile ranks help beyond occupancy, baseline gain remains uncertain

Using per-piece mobile capabilities outperformed the occupancy-only variant in
this exploratory Classic DOS screen. The complete-pair gain was +5.52 percentage
points, with the planned three-contrast 98.3333% interval [+1.35, +9.84]. Against
the unchanged book baseline, the mobile variant's +3.76-point estimate had a
98.3333% interval [-0.43, +8.10]. That comparison remains uncertain after the
prespecified multiplicity qualification, despite its positive ordinary 95%
interval. This is a promising component result, not fresh final validation.

All three frozen arms completed 1,000 attempts each, comprising 500 paired rounds
with seed 2490001, original-DOS armies, rotated policy-owned deployments and a
1,000-ply limit. There was no outcome-driven change to policy, model, gate or
sample size.

| Policy | Wins / draws / losses | Errors | Official scored score |
| --- | --- | --- | --- |
| Unchanged source-template book | 274 / 201 / 499 | 26 | 38.45% |
| Quiet occupancy beliefs | 264 / 186 / 535 | 15 | 36.24% |
| Quiet mobile-rank beliefs | 299 / 229 / 462 | 10 | 41.77% |

Scores count a draw as half a win and exclude unscored errors; they are not win
rates. Compare these arms within this matched setup context. Their percentages
are not directly comparable to fixed-army stress-family experiments or to a
different own deployment such as Fortress.

| Contrast | Complete / planned pairs | Paired effect (points) | 95% interval | Planned 98.3333% interval | Finite missing-score bounds |
| --- | --- | --- | --- | --- | --- |
| Occupancy minus book | 463 / 500 | -1.89 | [-5.29, +1.57] | [-5.99, +2.32] | [-4.35, -0.25] |
| Mobile minus occupancy | 480 / 500 | +5.52 | [+2.03, +9.01] | [+1.35, +9.84] | [+4.15, +6.65] |
| Mobile minus book | 466 / 500 | +3.76 | [+0.27, +7.30] | [-0.43, +8.10] | [+1.30, +4.90] |

The wider intervals qualify the three planned contrasts. Missing-score bounds
assign every error's unknown outcome any value in [0,1] over all attempted games;
they describe this finite cohort and are not confidence intervals. Occupancy
remains below book throughout its finite missing-score bounds, while mobile
remains above both controls in its finite bounds. These observations do not
remove sampling uncertainty: in particular, the mobile-versus-book wider
interval still crosses zero. The independent aggregate review reproduced all
W/D/L/error counts, complete-pair means and finite bounds directly from saved
result/participant metadata. Sign-direction diagnostics retained in result.json
are not substitutes for the planned mean-effect comparisons.

The experiment isolates two channels in the same quiet old-minus-new contact
danger component. Occupancy replaces the native unmoved-token half-risk factor
with the existing public Q12 mobile mass, retaining exchangeable conditional
mobile ranks. Mobile additionally uses each token's conditional mobile-rank
belief. Both retain native MAX aggregation, known contacts and source-vacated
Scout-ray semantics. Captures retain their original scores. Native goal selection,
other nonlinear danger conditions and missions remain unchanged: this is a score
component bridge, not exact recomputation of every evaluator term, an expected
maximum over worlds or a guarantee of safe movement.

Both candidates use the unchanged source-informed 80% eight-template / 20%
uniform-background prior, conditioned on public movements, disclosed ranks and
captures/counts. They receive no actual enemy deployment or private setup seed.
The procedural background is approximate, so this result does not establish
transfer to arbitrary formations or honest human opponents. The separate honest
stress comparison addresses a different population. No policy received additional
search or random draws; actual choices repair native persistent history.

All 51 failures remain preserved and unscored: 49 explicit original-code interrupt
faults and two illegal-move reports. The source-bound metadata-only diagnostic in
`error-actor-diagnostic.json` identifies both illegal returns as DOS-side, using
the [frozen-worker parity method](../research/terminal-error-actors-v1/README.md).
No native-side error appears among these records. This identifies the failing
participant, not whether original code, adapter state or emulation caused its
illegal return. The finite bounds include all 51 regardless of cause. Error
incidence differs across arms and should remain visible alongside official
scored percentages.

Recorded batch execution was 1,266.68 seconds for book, 1,310.53 for occupancy and
1,639.87 for mobile. Game lengths and concurrent load affect these totals.
Separate 300-decision-per-scope forced-screening timing diagnostics measured mean
adapter differences of about 0.085 ms and 0.503 ms respectively, with one-search
and public-history parity. Those observational desktop timings establish neither
controlled speed nor CX16 fit or interactive target cost.

All 3,000 saved games pass Python and native every-state replay and retain Qt6
captures. The terminal audit additionally verifies frozen runtime rebuilds and
own-policy/original-generator setup transcripts. Artifacts and conclusions are
bound by the final manifest. The original-DOS generator and adapter move-RNG
reseeding boundary remain unchanged. Production remains unchanged. A broader
claim for mobile quiet beliefs requires separate fresh validation of an unchanged
registered policy, rather than selecting its favorable 95% interval or changing
the mechanism on this cohort.
