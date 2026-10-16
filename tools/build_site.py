"""Build the static website: the game in the official, checksum-pinned r49 emulator.

Usage:
  python3 tools/build_site.py          (or: make site)

Copies site/ to build/site/, adds the WebAssembly emulator (downloaded once
into build/site-cache/), the runtime files of build/dist/FELDMARSCHALL.ZIP
with a manifest the page loads them from, the ZIP itself, the splash screen
and a few screenshots from docs/. build.json names the version and commit.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'x16emu_wasm-r49.zip'
URL = f'https://github.com/X16Community/x16-emulator/releases/download/r49/{ARCHIVE}'
DIGEST = '9711036cf5b33504815b278fa872b8ec20aef9cb609fd7b17f3685d91312628f'
NAME = 'FELDMARSCHALL'
# in the ZIP for the SD card, but not needed by the emulator
NOT_LOADED = {'AUTOBOOT.X16', 'HASHES.TXT', 'LICENSE.TXT', 'README.TXT'}
SCREENS = ['prepare-play.png', 'play.png', 'game-settings.png', 'options.png']


def emulator():
    cache = ROOT / 'build/site-cache'
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / ARCHIVE
    if not archive.exists():
        print('Downloading official X16 WebAssembly emulator r49…', flush=True)
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read()
        if sha256(data).hexdigest() != DIGEST:
            raise ValueError('Emulator archive checksum mismatch')
        archive.write_bytes(data)
    if sha256(archive.read_bytes()).hexdigest() != DIGEST:
        raise ValueError(f'Emulator archive checksum mismatch: remove {archive} and retry')
    return archive


def commit():
    if os.environ.get('GITHUB_SHA'):
        return os.environ['GITHUB_SHA']
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() or 'unknown'


def main():
    archive = emulator()
    output = ROOT / 'build/site'
    shutil.rmtree(output, ignore_errors=True)
    shutil.copytree(ROOT / 'site', output)

    (output / 'emulator').mkdir()
    with ZipFile(archive) as package:
        for name in ('x16emu.js', 'x16emu.wasm', 'x16emu.data'):
            (output / 'emulator' / name).write_bytes(package.read(name))

    # The distribution never holds saved setups, games or preferences, so
    # every visitor starts fresh.
    distribution = ROOT / f'build/dist/{NAME}.ZIP'
    (output / 'game').mkdir()
    resources = []
    with ZipFile(distribution) as package:
        for entry in package.namelist():
            folder, _, name = entry.partition('/')
            if folder != NAME or not name or '/' in name:
                raise ValueError(f'unexpected entry {entry} in {distribution.name}')
            if name in NOT_LOADED:
                continue
            (output / 'game' / name).write_bytes(package.read(entry))
            resources.append(name)
    assert 'FELDMARS.PRG' in resources, 'FELDMARS.PRG missing from the distribution'
    (output / 'game/manifest.json').write_text(json.dumps({'resources': sorted(resources)}, indent=2) + '\n')
    shutil.copy2(distribution, output / f'{NAME}.ZIP')

    shutil.copy2(ROOT / 'build/preview/splash.png', output / 'splash.png')
    (output / 'screens').mkdir()
    for name in SCREENS:
        shutil.copy2(ROOT / 'docs' / name, output / 'screens' / name)
    (output / '.nojekyll').touch()

    sys.path.insert(0, str(ROOT / 'tools'))
    from build_info import VERSION
    (output / 'build.json').write_text(json.dumps(
        {'version': VERSION, 'commit': commit(), 'emulator': 'r49'}, indent=2) + '\n')
    print(f'Site ready: {output.relative_to(ROOT)} ({len(resources)} runtime files)')


if __name__ == '__main__':
    main()
