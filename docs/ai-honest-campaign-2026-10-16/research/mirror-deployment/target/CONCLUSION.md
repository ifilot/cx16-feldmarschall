The frozen fixed-mirror and ticket-mixture deployment components both fit and run
through the real CX16 bank-24 setup gateway on the ordinary production Student
build. This qualifies deployment feasibility only; it does not qualify the full
source-template inference policy or establish playing strength.

| Build | Added MISSION code | MISSION used / free | New data/BSS | MISSION.BIN |
|---|---:|---:|---:|---:|
| Fortress control |0 B|7,515 /677 B|0 B|6,134 B|
| Fixed mirror |221 B|7,736 /456 B|0 B|6,355 B|
| Existing-ticket mixture |231 B|7,746 /446 B|0 B|6,365 B|

FELDMARS.PRG remains 35,096 bytes, PLAY.BIN 8,032 bytes and AI.BIN 6,943 bytes in all
three builds. AI's total linked allocation remains 8,147 bytes including BSS,
leaving 45 bytes; mirror code is placed in MISSION rather than consuming that
space. These are a PRG and loadable RAM-bank files, not system ROM images.

The ordinary control's complete C/assembly/header inputs, compile flags and six
output hashes exactly match the previously qualified ordinary production baseline
from the separate open-reserve receipt. The two candidate builds replace only the
deployment source, using identical bytes extracted from the registered mirror
policy archives and the corresponding frozen macro. Both frozen archives remain
unchanged. Full build inputs and outputs are preserved in the new build ZIP.

All 270 real banked setup calls pass: three builds × Easy/Normal/Hard × both colors
× fifteen seeds. Seeds cover all ten accepted ticket classes and all five initial
draw-rejection cases: 14457, 31996, 32510, 48509, 49023. In every call, returned board
bytes and next RNG match a native build from the same source. Independent canonical
and reflected setup serialization also matches the declared formation/ticket
formula. Easy/Hard boards match control; only Classic Normal changes orientation.
No extra RNG draw is introduced.

The actual production setup gateway returns to caller bank 22. Both hardware and
cc65 software stack pointers return unchanged, and a sixteen-byte canary at the
bottom of the reserved 1,024-byte C stack remains untouched in every case. This
checks balance and a lower guard, rather than measuring complete stack high-water
use. Emulator cycle deltas include gateway and possible interrupt work, and are
not hardware latency measurements.

The audit runs from copied temporary source/runtime trees. Every original source
and runtime file hash remains unchanged; no production output, artwork, policy
or earlier target evidence is edited. Source-template inference, complete AI turns,
banked inference/audio interactions and physical hardware gameplay remain outside
this qualification.

Evidence: `component-target.json`, three full-link logs,
`component-target-build.zip`, `independent-review.json` and `manifest.json`.
Harness: `tools/audit_new_campaign_mirror_target.py`.
