The optional quiet score-component bridge is ready for independent registration review. No policy has been registered and no games have been run by this agent.

`campaign_native_mobile.py` accepts `--adjustment-scope captures|quiet-occupancy|quiet-mobile` in addition to the existing required `--mobile-captures` packaging marker. `captures` remains the default, with the existing capture adjustment function bodies unchanged. The two quiet scopes are mutually exclusive alternatives: every hidden, disclosed and terminal capture score remains native. The existing frozen mobile-v1 sources and IDs are untouched.

`campaign_mobile_capture.py` adds `quiet_threat` and `quiet_adjustments`. The threat body is identical to frozen quiet-contact-risk-v1 research, apart from its function name. It preserves the maximum across first contacts, exact known-rank behavior, equal-exchange treatment, known Scout rays and far-unknown zero. The destination calculation vacates the source. Occupancy uses existing Q12 mobile mass; mobile scope additionally uses the target's conditional mobile rank probabilities. The only score correction is the posterior old-minus-new danger minus native old-minus-new danger. Terminal scores and every capture receive zero correction.

This is a score-component bridge. Nonlinear tactical and mission branches that previously used native danger remain evaluated by native code; the adapter does not recompute those branches using posterior danger. Goals, routes, probes, priority terms and native score coefficients are retained. Consequently this is neither a complete posterior score recomputation nor a safety guarantee. Population-prior, Q12-tail and MAX-aggregation limitations remain those documented in quiet-contact-risk-v1.

The adapter performs one native `ranked` search, makes no random draw and sends `played` exactly when it overrides the native choice. Native parent wins exact corrected-score ties. The existing public-input path masks concealed rank nibbles before inference or scoring. Runtime modules have no research-directory dependency.

Nineteen combined mechanical and real-observer tests pass. These include 2,880 native static-threat comparisons, private-nibble invariance, source-vacated and guarded Scout rays in both orientations, exact frozen research function-body parity, unchanged default capture function bodies, capture/terminal preservation, cold positions for both sides, no-move handling and Classic Normal scope restrictions. `tests.log` preserves the final run. `initial-test-expectation.log` preserves a corrected test assumption: a cold Scout move can already create a contact, so a cold quiet correction is not necessarily zero. No algorithm changed to resolve that test.

`audit-adapter.py` replays one fixed completed C21 screening game, using 300 forced public-history decisions per scope across both sides. The default scope exactly matches the frozen mobile-v1 launcher choices, including its 18 overrides of the underlying native parent. Quiet occupancy and mobile scopes produce 51 and 67 overrides respectively. For both, every raw ranked native choice matches the frozen template native reference after that reference is corrected to the same actual selected move. Public states also match. The audit asserts one ranked search per decision, no go/seed call from the candidate, and played bookkeeping iff overridden. This qualifies persistent-state/random-state handling on those histories; it is not a strength or population-incidence estimate. No validation cohort is read.

The two owned runtime modules and two new tests are code-final. `source-hashes.json` records their exact hashes. `before/` preserves the prechange runtime sources. The parent owns freezing, packaging, portable qualification, IDs and fresh comparisons. No core, registry, builder or C17 analysis file was edited.

Reproduce from repository root:

```
PYTHONPATH=tools python3 -m unittest tools.test_quiet_contact_risk tools.test_quiet_mobile_adapter tools.test_campaign_mobile_capture tools.test_native_mobile_adapter
PYTHONPATH=tools python3 docs/ai-honest-campaign-2026-10-15/research/quiet-contact-runtime-v1/audit-adapter.py
```

The adapter audit reads and verifies the existing frozen template and mobile-v1 build receipts; it never rebuilds or modifies those identities. Fresh registration should rerun portable qualification from the new immutable source archive. There is no CX16 size or speed claim.
