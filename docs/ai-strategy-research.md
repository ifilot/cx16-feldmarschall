# Strategy research and experiments — 2026-10-14

The objective is stronger play within the Commander X16's memory and move-time
budget. The frozen coordinated-mission policy remains the production reference.
Five independently implemented alternatives and one combination were tested;
none earned promotion over the validated mission policy.
These are changes in memory, evaluation and search, rather than parameter sweeps.

## Tested alternatives

Classic rules; identical deployments and move seeds, engine sides swapped.
Development seed offset: 12,000,000. Independent validation: 13,000,000.
Scores count draws as half a win; intervals resample complete deployment pairs.

| Strategy | Level | Games | Score | Paired 95% interval | Decision |
| --- | --- | ---: | ---: | --- | --- |
| Remember fortified flag sectors after guards are removed | Normal | 120 | 50.0% | 50.0–50.0% | Reject promotion |
| Same sector memory | Hard | 120 | 50.0% | 50.0–50.0% | Reject promotion |
| Raise values of ranks with no surviving equal or stronger enemy | Normal | 120 | 50.0% | 50.0–50.0% | Reject promotion |
| Same capability values | Hard | 120 | 50.0% | 47.5–52.5% | Reject promotion |
| Extend disclosed captures through one friendly recapture | Hard development | 120 | 50.8% | 48.3–53.3% | Validate independently |
| Same exchange extension | Hard validation | 600 | 49.9% | 48.7–51.2% | Reject promotion |
| Discovery value for a nearby piece's uncertain attack decision | Normal | 120 | 47.9% | 39.6–56.2% | Reject promotion |
| Same purposeful reconnaissance | Hard | 120 | 49.2% | 40.0–58.3% | Reject promotion |
| Condition unmoved-rank estimates on mobile ranks consumed by moved pieces | Normal | 120 | 46.7% | 40.0–53.3% | Reject promotion |
| Same occupancy inference | Hard | 120 | 46.2% | 38.3–53.8% | Reject promotion |
| Occupancy inference plus purposeful reconnaissance | Normal development | 120 | 54.2% | 45.8–62.5% | Validate independently |
| Same combination | Hard development | 120 | 45.0% | 36.2–53.8% | Reject promotion |
| Same combination | Normal validation | 600 | 49.9% | 46.2–53.8% | Reject promotion |

Exact 50% results do not mean identical play: the sector prototype produced
different traces in 2/60 Normal and 1/60 Hard pairs; capability values in 4/60
Normal and 5/60 Hard pairs; exchange search in 6/60 Hard development pairs.
The narrow intervals describe these paired opponents and deployments, not
performance against arbitrary opponents. Sparse activation is itself a finding:
these mechanisms did not address most decisions in this sample.

Every run in these two strategy batches and final validation preserves full
sources, executable snapshots, SHA-256 identities,
commands, deployments, seeds, results and complete moves in
[the experiment ledger](ai-experiments.json) and `docs/ai-runs/`. Archive integrity
verification covers 39 runs and 12,006 games after both batches and final validation.

The opt-in prototypes are reproducible with `make native-sector`,
`make native-capability`, and `make native-exchanges`. Corresponding
`test-ai-*` targets exercise masked-information fairness across all 64 rules
combinations. Sector fixtures verify continuation after guard removal,
snapshot restoration and contradiction. Exchange fixtures verify a General
capture followed by Marshal capture and Spy recapture, and board restoration.
Production has none of the experimental macros enabled.

The second batch uses development offset 14,000,000 and independent combination
validation offset 15,000,000. `make native-probes`, `make native-beliefs`, and
`make native-inference` reproduce its three policies; matching `test-ai-*` targets
run focused and hidden-information fixtures. Probes changed 59/60 Normal and
60/60 Hard development pair traces, so failure to improve cannot be explained
by rare activation alone. Its proximity criterion is Manhattan distance, which
can mistake pieces separated by lakes or blockers for useful beneficiaries.

Occupancy inference is our own combinatorial calculation under uniform rank
assignments consistent with public inventory and movement. With `m` mobile
hidden ranks and `k` moved unknown pieces, an unmoved target's relative rank
weight is `count[t] * (m-k)` for mobile types and `count[t] * m` for immobile types.
This preserves integer precision and respects Moving Bomb/Flag options. When
Silent Defense leaves undisclosed casualties in public counts, those counts
represent a larger latent inventory, so the estimate is not a fully specified
posterior over the surviving board. Focused tests prove that one moved Scout
and one stationary Bomb can be distinguished from their public inventory;
they also cover the Moving Bomb mutual-destruction payoff. Exhaustive fairness
checks pass for all 64 rule combinations.

