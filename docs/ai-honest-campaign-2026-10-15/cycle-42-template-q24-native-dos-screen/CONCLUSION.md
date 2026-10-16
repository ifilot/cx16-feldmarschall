# Native Q24 template screen

The native Q24 source-template policy retained a large advantage over the plain
validated-deployment control in this fresh, fixed Classic DOS screen. All 3,000
attempts were saved and replayed. There were 148 errors, left officially unscored;
their sensitivity bounds are reported below. A separate metadata-only actor audit
attributes all 148 failures to the DOS side (146 interrupt faults and two illegal
returns), with no recorded native-policy failure. It does not distinguish original
code, adapter or emulation as the cause of the illegal returns. See
[actor audit](../research/terminal-error-actors-v1/README.md). This attribution does
not recover missing outcomes. This is exploratory screening, not
fresh final validation or a production promotion.

| Policy | Wins / draws / losses | Errors | Official scored score |
| --- | --- | --- | --- |
| Plain validated deployment | 122 / 91 / 710 | 77 | 18.15% |
| Floating host template bridge | 279 / 202 / 483 | 36 | 39.42% |
| Native Q24 template policy | 278 / 203 / 484 | 35 | 39.33% |

All arms used 1,000 attempts, 500 matched paired rounds, original-DOS armies,
rotated policy-owned deployments and the frozen seed 2520001. The opponent was
`msdos-1990-v2-normal`. Scores count a draw as half a win. An absolute 50% score
is not a fair-strength null against the DOS information advantage.

| Contrast | Complete / planned pairs | Paired effect (percentage points) | 95% interval | Prespecified 98.3333% interval | Finite missing-score bounds |
| --- | --- | --- | --- | --- | --- |
| Q24 minus plain | 414 / 500 | +22.46 | [+18.48, +26.39] | [+17.63, +27.23] | [+13.50, +24.70] |
| Q24 minus floating bridge | 469 / 500 | -0.05 | [-0.32, +0.16] | [-0.43, +0.16] | [-3.65, +3.45] |
| Floating bridge minus plain | 414 / 500 | +22.52 | [+18.54, +26.45] | [+17.69, +27.29] | [+13.55, +24.85] |

The wider intervals address the three planned contrasts. Missing-score bounds
assign the unknown outcomes in every error game adversarially; they describe this
finite cohort and are not confidence intervals. Both template policies remain
above plain in those bounds. Q24 versus the floating bridge has only two nonzero
complete-pair differences, one in each direction, and 467 ties. Its narrow bootstrap
interval does not establish equivalence, noninferiority or identical decisions.
Error sensitivity also permits a materially wider difference between the bridges.

The Q24-versus-floating-bridge contrast changes only the frozen inference
implementation/numerics, not the source-template population or honest public
information contract. Both template arms introduce the source prior relative to
the plain control. Q24 is a distinct
registered numerical policy: native inference, count-constrained rounding and
signed gain truncation can differ from the floating host bridge. No actual enemy
setup, private seed or hidden rank enters either policy. This source-population
result does not establish performance against humans or other deployment families.

The saved matches pass Python/native all-state replay and retain Qt6 captures.
`audit.json` records archive, recipe, runtime, artifact and original-army checks;
`result.json` retains all counts, paired intervals and error sensitivities. Target
fit is separate evidence: the frozen research target uses a dedicated inference
bank and an experimental helper relocation recipe; measured worst-case work is
about 1.5 seconds at 8 MHz. A desktop tournament does not establish acceptable
interactive target cost, production readiness or permission to enable the macro.
Default production remains unchanged.
