Research/proposal only. No existing runtime, source, registry, builder, plan or analysis file was edited.

- PROTOCOL.json froze the geometric C21-only screening gate before sampling; audit.py/result.json preserve all335 eligible roots and source hashes.
- CERTIFICATE-PROTOCOL.json froze the first20 bounded actor-only proofs; certificate.py/audit_certificates.py/certificate-result.json preserve those results and public fixtures.
- CONTROL-PROTOCOL.json froze the common any-actor disclosed-capture response control before its evaluation; certificate_common.py/audit_common.py/common-result.json preserve both fork and saved-native proofs.
- test_certificate.py/tests.log:11 tests pass. initial-test-expectation.log preserves the corrected overly specific failure-label assertion.
- RUNTIME-PROPOSAL.json: proposal for root approval, with exact quantifiers, control, scope and budget. CONCLUSION.md explains the sharply reduced causal-opportunity count.

Reproduce from repository root, with a tools PYTHONPATH:

```
PYTHONPATH=tools python3 docs/ai-honest-campaign-2026-10-15/research/disclosed-fork-preflight-v1/audit.py
PYTHONPATH=tools python3 docs/ai-honest-campaign-2026-10-15/research/disclosed-fork-preflight-v1/audit_certificates.py
PYTHONPATH=tools python3 docs/ai-honest-campaign-2026-10-15/research/disclosed-fork-preflight-v1/audit_common.py
PYTHONPATH=tools python3 docs/ai-honest-campaign-2026-10-15/research/disclosed-fork-preflight-v1/test_certificate.py
```

Results contain only public masked root boards/counts/shuttle and legal-public outcome witnesses. JSON shuttle object keys must be converted back to integer army keys to replay a fixture. The model never receives an enemy setup; the outer referee replay alone uses setups to produce recorded public combat facts. No validation trajectories are accessed.

Rules references: tools/feldmarschall.py Position.moves implements the two-squares ban; tools/tournament_store.py replay checks no-move outcomes, including 'neither can move' draw. The proof keeps the corresponding own-mobility test when the enemy has no moves. The research successor mirrors Position.fight's marking of an own defender MOVED after a failed attack; production flags differ here. This does not affect Classic own legality/material proof, but a future runtime should preserve exact production flags rather than copy the extra MOVED bit.

The common response class ORs every legal disclosed surviving capture, not every possible friendly quiet move or uncertain attack. All enemy replies remain AND branches. Negative results are absence of proof in this response class. One new opportunity among the selected20 does not estimate incidence or strength across the full335 roots or400 games.

Expanded evaluation is complete under EXPANSION-PROTOCOL.json. audit_all.py/all-result.json preserve all335 roots,336forks, the common controls, filters, node counts and exact first20 proof parity. audit_unique.py/unique-result.json deduplicate public comparison kernels without additional proof queries;100new roots collapse to20comparisons across13games (83roots in one game). expanded-summary.json records measured cost. FIRST20-CONCLUSION.md preserves the prior stage; current CONCLUSION.md reflects the full fixed gate. Original first20 results are unchanged. Root's later executable-witness/actor-specific runtime refinement is separate work, not part of these research results.
