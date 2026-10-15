# Initial study of the 1990 Stratego AI

Reviewed 15 October 2026 from the private
[`ifilot/stratego-decompilation`](https://github.com/ifilot/stratego-decompilation/)
repository at commit `306e3cb757137f3c28d1224ee3d2c4570f412509`.
Access succeeded with the local authenticated `gh` CLI. The checkout used for
reading was `/tmp/feldmarschall-stratego-research`.

This is a source/report review. It does not rerun the project's original-code
comparisons, reproduce a complete original-game turn or measure playing strength.
The cited reconstruction reports describe controlled subsystem verification;
their limits remain relevant to every conclusion below.

## What the recovered design does

**It chooses a tactical priority before comparing positional scores.**
The reconstructed `choose_best_scored_move` in
[`SELECT.C`](https://github.com/ifilot/stratego-decompilation/blob/306e3cb757137f3c28d1224ee3d2c4570f412509/reconstruction/ovl5/SELECT.C)
first finds the lowest first-stage priority. Only moves with that priority
compete in the second stage, where the highest score wins. Destination
classifications dispatch to distinct evaluators, covering favorable,
unfavorable and uncertain encounters, Bombs, Flags and empty squares.
An earlier matching rule can take precedence over later considerations.

The two stages evaluate the same candidates. They are not two plies of search.
The [AI overview](https://github.com/ifilot/stratego-decompilation/blob/306e3cb757137f3c28d1224ee3d2c4570f412509/analysis/ai_overview.md)
does not establish recursive minimax in the recovered selection path, and
explicitly distinguishes source-range coverage from complete behavior coverage.

**Piece targets persist, and route progress contributes to decisions.**
[`APPROACH.C`](https://github.com/ifilot/stratego-decompilation/blob/306e3cb757137f3c28d1224ee3d2c4570f412509/reconstruction/ovl5/APPROACH.C)
compares the route assessments before and after a move toward a piece's cached
target. The recovered updater also maintains targets after notifications.
The path helper is bounded and has difficulty-dependent behavior; it is not
an unrestricted shortest-path planner. This supports the relevance of persistent
objectives, which Feldmarschall already has, rather than proving that copying
this route calculation would improve it.

**Some apparent knowledge comes from privileged information.**
The concealment block in
[`INIT.C`](https://github.com/ifilot/stratego-decompilation/blob/306e3cb757137f3c28d1224ee3d2c4570f412509/reconstruction/ovl5/INIT.C)
exempts the human Flag and Spy. The later normalizer can copy selected true
physical ranks into unknown AI records under sequence, difficulty and position
conditions. The [knowledge study](https://github.com/ifilot/stratego-decompilation/blob/306e3cb757137f3c28d1224ee3d2c4570f412509/analysis/ai_hidden_rank_knowledge.md)
documents the source paths and distinguishes internal sequence thresholds from
unproven full-turn counts. These mechanisms must not be mistaken for successful
inference from public observations. Our candidate experiments retain masked
inputs and hidden-rank invariance checks.

## The most useful experiment for our AI

Test an explicit hierarchy of tactical priorities, with positional and learned
scores choosing among moves at the selected priority. The motivation is that
adding several small positional rewards should not accidentally outweigh a
more important obligation. The precise priorities need evidence from our own
games; they should not be copied mechanically from the reconstructed constants.

Start by reviewing Classic matches where the current AI abandons a support job,
misses a necessary defensive move or makes an attractive but strategically
unproductive capture. If those examples show a common conflict between score
terms, build one named priority-based candidate alongside Missions v1 and the
Guarded Student v1. Preserve the current policies unchanged.

Evaluate it against both its predecessor and different opponents, across the
existing layout families, with fresh validation seeds. Retain the existing
cooperation and fairness checks. A simpler explanation of decisions is useful,
but promotion still requires game results and X16 feasibility.

This study identifies an architectural experiment. It establishes neither that
the 1990 AI is stronger than ours nor that a priority hierarchy will improve ours.
