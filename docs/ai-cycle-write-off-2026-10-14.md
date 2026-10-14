# Five-step AI development cycle: handoff and completion audit

14 October 2026

All five requested steps were carried out in order. The runtime policy remains
the validated mission AI. The new public-history tracker and learned capture
model are retained as opt-in native/X16 components; the fitted model did not earn
promotion. Deployment experiments found a confirmed setup-only advantage for
existing CORNER FORTRESS with Hard, and retain three diverse evolved alternatives.
No commit, push, publication or player save modification was performed.

## Outcomes

- Broader benchmarks: seven layout families and five distinct opponents,
  5,600 validation games plus a 70-game infrastructure check. Decoys reduce the
  mission policy's advantage, exposing a useful diagnostic weakness.
- Diagnostic collection: 1,587 positions from 1,074 sampled losses/capped games,
  with reproducible public histories and masked inputs separated from oracle data.
- Public tracking: 84 stable piece records, 941 bytes of snapshot state, certain
  movement/combat constraints and uncertain positive-prior encounter weights.
- Offline learning: 8,540,573 teacher nodes, 512 positions, 1,736 labels and a
  25-node/150-byte integer model. Development scored 48.9% over 280 fresh games;
  promotion was rejected. X16 parity and actual history-sensitive banked inference
  are verified.
- Deployment optimization: 52 layouts searched, three new alternatives separated
  by 32–35 piece placements, 11,760 search/validation/confirmation games. Fresh
  Hard confirmation found CORNER FORTRESS +3.0 percentage points over protected
  random (complete deployment-block 95% interval +0.2–5.7). The evolved alternative's
  +2.1-point result was inconclusive.

[The development record](ai-development-plan-2026-10-14.md) contains mechanisms,
scores, limitations, primary research links and reproduction commands. The
[experiment ledger](ai-experiments.json) contains 48 runs and 29,758 games;
accepted, rejected and diagnostic work is preserved. The
[integrity report](ai-runs/archive-integrity.json) verifies archive hashes/CRC,
evaluator identities, program/script identities, game counts and trace lengths.

## Requirement-by-requirement audit

| Requested requirement | Authoritative evidence | Status |
| --- | --- | --- |
| Broaden layouts: unguarded, unusual and deceptive placements | `stress_setup`, inventory/property tests over 2,500 samples, broad Normal/Hard runs with all seven groups | Complete |
| Vary opponents and test generalization | Five retained opponents; new-group scores and complete trace archives | Complete for the tested Classic distribution |
| Extract loss/stall positions and diagnose concrete symptoms | [Corpus manifest](ai-diagnostics/manifest.json), 1,587 verified replay snapshots, sampled repetition/Scout/flag/route observations and documented oracle caveats | Complete |
| Stable identities and public movement/encounter histories | Shared `ai_memory.c`; 6,506 focused checks, snapshot checks, 24 banked events/1,892 matched live histories | Complete as an opt-in component |
| Certain deductions and uncertain beliefs | Scout/movement/combat masks, same-outcome Silent Defense privacy tests, positive-prior approach/retreat weighting; consumed by teacher sampling | Complete; weights are not calibrated probabilities |
| Stronger desktop analysis for labels | Three-ply sampled-world teacher; controlled exchange improves on two-ply horizon; public-only label invariance and inventory tests | Complete; global teacher strength is not established |
| Compact fitted X16 policy | Retained model/labels/programs, 100 fresh parity positions, 120 real banked decisions, cold/warm age-split values +58/+36 matching native | Complete as an experiment; no reliable game-strength gain |
| Search and retain several strong diverse setups | [Portfolio](ai-deployments/portfolio.json); 52-layout search; three independently measured alternatives with pairwise distance 32–35 | Complete against the fixed league |
| Measure setup gains separately | Same frozen move executable, genotype-following sides, fresh controls and block-level confirmation; actual trial/program integrity checks | Complete |
| Keep the order and preserve results | Ordered development record, immutable run/source/program bundles and supplemental manifests | Complete |

## Practical limits and verification

Classic strength evidence does not establish optional-variant or human strength.
The tracker preserves history within play and AI_TEST snapshots; current GAME.DAT
loads restart observed history. The learned policy was trained with cold-history
examples and verified on both sides of a history-sensitive split. It remains
disabled in production. Its prototype mission bank uses 6,477/8,192 bytes, with
six bytes of main RAM below the reserved 1 KB stack. No stack reservation was
reduced to fit these components.

`make all check`, all experimental tracker/student/teacher checks, benchmark
layout checks, corpus validation and deployment integrity checks pass. Builds
verify the model table exists in both experimental X16 binaries; the original
misplaced-flag failure is retained alongside the corrected result. Default
production builds still exclude the experimental tracker/model. Future adoption
of deployment selection or improved learning should preserve hidden-information
fairness, deploy diverse layouts, and earn its own independent strength gate.

There are no running experiments or unfinished required steps for this cycle.
More capable information-set teachers, broader training data and runtime
deployment selection are future development choices, not completed features.
