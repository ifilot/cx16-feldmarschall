# Installed honest AI

Classic Normal uses `production-fortress-template-q24-cache-v1-normal`: the
guarded Student scorer, Fortress deployment and cached integer public Flag/Bomb
inference. Other difficulties and optional-rule policies retain their previous
definitions. Enemy setups, private deployment seeds and hidden ranks are never
inputs. This is the native port of our established DOS specialist; unfamiliar
human deployments may favor other strategies.

Fresh paired DOS validation used 1,024 attempts per arm. The native release
scored 40.74%, versus 40.83% for the floating reference (wins plus half draws).
The complete-pair difference was -0.05 percentage points, with a 95% interval
[-0.15, 0.00], passing the prospective two-point noninferiority margin. Twenty
candidate and 21 reference errors remain unscored. Independently completing
their unknown outcomes gives finite-cohort bounds [-2.10, +1.90] points; these
are not confidence intervals and slightly cross the margin. Qualification does
not establish full-cohort noninferiority for every possible error completion.

On fresh seed-validation layouts against the honest Missions opponent, both
arms scored 84.24% in 384 games, with no errors; paired 95% interval [-1.04,
+1.04] points. This is a numerical port qualification, not a strength increase
or a universal claim about human play.

Two X16 fixtures matched all 160 complete turns, native moves, RNG and integer
inference values. Audio, bank returns and stack guards passed. Maximum measured
turn cost was 11,601,396 cycles, 1.45 seconds at 8 MHz, below the fixed 2.5-second
fixture limit. One fixture mechanically restores owner caches to exercise hits;
its hit count is not a natural gameplay rate. Timing is not a universal bound.
Reproducible builds, save/load/reset/rematch, legacy saves, hidden-information
regressions and SD-card autoboot packaging also passed.

`ai-release/manifest.json` binds the portable AI/model files, policy snapshot,
target flags and qualification certificate. The final production build leaves MAIN 62,
AI 78, MISSION 235, PLAY 154 and BELIEF 974 bytes free; inspect each new build's
`src/ai-build.json` for current capacity. The game owns authoritative rules.

## Updating the release

The separate `feldmarschall-ai` repository retains experiments, frozen source
archives, datasets, negative results, the DOS adapter and Classic tournament/Qt6
review tools. Its `game-core.lock.json` pins an offline snapshot of this game.
The local repository is a sibling checkout; GitHub publication is pending valid
repository-creation credentials. No live research branch is followed by the game.

After qualification in the research repository:

```sh
# In feldmarschall-ai:
python3 tools/certify_ai_release.py
python3 tools/export_ai_release.py production-fortress-template-q24-cache-v1-normal --qualification docs/ai-consolidation/release-qualification.json
# In cx16-feldmarschall:
python3 tools/ai_release.py import ../feldmarschall-ai/releases/production-fortress-template-q24-cache-v1-normal
make check native dist
make test-ai-levels test-flow test-demo test-sound test-dist
```

Use a new immutable ID/version for every changed policy. Import rejects
corruption, incomplete qualification and reuse of an ID with changed contents.
The certificate command reproduces this frozen consolidation study; future
releases need their own preregistered qualification cohorts and certificate.
`make verify-ai-release` detects subsequent edits to installed AI/model files.
Full qualification receipts and their SHA-256 hashes are recorded in
`ai-release/qualification.json`; detailed evidence lives under
`docs/ai-consolidation` in the research repository.
