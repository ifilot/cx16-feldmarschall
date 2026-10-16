# Next steps for honest Classic AI

The next step is to build on the confirmed improvements and test specific missing
decisions. The evidence does not establish an honest-AI ceiling.

1. **Consolidate Fortress plus public formation inference as the desktop reference.**
   Fresh validation confirmed the source-informed Flag/Bomb prior in
   [C26](cycle-26-template-native-validation/CONCLUSION.md), then confirmed the
   unchanged Fortress deployment addition in
   [C41](cycle-41-fortress-template-validation/CONCLUSION.md). The latter scored
   **44.33% versus 39.54%**, with a paired gain of **4.98 percentage points**
   (95% interval **[3.25, 6.76]**). Score counts a draw as half a win; 44.33%
   is not a win rate. This is improvement against the specified original-DOS
   deployment population and adapter, rather than general Stratego strength.
   Public formation inference is honest: it conditions a population prior on
   observed movement and disclosed ranks, without receiving the actual enemy
   setup or private seed. Preserve the validated implementation as a reference
   while testing additions separately.

2. **Finish target engineering as a separate qualification task.**
   [C42](cycle-42-template-q24-native-dos-screen/CONCLUSION.md) supports the
   native Q24 implementation in exploratory DOS matches. Its small observed
   difference from the floating implementation does not prove equivalence.
   The [cache V2 qualification](research/template-target-cache-v2/README.md)
   demonstrates exact reuse on unchanged public evidence and native/target
   move, probability and RNG parity in its fixtures. Cache hits prepare in
   about 16–21 ms at 8 MHz; misses still take about 0.98–1.10 seconds, before
   other AI work. Validate complete-turn latency, reset/history/bank behavior
   and a reproducible deployable build. A successful desktop result or an
   experimental bank layout does not establish production readiness.

3. **Test full mobile-rank beliefs in long-range objectives.**
   The [persistent-history component pilot](research/template-mobile-objectives-pilot-v1/CONCLUSION.md)
   found concrete changes to target rejection, goal ordering and quiet routes
   when already-available public per-piece mobile beliefs replace the
   exchangeable mobile mean. It did not run a new policy: its 17 quiet argmax
   shifts concern only the distance-progress component. Preregister a goal-only
   implementation that preserves capture evaluation and tactical defenses, check
   full persistent-policy behavior, then test fresh matches. The pilot's fixed
   sample was Red only, so the next study must specify both colors in advance.

4. **Keep the tactical proofs as research tools until broader value is shown.**
   Completed [DOS forks](cycle-43-public-forks-dos-screen/CONCLUSION.md),
   [honest forks](cycle-44-public-forks-honest-generality/CONCLUSION.md) and
   [honest capture nets](cycle-48-capture-net-honest-generality/CONCLUSION.md)
   established no score gain. Sparse score-changing pairs do not prove
   equivalence or that the underlying decisions are identical. A short material
   certificate needs a clearer route to game conversion before more depth or
   proof cost is justified.

5. **Establish generality against honest opponents and unfamiliar formations.**
   [C32](cycle-32-compact-backrow-honest-generality/CONCLUSION.md) found a clear
   generality loss for the compact source prior, despite its fresh DOS gain in
   [C46](cycle-46-compact-backrow-independent-validation/CONCLUSION.md). Richer
   backgrounds also lost strength in [C30](cycle-30-procedural-background-honest-generality/CONCLUSION.md).
   Treat original-DOS strength and honest-opponent strength as separate questions.
   Compare the consolidated reference and promising additions across prespecified
   opponents and deployment families, including formations outside the source
   templates. A DOS-specific population prior can be useful without transferring
   uniformly. Report family variation and uncertainty rather than averaging away
   regressions.

For every strength experiment, freeze the hypothesis, comparator, population,
contrasts, stopping rule and error handling before play. Register an immutable
descriptive policy ID with its source, model, recipe and difficulty. Keep screening
and final validation separate, use fresh validation seeds, and preserve rejected
policies and failures. Use the Classic runner and Qt6 companion for reviewable
games. Confidence intervals describe sampling uncertainty; finite missing-score
bounds address unscored failures and must remain separately visible.

The [completed cache bridge](cycle-45-template-exact-cache-bridge/CONCLUSION.md)
matched all 400 game trajectories exactly, including error prefixes. It supports
implementation preservation on that cohort; target timing and production remain
separate gates. The goal-only proposal now also has a
[storage/arithmetic preflight](research/template-mobile-objectives-cost-preflight-v1/README.md)
and an [eleven-stage exact divider](research/template-goal-bounded-division-v1/README.md).
Neither is an implemented goal policy or a playing-strength result.
