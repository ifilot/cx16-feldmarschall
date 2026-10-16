# Reconsider pursuit when the public model changes regime

The native planner gives its previous square goal an eight-point persistence
bonus. That goal can have been selected while one or more source-template
components were plausible. Later public movement or rank disclosures can reject
every such template, leaving only the uniform legal-army background. The new
strategic hypothesis is to reconsider the old pursuits at this discrete model
change, while retaining normal persistence on every subsequent turn.

The broader planning motivation is updating retained planning information when
new observations change the problem. [Koenig and Likhachev, D* Lite, AAAI 2002](https://ocs.aaai.org/Library/AAAI/2002/aaai02-072.php)
studies efficient replanning with changed navigation information. Our proposal
is a limited goal-cache intervention, not D* Lite, and the paper supplies no
Stratego or DOS performance prediction. The specific regime boundary comes from
the existing public discrete-mixture model.

`RegimeResetBot` uses the unchanged Fortress Flag/Bomb belief adapter. After each
public `moved` or `battle` event it checks exact template compatibility against
tracked public original ranks and movement. On the first transition from at
least one compatible template to none, it queues a single reset. Before the next
ordinary native decision, `goal-regime-reset` clears only the own army's 100-byte
persistent goals array to NOWHERE. It does not reset missions, threat values,
quiet-turn counters, the opposite army's goals or RNG. Every turn still makes
exactly one native `go`. No thresholds, extra search or likelihood fitting occur.
New-game reset rearms the mechanism; repeated zero template support does not.

The strict source-compatibility calculation avoids treating a rounded tiny
posterior as a regime change. Only own setup and public events are consumed;
hidden rank nibbles and the enemy setup are unavailable. The standalone native
API accepts Classic Normal only and its protocol command accepts no arguments.

Dedicated files preserve shared core and previous policies:

- `tools/new_campaign_regime_ai.c`: the goal-only API.
- `tools/new_campaign_regime_engine.c`: the additional protocol command.
- `tools/new_campaign_regime_bot.py`: event gate and unchanged parent decision.
- `tools/new_campaign_regime_sources.py`: reproducible source materializer.
- `tools/new_campaign_regime_test.py`: four qualification tests.

Use the unchanged reference recipe, replacing only its two C source entries and
selecting the dedicated adapter with `--belief-regime-reset`. Freeze a new
descriptive policy ID before tournaments. Qualification checks direct controlled
goal state and unchanged RNG/history, default-off parity in 100 public prefixes
per color, pre-elimination parity, one reset per game, one go per decision,
private-nibble invariance and public hard-elimination events for both colors.
The fixtures are old designated development history, not validation games.

The intended primary comparison is this single reset against the unchanged
Fortress-template reference on fresh matched original-DOS armies, followed by a
separate honest development endpoint. Potential harms include losing a useful
commitment after irrelevant model rejection, goal oscillation at the one reset,
or negligible decision coverage. A successful mechanical test establishes none
of these outcomes. No target bank fit or measured CX16 timing is claimed.
