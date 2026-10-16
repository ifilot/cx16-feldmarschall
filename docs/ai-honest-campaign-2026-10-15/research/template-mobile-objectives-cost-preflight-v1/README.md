# Goal-only mobile beliefs: source and arithmetic cost preflight

A separate 960-byte goal table is unnecessary. The existing 200-byte transfer
union can stream one actor's goal expectations into `plan()`, then receive the
unchanged capture expectations before `score()`. This is a concrete isolation
plan, not implemented policy, a target-fit result or a strength claim.

## Frozen basis and call boundaries

`source-audit.json` binds C45's registered
`student-template-q24-native-v2-normal` archive
`73302ca8323ba0dbdedea55d9e8c565d50129c4791b39a54f25159954e6565c1`.
Its four relevant source files equal the inspected workspace files and the
source hashes in the frozen cache-V2 target report. No source was changed.
The extracted map excerpt is from that report's evidence archive.

The actual layout has only 78 bytes free in AI, 66 in MAIN, 245 in mission,
154 in play and 974 in inference/BELIEF (bank25). The existing bank25
`cache[12][40]` occupies 960 bytes. `ai_template_transfer` is a 200-byte
MAIN-visible union of 80 history bytes and 100 signed 16-bit row entries;
bank25 retains its own 80-byte history copy. Adding another 960-byte table
would consume virtually all nominal bank25 headroom before its code or scratch.

Current sequence in `ai.c` is actor copy, source-danger calculation, `plan()`,
then all that actor's `score()` calls. Existing `expected_at()` reads the row
only for an UNMOVED hidden token; MOVED hidden tokens deliberately use native
exchangeable counts. A goal-only implementation therefore needs a distinct
goal expectation accessor that also consumes moved-token inference. Merely
replacing existing row data would leave moved goal ranks exchangeable and could
silently change captures. Disclosed goals retain exact native `gain()`.

Preferred first mechanical implementation:

1. Keep the existing capture cache, Q12 Flag/Bomb arrays, history, counts and
   evidence-key lifecycle unchanged. Fill the existing transfer row with
   conditional-mobile goal gains for the current actor through a bank25 gateway.
2. Run `plan()` with ONLY its concealed-target expectation changed. Preserve
   utility/rejection arithmetic, prior goals, BFS reachability and tie ordering.
3. Restore the capture row with the existing `ai_template_actor(rank)` gateway
   before any `score()` call. Keep capture `expected_at()` and all danger,
   defence, mission and RNG code unchanged. New bank gateways must restore their
   calling bank; no callbacks should read a row while another phase owns it.

This adds no second row in MAIN and no second 960-byte bank25 table. Its extra
work repeats goal-row computation for actors of the same rank. A possible
80-byte bank25 last-rank row plus two validity/rank bytes reduces consecutive
same-rank work, but is not necessary for correctness and would need measured
hit rates. The transfer union cannot simultaneously hold history and a row:
all history export/collect work must finish before either actor-row phase.

A later, potentially faster alternative repurposes the EXISTING 960-byte cache
as goal gains for all ranks, rebuilding it only on an evidence-key miss. Capture
rows can be regenerated from the frozen Q12/count formula during actor copy,
using the existing 32-bit arithmetic and at most ten terms for that rank's
exchangeable mobile sum. This retains cache-hit benefits for the expensive goal
arithmetic without adding a table, at the cost of recalculating capture rows.
Its capture outputs must match every original cache entry exactly. It is a
separate implementation tradeoff, not an already qualified optimization.

## Bounded exact arithmetic for a declared Q24 bridge

This formulation preserves the current native Q24 posterior definition. It is
not bit-identical to the floating Python pilot; any executable numerical policy
requires a new immutable ID and a declared oracle.

Let `ONE=2^24`, `Q=4096`, `B` be current background mass and
`T=floor((ONE-B)/k)` the existing per-compatible-template mass (`T=0` if `k=0`).
At one hidden origin, let `t` be the number of compatible templates assigning
a mobile rank, and `A` the sum of that actor's combat gains over those templates.
Let `H` be remaining hidden mobiles and `S=sum_r remaining[r]*gain(actor,r)`.
For an unmoved origin use `U=unknown_unmoved`, `E=U-hidden_Bombs-hidden_Flags`;
for a moved origin use `U=E=1`. This represents background mobile eligibility
`E/U`; the background conditional mobile ranks remain exchangeable.

