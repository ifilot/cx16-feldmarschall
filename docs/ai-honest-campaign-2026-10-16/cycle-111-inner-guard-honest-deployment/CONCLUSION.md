# Retained inner guard: honest end-to-end development screen

The Sergeant deployment scored **80.58%** against Missions, versus **78.35%**
for the unchanged Fortress-template reference. The paired difference was
**+2.23 percentage points**, 95% interval **[−4.24, +8.93]**. This fixed exploratory
screen establishes neither an improvement nor equivalence. Both arms completed
224 attempts without engine errors. Paired scores improved 18 times, worsened
15 times and tied 79 times.

This comparison deliberately includes deployment. Both policies choose their
own army and rotate it with their side; they receive the same opponent armies
and move seeds. The candidate swaps its Miner and Sergeant at local origins
21 and 34, so the initial own armies differ intentionally. The independent
[swap audit](deployment-swap-audit.json) confirms exactly those two changed
squares in every game, their reflected equivalents when playing Blue, identical
rank inventory, and unchanged Flag, Bomb and Spy positions. A referee corpus
forcing the same own army would erase the treatment and answer another question.

| Opponent setup family | Reference score | Inner guard score | Difference |
|---|---:|---:|---:|
| Fortified | 60.94% | 76.56% | +15.63 points |
| Uniform | 84.38% | 87.50% | +3.13 points |
| Unguarded | 78.13% | 75.00% | −3.13 points |
| Forward | 93.75% | 90.63% | −3.13 points |
| Decoy | 90.63% | 96.88% | +6.25 points |
| Presets | 59.38% | 53.13% | −6.25 points |
| Broad mixed | 81.25% | 84.38% | +3.13 points |

Each family has only 16 paired records. These exploratory differences do not
establish reliable family-specific gains, and no favorable family was selected
for tuning or sample extension. The overall difference remains inconclusive.
The high absolute scores reflect an asymmetric setup population; **50% is not
the neutral comparison point** for these end-to-end arms. This is fresh-layout
screening from familiar generators, not held-out-generator generality.

The controlled native fixtures establish that a Sergeant can survive a defensive
recapture where a Miner trades. The tournament changes the two pieces' complete
starting assignments, so its score difference alone does not prove that this
specific recapture mechanism caused the outcomes. Offense and later routing
can change as well. Its deployment cost remains one fixed swap; the move policy
and public belief model are unchanged.

Six source-bound qualification tests passed again, reproducing the preserved
component artifact exactly without overwriting it. An isolated rebuild reproduced
all nine immutable runtime files. Full Python/native replay, repeated frozen
own-setup reproduction and Qt6 captures are retained. Trajectory diagnostics
explicitly exclude unequal initial own armies from identical-root comparisons.
No original-DOS setup audit applies to this honest opponent.

No validation partition was used. No source, rank assignment or sample size was
tuned from these results or the running DOS endpoint. Production remains
unchanged; cycle 110 is a separate DOS study and target bank fit remains untested.
