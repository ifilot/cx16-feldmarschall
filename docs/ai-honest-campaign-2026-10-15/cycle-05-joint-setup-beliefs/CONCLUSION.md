# Cycle 5: setup beliefs show a promising screening signal

The frozen joint Flag/Bomb setup model scored 162 wins, 13 draws and 372 losses (30.8%) against DOS, compared with Context at 146/9/394 (27.4%). The matched side-swapped complete-pair estimate is +4.0 percentage points, with a 95% bootstrap interval [+0.2, +7.8]. This is exploratory evidence among multiple campaign comparisons; no policy is promoted.

The identical learned Flag-row prior with spatial coupling disabled scored 29.5%. Joint minus this control is only +0.7 points, interval [-3.6, +4.8]. The experiment therefore does not establish that Flag/Bomb correlations improve play. A simpler positional prior may explain the signal. Joint minus the earlier learned behavioral model is +2.7 points, interval [-1.4, +6.8].

Next: independently validate Context, row-prior and joint models on fresh seeds without changing the frozen models. Also test a separate mechanism connecting these beliefs to immediate capture values and native quiet-move objectives: stronger prediction need not improve the current continuation correction.

All 2,240 attempted Classic games were replayed in Python and at every state in the native worker; 45 original DOS errors remain unscored with their legal prefixes retained. Four Qt6 reviews were captured, both new frozen policies rebuilt exactly, and 11 mechanism/adapter tests passed. Source, frozen model and runtime integrity were additionally checked independently of the evolving shared adapter.
