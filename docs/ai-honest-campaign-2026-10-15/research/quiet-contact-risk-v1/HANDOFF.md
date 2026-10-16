Research only; no runtime policy is implemented or registered.

- `PROTOCOL.json`: fixed sample, formulas and limitations, written before sampling.
- `risk.py`: isolated public-only MAX danger reconstruction and channel diagnostics.
- `test_native_risk.py`, `tests.log`: four focused mechanical tests, including 2,880 native oracle comparisons. The oracle appends a wrapper only to a temporary core copy.
- `audit.py`, `result.json`: reproducible fixed-prefix opportunity audit, no native search and no new games.
- `source-inputs.zip`, `source-inputs.json`: exact core/helper source inputs and hashes. Replay requires the C21 fmtour identified by SHA256 in result.json.
- `CONCLUSION.md`: interpretation and proposed controlled pilot.

Run from the repository root:

```
PYTHONPATH=tools python3 docs/ai-honest-campaign-2026-10-15/research/quiet-contact-risk-v1/test_native_risk.py
PYTHONPATH=tools python3 docs/ai-honest-campaign-2026-10-15/research/quiet-contact-risk-v1/audit.py
```

The audit reads only the explicitly selected completed C21 screening file. It does not use current candidate or prior validation cohorts. Source hashes should match before reproducing; the archive preserves the reviewed input version if the workspace subsequently changes. Coverage is conditional on 16 fixed opening pairs/prefixes and does not estimate final playing strength or population incidence. Existing runtime files and the builder are untouched.
