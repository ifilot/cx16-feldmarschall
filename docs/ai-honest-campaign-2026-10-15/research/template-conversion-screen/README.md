# Early Flag inference leaves a defensive problem

This descriptive audit uses all 400 completed native-template screening attempts
from cycle21. It does not inspect or tune the fresh validation cohorts, replace
any saved move, or establish how a new policy would score. The saved match's SHA
is checked before and after each analysis. Public predictions and tactical
checks receive own ranks, public disclosures and movement history only. Full
opponent setups are used separately to score prediction correctness.

At the first own decision with at least90% predicted probability on one
undisclosed Flag square, 332 games qualified; 324 predictions were correct and
eight were wrong. The correct group still ended in100 wins,148 losses,67 draws
and nine unscored engine errors. Its median first-confidence ply was4 in every
outcome group. These are selected descriptive groups, not causal comparisons.

Only one of those324 correct-confidence positions lacked a surviving own Miner;
the same position was the sole one with no optimistic Miner route to the
predicted Flag. The route calculation ignores every mobile blocker and enemy
guard, so a finite path proves neither a safe assault nor a win. Median lower
bounds were9 steps for wins/draws and10 for losses. Initial Miner exhaustion is
therefore not the common explanation in this cohort; later losses and blocked
or unsafe execution remain possible.

Of the203 scored losses,197 ended with own Flag capture and six with no legal
moves. Of the197 Flag captures,191 final attackers were Miners.195 attackers
were already publicly revealed before the final own move. All197 final
defensive positions had a confirmed public Flag threat. The checker found no
case where the selected move lost to a confirmed Flag capture in every
overapproximated combat branch while another legal move removed every confirmed
Flag capture in all branches.187 chosen moves were losing in every such branch;
the remaining ten included uncertain combat branches. This does not establish
that earlier positions were lost or that hidden long Scout threats were absent.

The branch checker respects the enemy two-squares restriction, includes moved
unknown neighbors as certainly mobile, and branches over all12 ranks for an
unmoved concealed target or all10 mobile ranks for a moved target. It deliberately
does not consult the true concealed rank or narrow support with remaining counts.
An immediate own Flag capture wins before any hypothetical enemy reply. Its
certificate concerns **confirmed** Flag attacks; it does not certify survival
against every possible concealed Scout.

The existing public two-turn interceptor was then checked on the last four own
decisions of these197 losses:788 roots. With equal baseline scores to isolate
the structural repair set, it would demote the actual selected quiet move at11
roots in ten games. Ten were one own turn before the final defensive move, one
was two own turns earlier. Captures retain existing control. This is an
opportunity count, not ten saved games: other enemy moves, hidden guards and
later play may defeat a local repair. No separate native integration is justified
yet; the same mechanism already has a frozen Teacher tournament in cycle10.

The evidence supports testing deployment and inference together, as frozen in
cycle27, and studying earlier defensive positioning. It gives little reason to
add a final-turn emergency filter: in this cohort the final public opportunities
were already exhausted. No policy, probability model or formation was changed.

Three conversion-boundary tests and five tactical checker tests passed. Their
logs and all per-game records accompany this note. Reproduction tools are
`analyze_template_conversion.py`, `analyze_public_flag_survival.py` and
`analyze_template_interception.py` in `tools/`; analysis output paths must be
fresh, preserving original screening evidence.
