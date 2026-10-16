# Release the isolated Fortress reserve

One fixed deployment swap exchanges origin28 Bomb with origin38 Lieutenant.
The strategic hypothesis is that restoring access to one of the army's33 mobile
pieces improves conversion enough to justify removing one outer-lane Bomb.
No rank-value bonus, new movement policy, extra turn search or enemy input is
introduced. The source-template prior, if selected as a comparator context,
remains a separate unchanged factor; this candidate does not include the new
inner-Sergeant placement.

This exact single-swap shape was already listed as `MobilityOnlyFortress` in the
previous campaign's geometry proposal. It was not the package played in C22:
that study tested three swaps and a second Flag Bomb cut, alongside freeing the
reserve. Its rejection does not isolate the one-swap reserve hypothesis. This
preflight extends that preserved proposal to native executable qualification;
it does not claim a newly discovered formation or improved playing strength.

The candidate has permanent front access for all33 mobile pieces, versus32 in
Fortress. The Bombs at20/31, Flag30, Spy27 and inner guard21 remain in place. The
same one-Bomb minimum path into the Flag remains, with both adjacent inner Bombs
unchanged. Those static properties do not establish equal dynamic defence: the
right-hand lane is now open and could allow an opponent to approach defenders
more easily. This is the material strategic tradeoff for a subsequent fixed
screen, rather than a guaranteed improvement.

The Lieutenant has **no initial legal move in either formation**. A full-own-army
native component demonstrates the release mechanism after two specific legal
corridor vacancies: the front origin8 Major moves forward, then origin18 Sergeant
moves into its vacated square. The candidate Lieutenant at28 can now advance
into18; the baseline Lieutenant38 remains permanently boxed by Bombs28/37/39 and
the board edge. This holds for both colors and horizontal reflections. These
are own-movement components, not complete two-sided reachable game histories or
claims that the move selector will choose this activation schedule.

A separate synthetic late residue retains all own Bombs/Flag and only this
Lieutenant as a mobile survivor, against a disclosed enemy Scout and a concealed
Flag. Native legal generation reports zero baseline moves and three candidate
moves; the native chooser selects the released Lieutenant. This is a legal
mobility/selection fixture, not a win-rate estimate. Other teammates' removal is
explicitly synthetic and does not estimate the frequency of the situation.

Six tests pass, including exact default-off native binary identity, Classic
Normal-only activation, unchanged Easy/Hard/optional-rule setups and RNG state,
macro requirements/separation, inventory, both colors/reflections, native legal
movement and a shared-library own-information boundary check. Deployment writes
only own40 squares and gives identical output under mutated enemy-board bytes.

Implementation: `tools/new_campaign_open_reserve_deploy.c`, selected by replacing
`src/core/ai_deploy.c` in a new immutable policy's source list and adding
`AI_FORTRESS_OPEN_RESERVE` with `AI_DEPLOY_FORTRESS_ONLY`. Compile-time guards reject
combining this factor with `AI_DEPLOY_DOUBLE_SHELL` or `AI_FORTRESS_INNER_GUARD`.
The swap runs only for Classic Normal after the unchanged Fortress RNG ticket;
no random draw, array or per-turn work is added. Native qualification does not
establish CX16 bank fit, timing or production readiness.

Evidence: `component.json`, `tests.log`, `tools/test_new_campaign_open_reserve.py`.
No new policy is registered and no strength match is run by this preflight.
