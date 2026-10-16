# Per-piece mobile capture inference, version1

The existing source-template model already returns mobile-rank probabilities for each concealed piece, but the native prior interface keeps only Flag/Bomb probabilities and treats mobile pieces as exchangeable. This experiment retains the same Q12 immobile masses and replaces only the conditional mobile part of hidden-capture expected gain. It adds no sampled worlds or extra native search.

Native danger, persistent objectives, quiet moves and publicly disclosed captures stay unchanged. The correction reconstructs signed integer gain, the existing ten-point cheap-probe term, and the existing forty-point near-own-Flag bonus threshold. The public template posterior can still be wrong on procedural formations. This partial bridge is not full posterior planning.

Eight focused tests pass: conditional-mean isolation, exact exchangeable zero correction, both-side hidden-nibble invariance, actual native expected_at comparisons on more than1,000 rank/target fixtures, probe/defence thresholds, and a real compiled immediate Flag-win fixture. Independent review found and closed the probe-threshold and omitted-terminal-credit issues before registration.

The frozen old policy rebuilds exactly. A ranked single-search/no-correction bridge matches it across160public-history decisions. Real correction matches an actual-choice-aligned reference across300decisions, making19overrides. A copied runtime outside the checkout also matches300decisions with19overrides, generated deployments and public state/history. These are integration checks on one completed screening game, not19better moves or a strength estimate.

An observational timing run on the same300positions under concurrent tournament load measured baseline0.869ms and candidate0.845ms mean decision time. The small negative paired difference is timing noise and establishes no speedup. This remains a desktop prototype with no CX16 size or cycle qualification.

Fresh immutable paired DOS and honest-opponent screens are cycles37/38. No parameters were selected from those games and no strength result exists yet. Reproduce focused checks with PYTHONPATH=tools python3 -m unittest tools.test_campaign_mobile_capture tools.test_mobile_capture_native_oracle tools.test_native_mobile_adapter -v. Public-history qualification scripts and raw JSON reports accompany this note.
