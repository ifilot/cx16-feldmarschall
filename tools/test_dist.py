"""Boot the distribution as an X16 would and check that the game came up.

Usage:
  python3 tools/test_dist.py          (or: make test-dist, after make dist)

Starts the emulator on build/dist/FELDMARSCHALL without -prg, so the ROM finds
and runs AUTOBOOT.X16, then checks the splash bitmap and palette in VRAM,
presses Enter, and checks the game's palette and layer-0 map.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'x16-emulator/api/python'))
from x16agent import X16Agent  # noqa: E402

DIST = ROOT / 'build/dist/FELDMARSCHALL'
CHECKS = (('PALETTE.BIN', 0x1FA00), ('L0MAP.BIN', 0x08000))
SPLASH_CHECKS = (('SPLASH0.BIN', 0x00000), ('SPLASH1.BIN', 0x09600),
                 ('SPLPAL.BIN', 0x1FA00))


def read_vram(emu, address, length):
    return b''.join(bytes(emu.read_memory(address + offset, min(4096, length - offset),
                                         space='vram'))
                    for offset in range(0, length, 4096))


def main():
    emu_path = ROOT.parent / 'x16-emulator/build/x16emu'
    roms = [ROOT.parent / 'emulator/rom.bin', ROOT.parent / 'emulator-win/rom.bin']
    rom = next((r for r in roms if r.exists()), roms[0])
    emu = X16Agent(emu_path, rom, fsroot=DIST)
    failures = 0
    try:
        emu.advance(360)                        # boot, autoboot and load
        for name, address in SPLASH_CHECKS:
            data = (DIST / name).read_bytes()
            if read_vram(emu, address, len(data)) != data:
                print(f'FAIL: {name} is not in VRAM at ${address:05X}')
                failures += 1
        shot = ROOT / 'build/dist-boot.png'
        assert emu.screenshot(shot.resolve())['captured']
        # Other menu keys must leave the splash visible until Enter.
        emu.request('key', key='2', down=True)
        emu.advance(3)
        emu.request('key', key='2', down=False)
        emu.advance(3)
        if bytes(emu.read_memory(0x9F2D, 1)) != bytes([0x05]):
            print('FAIL: a non-Enter key left the splash')
            failures += 1
        emu.request('key', key='Return', down=True)
        emu.advance(3)
        emu.request('key', key='Return', down=False)
        emu.advance(180)
        for name, address in CHECKS:
            data = (DIST / name).read_bytes()
            if read_vram(emu, address, len(data)) != data:
                print(f'FAIL after Enter: {name} is not in VRAM at ${address:05X}')
                failures += 1
        assert emu.screenshot((ROOT / 'build/dist-menu.png').resolve())['captured']
    finally:
        emu.close()
    print(f'distribution boots: {"FAILED" if failures else "ok"} (screen in {shot.relative_to(ROOT)})')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
