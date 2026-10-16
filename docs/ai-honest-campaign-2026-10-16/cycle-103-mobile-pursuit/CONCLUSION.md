# Mobile-rank beliefs in pursuit: original DOS screen

Keeping full public mobile-rank beliefs in long-range pursuit did **not establish
a DOS gain**. The frozen candidate scored **39.24%** (68 wins, 61 draws, 122
losses; five unscored errors), versus **41.63%** for the unchanged Fortress
template reference (83 wins, 43 draws, 125 losses; five errors). Score is wins
plus half draws, not a win rate.

Among the 120 side-swapped pairs complete in both arms, candidate minus
reference was **−1.88 percentage points**, with the planned 95% paired interval
**[−8.54, +4.79]**. Thirty-three pairs improved, 39 worsened and 48 tied. This
exploratory sample establishes neither a population gain nor a population loss.
Its interval also does not establish equivalence.

The [finite missing-outcome analysis](error-sensitivity.json) retains all 128
planned pairs and allows each error score any value from zero to one. The
candidate-minus-reference bounds are **[−4.30, −0.39] points**: even the most
favorable assignment of these missing outcomes leaves a deficit on this
particular sampled cohort. These bounds describe missing-score uncertainty,
not sampling uncertainty or a confidence interval. They therefore do not
contradict the wider population interval crossing zero. Error prefixes remain
saved and unscored in official standings.

The [trajectory diagnostic](divergence.json) confirms that this was an active
strategic change. Of 248 matched games complete in both arms, 201 had different
move sequences; 71 of those retained the same outcome. Six more games diverged
before an error prefix ended; two games had identical prefixes and errors in
both arms. Every one of the 207 observed first different moves belonged to the
candidate at an identical preceding position. Later differences are dependent
consequences, not independent activations. This mechanism was substantially
more active than the earlier sparse tactical gates, yet activity did not convert
into a score gain here.

The hypothesis was to retain already computed per-token mobile beliefs when
choosing distant pursuit targets. Immediate capture expectations, danger,
deployment and RNG calls remain the comparator's implementation; no extra
search or enemy private information was introduced. Expected-reward reasoning
over beliefs motivates the experiment, but the resulting route heuristic is
not an optimal partially observed controller. See the
[mechanism and scientific motivation](../research/objectives/README.md).

The fixed sample contains 512 attempts with matched original-DOS armies and
move seeds, identical own Fortress armies, and rotated policy-owned pairing.
The [independent arithmetic review](independent-review.json) recomputed standings,
pair means, root matching and finite error bounds directly from SQLite rows
without the runner's statistical helpers. Python/native replay, exact source
rebuilds and Qt6 review are retained separately in the reports and audit.

Observed execution was 402.68 seconds for the candidate arm and 198.87 seconds
for the reference arm. These are whole-arm host timings under the campaign's
workload, including different game trajectories, rather than an isolated causal
measurement of the new calculation. The desktop implementation adds a 2,000-byte
native goal table and a larger protocol buffer; CX16 fit and latency are not
established.

Preserve the candidate and rejected evidence. The separately frozen honest
development comparison in cycle 104 answers another endpoint; neither a transfer
claim nor promotion follows from this DOS screen. No policy, coefficient,
stopping rule or source was changed in response to these outcomes. Production
remains unchanged.
