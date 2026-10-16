# Public missed-capture evidence

Hypothesis: choosing a quiet move elsewhere while declining an unprotected
capture of a disclosed valuable soldier is soft evidence about the rank of the
piece declining the capture. Incorporating that evidence into the contact's
Flag/Bomb probability can improve honest combat choices. This changes the
information model, rather than adding a generic information reward.

Scientific motivation: [Sokota et al., Ataraxos, Appendix C.1](https://arxiv.org/html/2511.07312v1#A3.SS1)
explicitly encodes whether pieces had an opportunity to attack and declined it,
alongside threat and evasion histories. Its learned system combines these public
features with many other inputs. The present hand-written likelihood is our
bounded hypothesis; the paper does not validate its direction, magnitude or
playing strength. The full learned agent is outside this cheap experiment.

## Prespecified observation

Only actual public quiet enemy moves qualify. Another hidden enemy token must
be adjacent to one of our already publicly disclosed ranks Marshal through
Lieutenant. Our initial knowledge of our own ranks is insufficient. Exclude
contacts with any own mobile recapture ray and those prohibited by the current
two-square shuttle restriction. Record one contact, selecting the strongest
victim and then lowest enemy origin deterministically. Keep that single event
until the contact is disclosed; repeated turns do not multiply evidence.

Rank hypotheses that would have won the foregone capture receive likelihood
one-half; other ranks receive one. This bounded factor is fixed without fitting.
The opponent might prefer another move, so no rank is logically eliminated.
No private opponent army, seed, true rank or future event is accepted.

## Preserved preflight rejection

`tools/new_campaign_information.py` applied the factor to source-template
components while leaving the unmodeled uniform background untouched. Its
[fixed public screening audit](activation.json) triggered in 188 of 200 side
histories but changed no posterior by more than 1e-12. Public combat facts had
already resolved or eliminated the discrete source components. This version
is retained as an inert preflight rejection, without a strength claim or
registered saved tournament. The audit used the first 100 complete C39 screening
games and both colors; no validation trajectories were consulted.

## Exact background refinement

`tools/new_campaign_information_background.py` conditions the uniform background
as well. Enumerate the twelve possible contact ranks under public rank counts
and moved/unmoved masks, multiply by the one observation likelihood, then
renormalize. For each rank, remove that rank and its moved/unmoved slot before
computing every other hidden piece's conditional marginal. Mixing these rows
retains exact inventory totals. Source-template components receive the same
rank-dependent likelihood. Unlike the rejected version, a background-only
position can change the contact's Flag/Bomb probability.

Existing native capture, safety, goals, deployment and RNG logic remain the
comparator. The runtime imports the usual public NativeTemplateBot adapter and
requires `--missed-background-captures`. The parent registers an immutable policy
before playing saved games. The associated [activation audit](background-activation.json)
is a component diagnostic, not a tournament or evidence of higher score.

In that fixed audit, 103 of 200 side histories had changed contact Flag/Bomb
marginals. Testing the first such root per history changed 89 of 103 complete
Q12 packets; every tested clue was unmoved. The separate
[native public-prefix fixture](native-fixture.json) compared 40 eligible
decisions with the frozen Fortress observer, covering both colors: four selected
moves changed. This observer lacks scalar candidate traces, so scalar scores
were not observed and cannot explain the changes. Prefixes were forced public
histories without earlier native `go` calls, so these are component results,
not persistent-policy behavior or a score improvement.

Tests: `python3 tools/test_new_campaign_information_background.py` checks an
exhaustive tiny-world oracle, complete Classic inventory preservation, probability
normalization, moved-piece masks, Q12 rounding, both colors and disclosure/reset
lifetime. The inherited tests reject use of undisclosed own ranks, adjacent or
Scout-ray protection, the moving contact itself, shuttle-banned opportunities,
invalid input side effects and repeated evidence compounding.

Storage is one event and public disclosure identities in addition to the existing
tracker. One observation adds at most twelve conditional rank cases per public
decision. Host audit timing is recorded in its JSON. No CX16 fit or whole-turn
latency qualification is claimed. A missed capture could reflect strategic
urgency or intentional deception; an unchanged one-half factor can therefore
be wrong. Only fresh paired games can test whether it helps.
