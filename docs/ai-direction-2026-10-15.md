# Classic AI direction — 15 October 2026

New work focuses on the base game. Existing variant behavior and evidence remain
available, but further variant evaluation and tuning are deferred. Every new
candidate needs an immutable name, source-backed recipe and a reviewable Classic
tournament. Repository guidance is also recorded in `AGENTS.md`.

The next policy experiment should test one strategic explanation of our current
weaknesses. It should describe observable behavior, not start with adjusting a
small score constant. Use the tournament desk to inspect representative games
before choosing an implementation, then test both the predecessor matchup and
different kinds of opponent on fresh seeds.

## Research and proposed experiments

The requested [1990 Stratego partial decompilation](https://github.com/ifilot/stratego-decompilation/)
is private but accessible through the local authenticated `gh` CLI. The public
and connected-app failures did not establish that local access was unavailable.
An initial review at commit `306e3cb757137f3c28d1224ee3d2c4570f412509`
is recorded in [the source study](stratego-1990-source-study.md). It covers the
reconstructed selector, approach helper and knowledge findings, together with
their documented verification limits. The original/DOS comparison suites have
not been rerun here.

The strongest immediate architectural lead is separating tactical priorities
from positional scoring. This is a proposed new experiment, not a recovered
policy already ported to Feldmarschall or an established strength improvement.

The following are proposals informed by accessible primary sources, rather than
implemented or validated improvements:

| Strategic question | Proposed experiment | What would make it useful? |
| --- | --- | --- |
| Does the army need a clearer offensive plan? | Choose an attack lane and assemble the pieces needed to advance through it. Reconsider after meaningful public evidence or sustained failure. | More coordinated entry into the rear, with fewer unsupported advances and without losing the mission baseline advantage. |
| Does the AI gather information it can actually exploit? | Tie scouting to a pending attack or defense decision: identify which uncertain blocker matters, then use an affordable piece to test it. | Discoveries change a subsequent useful decision; expendable probes do not simply increase material losses. |
| Is it too easy to misdirect? | Evaluate a small mixture of plausible strategic explanations for a fortified sector instead of treating the first Bomb structure as the only objective. | Better play against decoys while retaining performance against genuinely protected flags. |

The [Demon of Ignorance author's design description](https://github.com/braathwaate/stratego#about-the-ai-artificial-intelligence)
discusses directed attacks through one of three lanes, information acquisition
and using approach/retreat histories cautiously because opponents can bluff.
My application of those ideas here is the lane and purposeful-information
experiments above; it is not evidence that our corresponding implementation
would improve strength.

[DeepNash](https://arxiv.org/abs/2206.15378) demonstrates model-free learning via
self-play toward an approximate Nash equilibrium. Its useful high-level lesson
for this project is to evaluate robustness across opponents, rather than assume
beating one predecessor means universal improvement. Applying that lesson through
small policy mixtures and diverse opponents is our proposal, not a claim to have
implemented DeepNash or reproduced its results.

The existing desktop teacher is a useful reference because it already tests
choices under several plausible hidden armies. Future training should preserve
the strategic context of the decision, including cooperation commitments, rather
than reward a different isolated move merely because the teacher selected it.
The guarded student's Scout-support regression is the local evidence for this
concern; its predecessor advantage but unchanged broader-league score is the
reason to retain both kinds of tournament.

No new playing policy or strength claim is introduced by the tournament tools
or source study. The next step is to examine real Classic games for conflicts
between tactical necessity and positional rewards, choose a strategic hypothesis,
give its candidate a new name, and evaluate it against preserved opponents.
