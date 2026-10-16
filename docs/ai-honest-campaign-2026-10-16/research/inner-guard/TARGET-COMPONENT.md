# CX16 qualification of the deployment component alone

The one-swap **ordinary production deployment component fits** the existing
MISSION bank. This does **not** qualify the desktop full public-template adapter
or establish that the source-informed prior fits the CX16.

The dedicated deployment C bytes were read from C110's already frozen policy
archive and matched the working component's hash. The audit built two separate
copied `/tmp` production trees with cc65's CX16 target, the complete existing
C/assembly source set, production Student/memory/mission features, the original
linker configuration, sound library, generated headers and 1024-byte C stack.
Only the candidate's deployment source and `AI_FORTRESS_INNER_GUARD` differ from
the Fortress-only control. No template prior, desktop adapter, extra belief bank
or custom linker relocation is enabled.

| Allocation | Fortress control | Inner guard | Change |
|---|---:|---:|---:|
| MISSION code | 5820 bytes | 5894 bytes | +74 |
| MISSION read-only data | 314 | 314 | 0 |
| MISSION BSS | 1381 | 1381 | 0 |
| MISSION total / free | 7515 / 677 | 7589 / 603 | +74 / −74 |
| AI total / free | 8147 / 45 | 8147 / 45 | 0 |
| PLAY total / free | 8032 / 160 | 8032 / 160 | 0 |
| Ordinary BSS | 2018 | 2018 | 0 |

`PLAY.BIN` and `AI.BIN` are byte-identical between builds. `MISSION.BIN` grows
from 6,134 to 6,208 bytes; its file excludes the 1,381-byte BSS reservation. The main
PRG remains 35,096 bytes, with changed relocation references. These are linked
RAM-bank program files, not a system-ROM modification.

The X16 emulator booted each copied program and executed **52 actual deployment
gateway calls** through bank 24. Both colors, Classic Normal, easy/hard fallback
controls, ordinary seeds and all five seeds whose first RNG draw is rejected
were included. Every resulting 100-byte board and next RNG result matched a
temporary native build of the corresponding deployment. The real gateway
restored caller bank 22 and the hardware stack after each call. Easy/hard
deployment boards match the control. These fixtures do not execute full AI
turns, test subsequent memory history or establish hardware gameplay.

Measured Normal setup durations include real gateway work and audio interrupts.
Twelve of 18 matched Normal cases differ by 97 CPU cycles; the remaining six have
interrupt-window differences, so that observation is not an isolated latency
bound. The largest observed candidate Normal setup took 79,013 cycles, about 9.88 ms
at an assumed 8 MHz. No per-turn latency or full-prior cost is inferred from this
deployment measurement.

All files under the workspace's `src` tree had identical hashes before and
after. No production output, artwork, Makefile or shared source was replaced.
The audit also verified the frozen policy archive hash and every retained output
against its recorded digest.

Reproduce with `python3 tools/audit_new_campaign_inner_guard_target.py`.
[Exact commands, input hashes, segments and banked records](component-target.json)
and [linked binaries/maps/symbols](component-target-build.zip) preserve the result.
This is target component fit and deployment execution evidence, separate from
the immutable desktop policy's playing-strength qualification.
