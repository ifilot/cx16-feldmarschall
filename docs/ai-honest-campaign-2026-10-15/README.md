# Eight-hour honest Classic AI campaign

The campaign runs from 2026-10-15 20:44:38 UTC until 2026-10-16 04:44:38 UTC.
The user requested three assisting agents, distinct cheap research hypotheses,
DOS tournaments, a cumulative overview, and a commit after every completed cycle.
Existing experiments were preserved in baseline commit `209d3ef`.

All candidates receive their own setup and public moves/battles only. The DOS
opponent retains its original information advantage. Concealed referee ranks may
be used for offline assessment, never for a candidate's decision. Classic rules,
paired side swaps and frozen source-backed policies apply. Each plan specifies
its deployment context: seven stress families or the original DOS generator,
and common referee armies or armies selected by the honest policy itself.
Scores from those different contexts must not be compared as one difficulty.
Production selection stays unchanged unless separate fresh validation supports
a promotion. Original DOS crashes are preserved and unscored.

See [the cumulative overview](OVERVIEW.md) for every completed cycle. Each cycle
directory contains its prespecified plan, registration time and immutable recipes.
Completed tournament cycles also preserve
portable `.fmtour` matches, independent full Python/native replays, Qt6 review
captures and a SHA-256 manifest. Exploratory confidence intervals are descriptive;
trying many hypotheses requires fresh validation before claiming a strength gain.

Original-DOS deployment cycles run the unchanged level-three setup instructions,
including their template/procedural mixture. A separate private setup seed never
reaches the honest player. The explicit `policy-owned-rotated-v1` setup mode
rotates both armies 180 degrees when colors swap, preserving the DOS-local army.
The existing move adapter independently reseeds its random stream; these are not
claims of bit-for-bit reproduction of an entire original UI game. Superseded
setup-mode registrations for cycles 19 and 21 are retained under `plan-revisions`;
both revisions preceded any saved matches and changed no policy identity.

## Initial hypotheses

1. **Sampling budget:** Does 32 rather than eight possible enemy armies improve
   decisions, and does it unlock the previously frozen learned belief model?
   This follows our earlier offline-versus-eight-world prediction discrepancy.
   Four matched arms identify both simple effects and the interaction.
2. **Latin-hypercube sampling:** Spread the same eight armies across random
   coordinates while preserving each army's proposal distribution, exact public
   counts/masks and behavioral importance weights. Inspired by
   [McKay, Beckman and Conover (1979)](https://www.stat.cmu.edu/technometrics/70-79/VOL-21-02/v2102239.pdf).
   Their variance results do not guarantee improvement for nonlinear game search.
3. **Army activation:** Prefer quiet moves that open teammates' routes toward
   central crossings. Uses friendly ranks and occupancy, with no inferred Flag
   target or disclosure bonus. Motivated by
   [mobility concepts studied in AlphaZero](https://pmc.ncbi.nlm.nih.gov/articles/PMC9704706/)
   and [transition potentials](https://ai.stanford.edu/~ang/papers/shaping-icml99.pdf).
   Our root-only capped heuristic has no policy-invariance guarantee.
4. **Paired uncertainty control:** Require a search override's advantage over
   the native move to exceed one jackknife standard error. Reuse shared-world
   differences without extra native rollouts. Inspired by
   [root best-arm identification](https://papers.nips.cc/paper/2017/file/a6d259bfbfa2062843ef543e21d7ec8e-Paper.pdf);
   this is a pragmatic uncertainty heuristic, not that paper's algorithm or a
   finite-sample guarantee.

Research and integration continue while frozen matches run. Mechanism tests
establish intended behavior and information boundaries; tournaments establish
whether that behavior helps play.
