# Conditional own-Flag geometry beliefs: development evidence

The tested idea is that observed enemy motion, conditioned on our legitimately
known Flag position, helps predict the ranks of concealed moving enemy pieces.
The extra inputs are shortest-path distance to our Flag, net progress toward it
from the enemy piece's public initial square, and the progress made by its most
recent actual public move. A lake-aware static board graph supplies distances.
The model adds bounded conditional likelihood factors to the frozen existing
public-history model; its original tables and temperature are unchanged.

This is honest conditional geometry inference. It does not read an enemy setup,
concealed enemy rank, future event, or referee board. Our own complete setup is
legitimate private knowledge. A strict public token tracker validates actual
move/battle events, retains disclosed ranks after capture, and records action-time
objective locations. Spy features were investigated and rejected: their selected
strength was zero. Only the three Flag features are active in the new assets.

## Historical data and selection

Only the earlier development corpus and its original whole-pair train/calibration
partition were used. No campaign validation or new campaign outcome enters fitting
or selection. Observer views were restricted to the side opposite the DOS engine;
the other half of the original corpus observes an honest teacher and is excluded.
The fit contains 1,498 views / 6,857 moved concealed labels. Calibration contains
660 views / 2,756 eligible labels; 63 of its 84 games contain eligible labels.
Training uses inverse game-view weights, categorical rank-conditional factors, and
alpha=10 pooled-frequency smoothing. Selected factor groups and strengths are
preserved, including rejected Spy, combined/motion alternatives and mirrored
controls. Strength selection uses historical fractional count-balanced marginal
predictions; these are approximate marginals.

The real Flag group selected strength .5 from [0,.125,.25,.5,1]. Its fractional
moved-rank log loss was 2.0074 versus 2.0282 for the frozen base. A separate fixed
sampling follow-up retained this choice and tested the actual eight-world
importance sampler:

| Historical calibration prediction | Base | Real Flag | Mirrored Flag |
| --- | ---: | ---: | ---: |
| Eight-world log loss | 2.9417 | 2.8719 | 2.8916 |
| Eight-world Brier | .9954 | .9817 | .9841 |
| Eight-world rank accuracy | 16.80% | 20.17% | 19.18% |
| 256-world log loss | 2.0664 | 2.0341 | 2.0469 |

The mirrored control uses separately fitted mirrored-file objective tables with
identical fit recipe, the same three Flag feature indices and the same real-selected
strength .5. Its strength is deliberately not selected independently. The real
minus baseline eight-world pair-cluster log-loss contrast was -.0770,
95% interval [-.1209,-.0340]. Real minus mirrored was -.0265,
[-.0776,+.0236]. Thus both geometry models help descriptively; these data do not
demonstrate that the real objective explains more than its mirrored control.
They do not establish a causal inverse-planning explanation or playing strength.

All intervals resample whole historical pair clusters within setup family, never
individual piece examples. Eligibility leaves 34 pair clusters, of which 29 have
two eligible games and five have only one. The generic bootstrap helper names its
cluster count `complete_pairs` in the preserved JSON; here that field means
**available eligible pair clusters**, not 34 fully eligible pairs. Means average
available eligible games within each cluster. Selection and these intervals reuse
historical calibration and are development evidence, not unbiased fresh validation.
Eight/256-world log loss uses a prespecified 95% sampled / 5% count-prior mixture
to give finite scores when finite samples omit the true rank.

## Reproducible assets and runtime API

`tools/freeze_inverse_objective_models.py` creates two immutable v1 assets from
preserved fits, never refitting: `ai/models/own-flag-motion-beliefs-v1.json` and
`ai/models/mirrored-own-flag-motion-beliefs-v1.json`. Each embeds the exact frozen
base document, complete original game/pair partition IDs, training recipes,
selection notes, source/data/report hashes and primary citations.

`ObjectiveSampler.load(path)` in `tools/campaign_inverse_objectives.py` exposes
`observe(words)`, `sample_worlds(cells,lost,histories,rng,army,samples)` and inherited
`marginals(...)`. Feed every actual protocol input, including generated own setup
after a bare setup request. Never feed speculative rollout inputs. Missing own
setup, opponent setup, stale origins, conflicting own ranks or inconsistent
captured inventory are rejected. A zero-strength sampler exactly reproduces base
worlds, weights and RNG use. The proposal and importance correction preserve
exact rank counts and public masks; eight worlds remain a finite approximation.
Dependencies are `calibrated_beliefs.py`, `campaign_joint_beliefs.py` (strict public
tracker only; uniform dummy style parameters, no joint model asset), and
`feldmarschall.py`. No native rollout budget increase is introduced.

The empirical original module is preserved as
`campaign_inverse_objectives.original.py`, matching the hashes in the research
reports. The current module adds the runtime facade and setup callback checking;
feature/factor equations are unchanged. All group/grid/control predictions and
runtime results remain in the adjacent JSON/gzip files.

Ten isolated feature/adapter checks pass, including actual frozen native observer
prefixes of 80 public events for both sides and both assets, enemy-nibble
invariance, exact counts/masks, reset/honesty rejection and zero-strength parity.
Teacher CLI integration and immutable policy registration belong to the parent
campaign workflow. Fresh broad Classic comparison should include base, real and
mirrored policies together, followed by honest-head qualification before promotion.

## Scientific motivation and its limits

[Baker, Saxe and Tenenbaum (2009), Action understanding as inverse planning](https://dspace.mit.edu/entities/publication/2e23673d-f720-4720-98bc-6db894ba27e1)
models goal-directed action through Bayesian inversion. Its setting motivates
conditioning observed action on goals; this lightweight categorical model does
not implement their planner or inherit an efficacy guarantee.
[Stankiewicz (2009), Opponent Modelling in Stratego](https://project.dke.maastrichtuniversity.nl/games/files/bsc/OMStratego.pdf)
provides Stratego-specific historical motivation for behavior-conditioned rank
beliefs. Our predictive evidence and subsequent fresh matches must establish the
value of these particular features.
