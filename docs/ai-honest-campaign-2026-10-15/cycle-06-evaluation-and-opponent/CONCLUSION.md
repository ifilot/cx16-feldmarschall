# Cycle 6: useful model corrections, no demonstrated strength gain

Context scored 116 wins, 3 draws and 293 losses (28.5%) against DOS. The capable-route evaluator scored 128/7/281 (31.6%), the informed-opponent model 120/11/285 (30.2%), and the legal-parent correction anchor 113/9/292 (28.4%).

Matched complete-pair gains over Context are respectively +2.78 percentage points (95% interval [-1.64,+7.20]), +2.27 [-2.78,+7.32], and +0.13 [-3.52,+3.89]. No candidate establishes an improvement. The paired anchor effect differs from its raw-score difference because error-containing pairs remain excluded from the paired estimate; all errors and finite-cohort missing-score bounds are preserved separately.

These tested distinct mechanisms: route evaluation requires an actual surviving attacker; the simulated DOS opponent legitimately knows our own Flag/Spy while our root remains masked; continuation correction is centered on a legal fallback rather than an imaginary pass. Audits prove these mechanisms operate, but mechanism correctness does not imply stronger play.

All 1,680 attempts were replayed in Python and at every native state. Twenty-two errors remain unscored with legal prefixes. Four Qt6 reviews and exact rebuilds of all three new policies passed. Production selection is unchanged. Higher-priority fresh validation follows the setup-prior and cheap native contact-risk screens; these three candidates remain preserved experimental policies.
