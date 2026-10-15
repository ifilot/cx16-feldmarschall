# Simple unbanked relocation does not fit

The prior interface can leave the AI bank, but moving all of it into unbanked
memory is insufficient. The isolated complete production link then fails with
`Segment 'BSS' overflows memory area 'BSS' by 748 bytes`. No production source,
saved policy, archive, linker configuration or bank gateway was changed.

The experiment wraps only the existing prior arrays, setter/clear/valid functions
and `expected_at` helper with cc65 code/BSS segment pragmas in temporary copies.
It changes no probability, arithmetic or move rule. Always-visible helper code
would read AI private state while the AI bank remains selected; no new bank
switch is introduced. Actual banked execution was not attempted because the
candidate fails the complete link.

| Isolated build | AI code / read-only / BSS bytes | Added main code / BSS | Complete link |
| --- | ---: | ---: | --- |
| Production baseline | 6519 / 424 / 1204 | 0 / 0 | Pass; 45 AI bytes free |
| Unmodified prior interface | 7339 / 424 / 1627 | 0 / 0 | AI overflow: 1198 bytes |
| Prior helpers and storage in main | 6467 / 424 / 1204 | 872 / 423 | Main BSS overflow: 748 bytes |

The relocated AI object would leave 97 bytes in that bank, but the main allocation
cannot accommodate the additional 1295 bytes. BSS includes the 401-byte explicit
prior packet and 22 bytes of compiler static locals. These are measurements from
cc65 `-O -t cx16` with the production source set, existing vendor library,
unchanged linker configuration and 1024-byte software stack. The successful
baseline PRG is 35096 bytes. All workspace source hashes were identical before
and after the experiment.

`audit.json` records commands, diagnostics, input hashes and object segments for
all three builds. `target-build-evidence.zip` preserves generated assembly,
objects, maps/symbols where available, the exact temporary transformed source,
and successful baseline outputs. `tools/audit_native_belief_main_fit.py` reproduces
the experiment into a fresh output directory.

This rejects simple relocation, not the possibility of a port. A compact belief
representation or explicit cross-bank interface needs a separately versioned
design and real banked execution checks. The current experiment also excludes
the Python posterior computation: fitting this interface alone would still not
produce a complete CX16 inference implementation. No playing-strength result
is attached to this target-fit study.
