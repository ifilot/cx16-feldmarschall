# Exact bounded quotient for goal expectations

The [committed cost preflight](../template-mobile-objectives-cost-preflight-v1/README.md)
needs wide intermediates, but not a general 64-stage divider. A goal expectation
is a convex combination of combat gains in [-400, 2000], so its final integer
quotient has magnitude at most 2000. Eleven quotient bits suffice. This followup
preserves that preflight unchanged and supplies a real byte-limb reference for
the narrower division step. No runtime policy, source archive or model changed.

Call the final signed numerator `X` and positive final denominator `V=4096*D`,
using the earlier note's conditional-mobile denominator `D`. The earlier bounds
give `V<2^47`, `abs(X)<=2000*V<2^58`. Signed products must first be added or
subtracted exactly to produce the magnitude of `X`; sign restoration happens
AFTER division. Dividing positive and negative contributions separately would
change the result under cancellation.

Initialize an eight-byte temporary to `V<<10`, which is less than `2^57`, and
the remainder to `abs(X)`. For bit positions 10 through 0, compare the remainder
with that shifted denominator; if at least as large, subtract and set the bit.
Shift the denominator right once between steps. Because `2000<2048`, no higher
quotient bit can be set. The ordinary binary long-division invariant therefore
returns the exact floor of the nonnegative magnitude ratio. Restoring a negative
sign gives truncation toward zero, including a zero result for a small negative
fraction. There is no rounding of the conditional mobile mean first.

`test_division.py` performs its comparison, subtraction, initial ten-bit shift
and repeated right shifts on eight-element byte arrays. The division loop uses
no Python-wide dividend, remainder, multiplication or division. Its largest
initial-shift temporary is 1023, right-shift temporary 511 and signed-subtract
temporary lies within [-256,255], all representable with explicit 16-bit work
variables in a later cc65 implementation. `encode`/`decode` and `Fraction` are
test setup/oracles, not operations inside the divider. The caller must establish
the positive-denominator and magnitude bounds; this is not a general divider
for arbitrary eight-byte inputs.

The final native `g/4` in goal utility remains a SEPARATE signed truncation.
Keep the existing rejection threshold, persistence, distance and tie semantics.
This arithmetic improvement cannot independently justify changing any of them.

## Counts and verification

Exactly 11 compare stages and ten right shifts run per quotient. With eight-byte
arrays, the conservative bound is 88 comparison-byte steps, 88 subtraction-byte
steps and 80 right-shift-byte steps, plus seven byte steps to build `V<<10`.
Comparison stops at the first unequal high byte, and subtraction occurs only
when a quotient bit is set. These counts exclude signed numerator construction,
wide multiplications, row mapping, bank calls and all native planning.

The previous deliberately loose streamed bound falls from 33 actors × 40 origins
× 64 = 84,480 division stages to **14,520**. If the existing 480-entry cache is
repurposed for goal expectations, an evidence miss needs at most **5,280** stages
instead of 30,720; exact cache hits need none. Neither number is a cycle count,
an observed average nor a target latency/fit claim.

Three tests pass. They include 5,000 fixed-seed synthetic signed ratios against
an independent `Fraction` oracle, boundaries at zero, 1023/1024 and 1999/2000,
denominators close to `2^47`, sign cancellation and separate native quarter
truncation. `operations.json` records actual counters over the 5,000 cases:
55,000 stages, 124,642 comparison-byte steps, 217,752 subtraction-byte steps,
400,000 right-shift-byte steps and 35,000 initial-shift-byte steps. Per-case
observed maxima were 43 comparison and 80 subtraction-byte steps; these do not
replace the conservative bounds. Boundary cases are tested separately from
that operation-count cohort.

Reproduce:

```
python3 docs/ai-honest-campaign-2026-10-15/research/template-goal-bounded-division-v1/test_division.py
```

All inputs are invented arithmetic cases. No game trajectories or validation
data were read. A future target implementation still needs signed-magnitude
product/addition qualification, byte-for-byte numerical oracles, compiled bank
and software-stack checks, an actual link and measured complete-turn cycles.
This note establishes a smaller exact division algorithm; it establishes
neither a complete inference implementation nor stronger play.
