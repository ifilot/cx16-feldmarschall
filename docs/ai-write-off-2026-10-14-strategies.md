# AI strategy exploration: final handoff

14 October 2026

The exploration retains coordinated missions as the production AI for Normal
and Hard. Final independent classic-rule comparisons against the original
pre-upgrade v0.2.0 policy show a clear strength increase: Normal scores 80.1%
(paired 95% interval 77.2–82.9%) and Hard 75.8% (72.7–78.8%), over 600 games each.
The current native executable matches the archived binaries from both runs.
Hard superiority over current Normal remains unestablished.

## Strategies and records

Earlier work retained adaptive Normal planning and evidence-triggered coordinated
missions after independent validation. Later exploration tested persistent flag
sector hypotheses, rank capability values, selective recapture search, purposeful
reconnaissance, occupancy-conditioned hidden-rank estimates, and the combined
inference/reconnaissance policy. None of these later prototypes showed a reliable
improvement over coordinated missions. The promising combination's development
score did not replicate on independent seeds, so it remains experimental.

[Research and results](ai-strategy-research.md) describe mechanisms, limitations,
primary internet sources, reproducible Make targets, and future research options.
The implementation draws independently on ideas described by Demon of Ignorance.
DeepNash and Ataraxos informed the assessment of offline learning, compact runtime
policies and belief modelling. We did not train or deploy their neural systems.

The [ledger](ai-experiments.json) contains 39 runs and 12,006 games: 6 keep,
19 reject, and 14 diagnostic decisions. Historical entries retain recovered
evaluator sources; recent runs additionally retain whole source snapshots,
executables, deployments, seeds and full moves. The
[integrity report](ai-runs/archive-integrity.json) verifies archive SHA-256/CRC,
evaluator identities and retained executable identities for all 39 archives.
Frozen milestone files are unchanged. No commit, push or publication was made.

## Final verification

- `make all check`: X16/native builds, rules, ten presets, tactical fixtures,
  15,163 hidden-permutation decisions and 3,836 private-inventory comparisons pass.
- Experimental `test-ai-sector`, `test-ai-capability`, `test-ai-exchanges`,
  `test-ai-probes`, `test-ai-beliefs` and `test-ai-inference` targets pass their
  focused and masked-information tests across all 64 combined rule options.
- `tools/test_ai_missions.py`: eight real banked jobs pass; masked views remain
  intact and bank nesting restores banks 22/23/24.
- Current versus frozen coordinated policy: 1,672 Normal and 1,809 Hard decisions
  across six games each match, including independent per-army persistent state.
- [Hard variant parity](ai-runs/final-hard-variants-parity.json): 100 positions,
  zero mismatches, maximum 49 frames (0.82 seconds) per decision.
- [Normal persistent parity](ai-runs/final-normal-persistent-parity.json): ten
  positions, 129 calls each, zero mismatches. The reported 2,239-frame maximum
  measures a complete 129-call batch, not a single decision.
- `make dist site`: runtime distribution and local browser package rebuilt.
- `make test-dist test-ai-levels`: packaged boot, input/display, saved Hard,
  legacy Normal, banked Hard and concealed-rank compatibility pass.
- `git diff --check` passes.

Tactical bank occupancy remains 8,147/8,192 bytes; mission bank 2,175/8,192.
The production build enables `AI_MISSIONS` only. Experimental belief, information
and search macros remain opt-in native targets; no claim is made about their
untested X16 resource cost. Future substantial improvements should use the
mission bank's remaining space and earn promotion through independent strength
validation plus emulator timing, rather than assume a desktop result fits.

## Objective audit

| Requirement | Authoritative evidence | Result |
| --- | --- | --- |
| Explore different strategies | Frozen implementation stages, six later alternatives/combinations, completed paired runs in the ledger | Complete |
| Keep track of results | 39 archives, evaluator identities, move traces, decisions and verified integrity report | Complete |
| Strengthen the computer | Production mission policy; independent direct 1,200-game validation against original v0.2.0, matching current executable; X16 checks | Complete for the tested classic deployment distribution |
| Explore internet approaches | Linked primary engine/research sources, independent implemented adaptations, documented assessment of offline learning | Complete |

Tracked identities, learned beliefs, a distilled desktop teacher and optimized
deployments remain future research opportunities. They are proposals, not
implemented or validated features. There are no pending benchmark processes or
required integration steps for the retained improvement.
