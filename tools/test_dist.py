"""Boot the distribution as an X16 would and check that the game came up.

Usage:
  python3 tools/test_dist.py          (or: make test-dist, after make dist)

Starts the emulator on build/dist/STRATEGO without -prg, so the ROM finds
and runs AUTOBOOT.X16, then checks that the palette and the layer-0 map in
VRAM are those of the shipped files, and saves build/dist-boot.png.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'x16-emulator/api/python'))
from x16agent import X16Agent  # noqa: E402

DIST = ROOT / 'build/dist/STRATEGO'
CHECKS = (('PALETTE.BIN', 0x1FA00), ('L0MAP.BIN', 0x08000))


def main():
    emu_path = ROOT.parent / 'x16-emulator/build/x16emu'
    roms = [ROOT.parent / 'emulator/rom.bin', ROOT.parent / 'emulator-win/rom.bin']
    rom = next((r for r in roms if r.exists()), roms[0])
    emu = X16Agent(emu_path, rom, fsroot=DIST)
    failures = 0
    try:
        emu.advance(360)                        # boot, autoboot and load
        for name, address in CHECKS:
            data = (DIST / name).read_bytes()
            if bytes(emu.read_memory(address, len(data), space='vram')) != data:
                print(f'FAIL: {name} is not in VRAM at ${address:05X}')
                failures += 1
        shot = ROOT / 'build/dist-boot.png'
        assert emu.screenshot(shot.resolve())['captured']
    finally:
        emu.close()
    print(f'distribution boots: {"FAILED" if failures else "ok"} (screen in {shot.relative_to(ROOT)})')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
