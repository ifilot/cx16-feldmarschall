# Metadata-only terminal error attribution

All 272 error records in C41 and C42 are attributable to the DOS-side adapter:
260 report an explicit original-code interrupt fault and 12 report an illegal
move returned on the DOS participant's turn. This diagnoses the failing side,
not the underlying cause of those illegal returns. It does not show whether
original code, adapter state or emulation produced the bad move.

| Cohort / arm | Original interrupt fault | DOS illegal return | Native-side error |
| --- | ---: | ---: | ---: |
| C41 book | 69 | 4 | 0 |
| C41 Fortress + book | 45 | 6 | 0 |
| C42 plain | 77 | 0 | 0 |
| C42 floating book | 35 | 1 | 0 |
| C42 native Q24 book | 34 | 1 | 0 |

The initial reason-only review correctly left the generic illegal-move reason
unattributed. The parent then authorized this narrower operational diagnosis,
using stored participants and completed-ply counts, without opening validation
trajectories. Each of the five saved tournaments contains its actual worker
executable, source archive and build receipt. `audit.py` verifies their SHA-256
bindings, extracts `desktop/worker.cpp`, checks its receipt hash and equality to
the reviewed source (SHA-256
`4845a3caa6ba0e5e77b93a23d41de88386e5d640c13c52ee4172b0c9ab1851f8`).

The frozen `play()` starts with Red (`side=0`). It asks `engines[side]` for a move,
throws the specific illegal-move error before appending anything, appends exactly
one trace entry per completed legal move, and then alternates side. The stored
`plies` equals `trace.size()`. Consequently, an illegal return with even plies
belongs to Red and with odd plies belongs to Blue. This deduction is specific to
that error: exceptions during event notification need not have the same parity.
The interruption errors identify the DOS original-call path directly.

The SQL game queries select only error reasons/counts and `red, blue, plies,
reason` for illegal errors. They never select moves, seeds, deployments or
positions. No validation game was replayed or used to develop an algorithm. No
policy, tournament result or scoring rule changed. Every error remains unscored
and included in the existing finite error-sensitivity bounds.

Reproduce from repository root:

```
python3 docs/ai-honest-campaign-2026-10-15/research/terminal-error-actors-v1/audit.py
```

`result.json` preserves all twelve metadata records and source bindings. The
diagnosis supports the phrase **DOS-side failures**; **emulator faults** is too
specific for the illegal returns. No native/Python-side failure appears among
these recorded errors, which is narrower than proving either implementation
free of defects.