The combined Normal development signal did not replicate. Neither an inference
improvement nor a local estimate of information value is sufficient evidence
of improved whole-game decisions. The suggested causal explanations in the
development notes remain hypotheses; these games do not isolate a unique cause.

## Direct measurement of the retained improvement

Independent final classic validation, seed offset 16,000,000, compares the
retained production engine directly with the frozen pre-upgrade v0.2.0 engine:

| Current level | Games | Wins / draws / losses | Score | Paired 95% interval |
| --- | ---: | --- | ---: | --- |
| Normal | 600 | 461 / 39 / 100 | 80.1% | 77.2–82.9% |
| Hard | 600 | 396 / 117 / 87 | 75.8% | 72.7–78.8% |

The reference is the original single policy, not a difficulty-matched new engine.
These results establish improvement for the tested deployment distribution;
they do not establish Hard superiority over current Normal or human strength.

Sector memory uses 20 bytes per AI instance and public evidence only. It is a
spatial hypothesis, not a probability distribution over hidden ranks. Capability
values are coarse and shared between friendly and enemy material evaluation;
an asymmetric model would represent army-specific scarcity more accurately.
Exchange search handles a disclosed capture of the root mover only; it excludes
concealed recaptures and further continuations. It is a bounded approximation
to quiescence search, not a complete three-ply game tree. The prototypes are
native experiments; their X16 memory cost and move time have not been validated.

## Primary sources and adaptations

The [Demon of Ignorance author's description](https://github.com/braathwaate/stratego)
uses selective search, discovery value and behavior-based suspected ranks. It
motivated the exchange and capability experiments. Its deployment uses a desktop
search budget; its reported playing strength is the author's assessment.
Our independently written prototypes reproduce selected ideas, not that engine.

[DeepNash](https://arxiv.org/abs/2206.15378) demonstrates self-play policy learning
for Stratego without game-tree search. This motivates moving expensive learning
off the X16 and exporting a small policy; the paper does not establish that a
small distilled policy will retain its strength.

[Ataraxos, revision 2](https://arxiv.org/html/2511.07312v2), dated 2026-10-04,
combines a policy/value model, learned hidden-piece beliefs, and test-time
search. It also learns deployments and moves in coupled processes. The useful
architectural lesson for this project is to separate inference from action
selection and learn deployment choices alongside play. Directly running its
networks and search on an X16 has not been shown feasible. Offline training and
distillation are our proposed adaptation, not a claim made by the paper.

## Next substantial experiments

1. **Tracked enemy identities and compact beliefs.** Preserve movement history
   for each enemy piece, including long Scout moves and disclosed combat. First
   use only logically justified rank elimination. Then evaluate calibrated
   behavioral likelihoods learned offline. Treat bluffing as uncertainty. Counts,
   per-piece beliefs and public observations must agree; concealed truth must
   never enter runtime inference. Silent Defense needs separate observation
   handling. The current board snapshot alone cannot preserve all this history.
2. **Reconnaissance with a purpose.** Choose probes by how discovery changes
   future legal attacks and safe routes. Prioritize a blocking defender or a
   suspected superior rank when a suitable attacker can exploit the discovery.
   Test information gained and subsequent flag conversion, as well as wins.
3. **Offline teacher and compact student.** Generate a fixed corpus with the
   native referee, then use sampled consistent hidden layouts and a stronger
   desktop policy to label candidate decisions. Train a shallow tree or integer
   lookup policy over permitted features. Runtime must receive only the player's
   information. Compare against a league of frozen policies on held-out
   deployments before measuring bank size and emulator latency. Begin with a
   small pilot; no large training job is currently running.
4. **Deployment search.** Optimize legal setups offline against several frozen
   opponents; retain diverse setups rather than a single opponent-specific
   arrangement. Evaluate learned setups separately from move-policy improvements.

Add a shared sparse-endgame and tactical corpus alongside full-game benchmarks:
late-game mechanisms activate too rarely to diagnose them through wins alone.
Full-game validation remains the promotion gate. Hard still has no established
advantage over current Normal; deeper search should earn its additional cost.
