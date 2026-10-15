# Original board initializer: runtime completion

This report records one successful real-game run through the original
overlay 6 physical-board initializer, then compares its complete watched
DGROUP window with the reconstructed initializer chain. The debugger trace,
input shim and replay outputs are in the ignored
`build/original-board-initializer-run3/` directory; the reproducible driver is
`scripts/trace_original_board_initializer.py`. A schema-v2 manifest generated
from those archived captures only is at
`build/original-board-initializer-run3/verification.normalized.json`; its
normalizer is `scripts/normalize_original_board_initializer_report.py`.

## Captured call and return

The run starts from the packed original `binaries/STRATEGO.EXE` (SHA-256
`bd3820e59fb36346c37be7970c39e8587241aff88521af2ce4424271ddb96cdf`). The
challenge was entered through SDL key events sent with `SDL_PushEvent`; the
game's own resident keyboard queue and parser consumed them. At overlay 4
`99FC:049C`, AX was `0B7B`, the caller's expected word was `0B7B`, and execution
reached the original success branch at `99FC:050C`. The resulting original
control flow reached the board initializer; no game code, stack, registers, or
input return value were patched.

The loader's resident pointer at `load:9A2E` resolved the active overlay
segment on this run. At overlay 6 runtime `9DEC:1DDD`, the original entry bytes
were `55 8B EC`. The native frame at `SS:SP` was
`F5 2D B3 15 00 01`, or return `15B3:2DF5` and argument word `0100` in
little-endian order. The return frame captured immediately before `RETF 2` at
`9DEC:1F4F` was byte-identical, and execution stopped at `15B3:2DF5` after that
far return.

The `0100` word matters: the initializer tests the low byte of this Pascal
argument. In this capture the low byte is zero, so the lower template is
skipped. The caller bytes at `15B3:2DED` are `B0 00 50` (`mov al,0; push ax`),
which also show that AH contributes to the pushed word. Therefore this run
does **not** demonstrate the nonzero-low-byte/lower-template path. A separate
earlier observation described as argument “1” is not corroborated by the
retained raw frames in the `run2`, `run3`, or `final` directories: all three
frames are `F5 2D B3 15 00 01` (`0100`). Keep that prior observation separate
unless its own raw frame is recovered.

The active overlay image was captured as 8,483 bytes with SHA-256
`dd1898c9b4779a98f13c4a222cc8f9b23c7e994089e44de1cb49d956ec620715`. Its 33
relocations were checked against the packed EXE's loader metadata: add DOS load
segment `0823` to each relocation word; when that value is within the loader's
nominal overlay range `15B3..23AD`, additionally add runtime-CS minus nominal
base (`9DEC - 15B3`). The resulting bytes match the captured loaded image.
This rule is conditional; it does not replace every segment word with the
runtime CS.

At initializer entry, DS was `2808`; the complete watched range
`DS:1800..5FFF` was saved (18,432 bytes, SHA-256
`6656e1591176efb58e5f78c16aabe18221eb4a8d78347d8c49e64fc1fe0a337f`). The
resident RNG state at `DS:3544..3547` was `54 86 76 25`. At the original far
return the same full range had SHA-256
`1958ffea95187486cad49cef292fc0455d29236bcd8288f3aa735ed14e0bdeb3`; 451
bytes changed, including RNG state `32 2C 47 33`. Observed checks passed for
all 40 top-board availability markers cleared, the eight lake movement flags
cleared, and all 24 words in three banks set to 11. Lower rows retained their
initial rank-9, owner-0, movement-1, available-1 state, consistent with the
zero low argument byte.

## Reconstructed replay

The replay copies the actual captured entry bytes for `DS:1800..5FFF` into a
separate DOS process, then executes the reconstructed `BINIT.C` placement and
resident RNG chain using the captured real tables and RNG seed, with argument
`0100`. Its 18,432-byte `C-RESULT.BIN` is byte-for-byte equal to the original
initializer's return snapshot (zero differing bytes); both hashes are
`1958ffea95187486cad49cef292fc0455d29236bcd8288f3aa735ed14e0bdeb3`. The
replay's `ENTRY.BIN` also matches the original entry snapshot exactly.
`STATUS.TXT` containing `PASS` is written by `tools/turbo_c.py` in
`build(run=False)` mode, so it proves only compiler/link completion. Guest
execution is independently established by the fresh `REPLAY.LOG` success
marker and complete `C-RESULT.BIN`; the emulator wrapper exits with status 1.
The normalized report keeps the compiler-build marker separate from guest
execution evidence. The original `compiler.executed: false` is build-helper
metadata and does not describe whether the guest executable ran.

