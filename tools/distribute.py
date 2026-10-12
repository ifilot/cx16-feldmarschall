"""Create a reproducible binary distribution containing only runtime files.

Usage:
  python3 tools/distribute.py          (or: make dist)

Writes build/dist/FELDMARSCHALL/ and build/dist/FELDMARSCHALL.ZIP. The runtime files
are the game itself, a copy named AUTOBOOT.X16 that the X16 starts on
power-up, and every file the game loads into VRAM (found in the load_vram
calls of src/ui/video.c, so a new resource cannot be forgotten). The test
programs (BRIDGE.PRG) and the player's saved deployments (DEPLOY.DAT) stay
out. Entries carry a fixed date, so the same build gives the same ZIP.
"""
import hashlib
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
NAME = 'FELDMARSCHALL'


def runtime_files():
    video = (ROOT / 'src/ui/video.c').read_text()
    resources = re.findall(r'load_vram\("([A-Z0-9]+\.[A-Z0-9]+)"', video)
    assert resources, 'no load_vram calls found in src/ui/video.c'
    return ['FELDMARS.PRG'] + resources


README = '''CX16 Feldmarschall

A game of hidden armies for the Commander X16, at 640x480 in sixteen
colours.

Keep all files in this directory together on your X16 SD card. Copy them
to the root of the card to boot the game automatically: AUTOBOOT.X16 is a
copy of FELDMARS.PRG and starts the game on power-up. Otherwise load
FELDMARS.PRG and run it.

Emulator: x16emu -prg FELDMARS.PRG -run

The game is played with the mouse. Deploy your army by dragging pieces
from the tray onto your four home rows, or load one of ten classic
deployments; then play against the computer. Escape returns to the menu.
Deployments you save go into DEPLOY.DAT, which the game creates here.

FELDMARS.PRG is the game; the .BIN files hold its graphics and palette.

Source, license (GPL-3.0-or-later) and credits:
https://github.com/ifilot/cx16-feldmarschall
'''


def main():
    destination = ROOT / 'build/dist' / NAME
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    files = runtime_files()
    for name in files:
        base, extension = name.split('.')
        assert 1 <= len(base) <= 8 and 1 <= len(extension) <= 3, f'{name} is not an 8.3 name'
        source = ROOT / 'src' / name
        assert source.exists(), f'{source} is missing: run make first'
        shutil.copyfile(source, destination / name)
    shutil.copyfile(ROOT / 'src/FELDMARS.PRG', destination / 'AUTOBOOT.X16')
    (destination / 'README.TXT').write_text(README)
    shutil.copyfile(ROOT / 'LICENSE', destination / 'LICENSE.TXT')

    names = sorted(p.name for p in destination.iterdir())
    hashes = {name: hashlib.sha256((destination / name).read_bytes()).hexdigest() for name in names}
    (destination / 'HASHES.TXT').write_text(''.join(f'{hashes[n]}  {n}\n' for n in names))

    archive = destination.parent / f'{NAME}.ZIP'
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as output:
        for path in sorted(destination.iterdir()):
            entry = ZipInfo(f'{NAME}/{path.name}', date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, path.read_bytes())
    with ZipFile(archive) as packaged:
        assert packaged.testzip() is None, 'the ZIP failed its CRC check'
        for name, digest in hashes.items():
            assert hashlib.sha256(packaged.read(f'{NAME}/{name}')).hexdigest() == digest, name
    contents = list(destination.iterdir())
    print(f'Distribution: {archive.relative_to(ROOT)} ({archive.stat().st_size} bytes; '
          f'{len(contents)} files, {sum(p.stat().st_size for p in contents)} bytes unpacked)')


if __name__ == '__main__':
    main()
