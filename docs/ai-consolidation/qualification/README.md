# Native candidate target qualification

Candidate: `production-fortress-template-q24-cache-v1-normal`. These are target
integration checks, not new strength experiments or proof of general human-play
superiority. The production defaults have not yet changed.

Two clean builds produced byte-identical FELDMARS.PRG, PLAY.BIN, AI.BIN,
MISSION.BIN and BELIEF.BIN without modifying the installed cc65 library. Map,
symbol and command records contain temporary paths and are not claimed byte
identical. The checked link leaves MAIN 66, AI 78, MISSION 235, PLAY 154 and
BELIEF 974 bytes free. The explicit bank-25 helper closure is checked against
generated call sites and every remaining linked MAIN library member's imports.

The ordinary 80-turn demo fixture matched a separately qualified native observer
on both armies' full moves, RNG, history and Q12 inference values. Audio stayed
active, bank returns matched and at least 996 software-stack canary bytes
remained untouched. Maximum whole-turn cost was 11,594,108 cycles (1.45 seconds
at 8 MHz), below the prospectively fixed 20,000,000-cycle limit. Alternating
owners invalidate the single-owner cache, so this fixture had no cache hits.

A separately labelled mechanical fixture restored each owner's previous actual
cache between turns. It matched all 80 turns and exercised 35 cache hits; it
measures cache mechanics, not a natural gameplay hit rate. Its maximum whole
turn was 11,601,396 cycles. Both fixtures poison initial bank BSS before starting
the real game. Costs apply to these fixtures, not a universal latency bound.

The existing real UI flow and difficulty tests passed against the isolated
candidate runtime, including setup persistence after process restart, game
save/resume equality, rematch, every difficulty encoding and legacy saves.
Loading discards poisoned old token identities and rebuilds a fresh public
snapshot; opening ancestry is marked unavailable and poisoned inference-cache
valid/hit bytes are cleared. A real Hard turn still receives concealed ranks.

The initial banked attempt failed because the frozen public executable correctly
omits a diagnostic-only command. The private observer adds test diagnostics to
the exact frozen source and reproduces 160 decisions from the public executable;
it never replaces the registered executable. The initial lifecycle test expected
the older empty tracker. The Q24 build intentionally synchronizes a fresh public
snapshot on load, so the revised check verifies snapshot contents, forbidden
opening ancestry and cache invalidation explicitly. Initial failure logs remain
alongside passing logs and exact qualification tool sources.

Separate native checks cover all 65,535 nonzero seeds, both colors and all
levels, plus optional-rule/rejection-draw cases: 396,612 exact board/RNG
comparisons preserve previous Easy/Hard and optional behavior and verify Normal
Fortress against its historical implementation. Eleven inference/cache tests
also passed. Fresh DOS validation and final production packaging remain pending.