The archived `REPLAY.MAP` was checked retrospectively. Its reserved block is
`0315:0194..7194` (0x7000 bytes), covering the watched `DS:1800..5FFF`
window. `_DATA` ends at DS offset `74C3`, `_BSS` spans `74CA..755F`, and
`_STACK` spans `7560..75E0` (exclusive end), all outside the reservation.
File and heap-control symbols are also outside it; no public data symbol
overlaps the reservation. The MAP does not encode the dynamic heap extent, so
the check establishes static DATA/BSS/stack separation, not a runtime heap
limit. MAP SHA-256: `263f76f367e18b49496705453185f3766cf88e1625fca54dae9714b9c43106b9`.

## Provenance and freshness

The archived run pinned the exact trace-driver bytes by SHA-256
`9c1182d678ce778aaa9945ce44fd37164b73e2dba07907e6d7d4a03a7d788c79` in its
before/after source maps. The current driver has since been extended for
schema-v2 and complete dependency hashing; its current SHA-256 is recorded in
the normalized report's `current_driver_sha256` field.
These hashes are kept separate: the current driver is not claimed to be the
script that performed the archived original-game run. The exact historical
source bytes were not retained in the capture directory; the archived run
preserves the hash and raw evidence only. The current driver is a reviewed
reproduction path awaiting a fresh end-to-end run. The schema normalizer did
not launch the original game or DOSBox-X.

The normalized JSON contains hashes for the original inputs and sources
pinned during the run, every archived replay source/header (19 files), every
staged DOS build input (20 files), and the copied Turbo C/TASM trees (71
files), plus the replay EXE and MAP. It checks that the current reconstruction
sources still match the archived copies used by that replay. The archived
source closure includes `ENUM.C`/`ENUM.H`; generated `MAIN.C`, `ALL.C`, and
`RESERVE.ASM` are hashed from their stored replay copies.
The normalized provenance also preserves historical hashes for the trace
driver, challenge-input driver, debugger session, SDL shim, packed EXE,
resident image and overlay inputs. It lists current post-capture hashes for
driver dependencies separately; the debugger binary itself was not pinned in
the original before/after source map.

Selected raw evidence hashes are:

| Archived evidence | SHA-256 |
|---|---|
| `BOARD-ENTRY-FRAME.BIN` and `BOARD-FAR-RETURN-FRAME.BIN` | `891c5b9ffefb21db281056214f00999030d8e155f5b77d2eba67fe1144784c86` |
| `BOARD-ENTRY-LOADED-OVL6.BIN` | `dd1898c9b4779a98f13c4a222cc8f9b23c7e994089e44de1cb49d956ec620715` |
| `BOARD-ENTRY-DS.BIN` and replay `ENTRY.BIN` | `6656e1591176efb58e5f78c16aabe18221eb4a8d78347d8c49e64fc1fe0a337f` |
| `BOARD-RETURN-DS.BIN`, `BOARD-CALLER-DS.BIN`, and replay `C-RESULT.BIN` | `1958ffea95187486cad49cef292fc0455d29236bcd8288f3aa735ed14e0bdeb3` |
| Replay guest `STATUS.TXT` | `d938fa189912f8776c3deb31a6bec42f403f57b9c8e3ed936bdb076caf6bd61c` |
| Replay guest `REPLAY.LOG` | `4f8f5c2abdbc67a22e9cb9bdd786766efa8bc7d78738c1f140191e89c77ee52e` |

The normalized manifest has hashes for 24 raw evidence files, including the
challenge queue and submitted buffer. It records explicitly that no fresh
original execution occurred during normalization. Its flat `source_hashes`
map contains 167 repository-relative hashes covering current inputs and
drivers, pinned source dependencies, archived source/build/toolchain copies,
raw captures, and replay outputs. All 167 paths were re-hashed successfully
after normalization.

This validates the memory behavior of the initializer chain on one captured
real DS state, including the zero-low-byte argument path. It does not claim
that this capture reached actual board rendering, that the lower-template
path was exercised, or that every initialized field has a recovered semantic
meaning.
