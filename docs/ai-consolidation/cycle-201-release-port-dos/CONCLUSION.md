# Native release port: DOS validation

The frozen candidate passes the prespecified complete-case release gate. In
1,024 attempts per arm, the reference scored 310 wins, 199 draws and 494 losses
(40.83%), with 21 errors; the native candidate scored 310 wins, 198 draws and
496 losses (40.74%), with 20 errors. Errors remain unscored, not converted into
draws or losses. This is a port qualification, not a strength improvement.

Of the 512 paired units, 491 have all four games complete. Their candidate-minus-
reference score difference is -0.0509 percentage points, with a paired 95%
interval [-0.1527, 0.0000] points. Its lower endpoint exceeds the frozen -2-point
margin. There was one negative complete pair and 490 tied pairs. This does not
establish universal policy or decision equivalence.

Engine errors leave an additional limitation: independently assigning each
unknown error outcome any score in [0,1] yields finite-cohort effect bounds
[-2.0996, +1.9043] percentage points. These are not confidence intervals and
slightly cross the two-point margin. The planned statistical gate uses complete
cases and reports error sensitivity separately; full-cohort noninferiority under
every possible error completion has not been established.

Both arms retain the original DOS setup generator, own-policy deployments,
rotated colors, public observations and independent private deployment seeds.
The cohort is consumed. No tuning or sample extension follows this result.
Saved attempts, error prefixes, all-state referee replays and Qt6 review captures
are preserved. Target integration and production packaging remain separate
release obligations.
