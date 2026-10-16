The bounded pursuit test finds a concrete planning geometry, but **no sampled
native-selected move pursues one of the certified Scout goals**. A new strength
tournament is premature; no policy was implemented and no numeric bonus was
introduced.

In 356 fixed roots from 48 old DOS screening games, ordinary own soldiers have
74 native goals targeting disclosed enemy Scouts. Forty-four are at least three
route steps away and outside immediate own-Flag defence; 28 also have another
reachable target accepted by the existing gain gate with nonnegative native
utility. Fourteen actor goals, in 12 roots across seven games, pass the full
one-step nonprogress certificate. Ten are Red actor plans and four Blue. None
belongs to the actor making the selected quiet progress move. All 6,520 preceding
native choices match the frozen Fortress-template launcher.

The certificate quantifies a precise local obstacle: for every legal shortest
quiet pursuit step, the disclosed Scout has a legal long ray escape that restores
at least the original route separation, avoids next-turn capture by every own
mobile actor, and gains no immediate attack on our Flag. Occupancy and public
shuttle bans are respected. The other pieces remain stationary during this
one-step argument. This does not prove infinite evasion, that chasing is useless,
or that ignoring the Scout improves play. Moving toward it could restrict future
space even without immediate distance progress. A policy would require a full
counterfactual routing test before claiming global move activation.

The structural checker tests at most four first pursuit steps and 36 Scout ray
endpoints per step. The historical gate required only 31 endpoint examinations
in total. Its small incidence cost does not establish CX16 fit or timing; it is
Python mechanism research. Five fixtures pass for open escape, friendly
interceptor veto, blockers, both players' shuttle bans, hidden-nibble invariance
and color rotation. No current tournament or final-validation history was used.

[Fomin et al., *Pursuing a fast robber on a graph* (2010)](https://fedorvf.github.io/articles/2010/2010c.pdf)
studies how speed and graph structure affect capture guarantees. It motivates
distinguishing geometric closeness from forced pursuit progress. Their robber
can traverse bounded general paths, whereas our Scout uses straight rays;
their global results do not prove this game's local certificate or performance.
This hypothesis differs from prior fork/net work: it tests refusal of a slow
pursuit objective, rather than proving a material capture tactic.

Preserve the prospective protocol, incidence data and fixtures. Do not relax
distance, safety, alternative-goal or selected-action conditions to manufacture a
benchmark from this fixed sample. Further investigation could predeclare a full
goal-refusal counterfactual or examine independently sampled longer pursuit
histories; neither has been run here.

Evidence: `SCOUT-PURSUIT-PROTOCOL.json`, `scout_pursuit_preflight.py`,
`scout-pursuit-result.json`, `scout-pursuit.log`, `test_scout_pursuit.py`,
`scout-pursuit-tests.log`. Audit wall time: 60.3 host seconds.