The conditional mobile mean is exactly `N/D`, where:

```
N = T*A*H*U + B*E*S
D = T*t*H*U + B*E*H
```

Using the EXISTING rounded Q12 Flag and Bomb masses `f,b`, the goal expectation is:

```
immobile = 2000*f + gain(actor,Bomb)*b
g = trunc_zero((immobile*D + (Q-f-b)*N) / (Q*D))
```

Do not truncate `N/D` first: that independently changes goal values, particularly
near zero and rejection thresholds. Preserve the subsequent native signed `g/4`
and `-worth[actor]/2` truncation separately. When `D=0`, mobile conditioning is
undefined. Use the existing exchangeable fallback (or the frozen immobile result
if no mobile mass), without manufacturing a rank. Known origins bypass this
conditional formula. Captured public origins still condition compatibility and
counts, but are never emitted as live targets.

Signed 32-bit arithmetic is insufficient: even `ONE*2000` exceeds INT32_MAX.
For mobile actors, gains against mobile ranks lie in [-400,400], `H<=33`,
`U<=40`, and `T*t+B<=ONE`. Consequently `D<=ONE*33*40<2^35`,
`Q*D<2^47`, and the final absolute numerator is at most
`Q*2000*D<2^58`. Eight-byte unsigned limbs plus an explicit sign are sufficient;
avoid cc65's unsupported/implicit wide arithmetic. Signed-magnitude products,
addition/subtraction and binary shift/subtract division preserve truncation
toward zero without any Q24-times-worth overflow. Byte multiplication needs
at most `255*255+255+255=65535` in a 16-bit temporary. Signed cancellation must
precede division. A cancellation-independent conservative bound also fits 64 bits.

One implementation can reuse about 24–40 bytes of bank25 arithmetic scratch
(product/denominator/remainder plus sign and loop temporaries), rather than
allocating 480 values. This is a scratch design estimate, not measured cc65
allocation or software-stack usage. Public validity and hidden-nibble masking
must retain their existing fallbacks. Cache keys already include disclosed and
moved origin state, dead origins, owner and dynamic-worth Marshal/Bomb losses;
changing model/numerical format requires explicit invalidation/versioning.

## Static work bound, tests and unresolved costs

A streamed row examines at most 40 origins and eight templates per origin;
its background mobile sum takes ten rank terms. Up to 40 wide divisions of at
most 64 bit iterations add at most 2,560 divide iterations per actor row.
With 33 movable actors, the deliberately loose per-turn bound is 84,480 such
iterations, plus multiplications, copies and native planning. Reusing the old
cache as goal storage instead moves up to 480 divisions / 30,720 iterations to
an evidence miss and avoids them on exact hits. These are operation counts,
not cycles, average latency or proof that the code fits the 974 free bytes.
Wide arithmetic code may be the binding cost even when scratch is small.

Three independent tests pass, including 3,000 deterministic SYNTHETIC rational
cases against `fractions.Fraction`, signed cancellation, declared bounds and
byte-limb multiplication/binary division. The tests are arithmetic feasibility,
not a target implementation: division's reference remainder uses Python's wide
integer, and no cc65 assembly, stack, real bank gateway or timing is measured.
No game states, screening trajectories or validation data were queried.

Before implementation: choose and preregister the Q24 numerical oracle,
row ownership/fallback API and streaming-versus-cache tradeoff. Before matches:
prove default-off byte parity, exact baseline-plan/capture-score parity when
the conditional model reduces to exchangeability, moved/unmoved/disclosed and
both-color mapping, full persistent native goals, hidden-nibble invariance,
reset/cache/restore validity and one-search/RNG behavior. Actual target linking,
bank/stack checks and measured miss/hit/whole-turn cycles are separate gates.
The committed component pilot motivates this channel; it does not establish
that these altered long-range goals improve play.
