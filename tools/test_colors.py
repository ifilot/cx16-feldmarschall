"""Exercise independent color profiles, controls, sprites and saved preferences.

Run after make. Tests use a temporary runtime directory, preserving the
player's COLORS.DAT and DEPLOY.DAT. Captures go to build/test-shots/;
tools/screenshots.py owns docs/.
"""
import shutil
import sys
import tempfile
from pathlib import Path
from PIL import Image

from distribute import runtime_files
from screenshot import Session, X16Agent

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'assets/scripts'))
from color_profiles import FIELDS, ARMIES  # noqa: E402
from palette import vera_palette  # noqa: E402


def palette(session):
    return bytes(session.emu.read_memory(0x1FA00, 512, space='vram'))


def expected(field, armies):
    return vera_palette(FIELDS[field][2], ARMIES[armies][2])


def start(directory):
    session = Session.__new__(Session)
    roms = [ROOT.parent / 'emulator/rom.bin', ROOT.parent / 'emulator-win/rom.bin']
    session.emu = X16Agent(ROOT.parent / 'x16-emulator/build/x16emu',
                           next(r for r in roms if r.exists()), fsroot=directory,
                           options=['-prg', str(directory / 'FELDMARS.PRG'), '-run'])
    session.buttons = 0
    session.emu.advance(360)
    session.press('Return')
    session.emu.advance(180)
    return session


def read_vram(session, address, length):
    return b''.join(bytes(session.emu.read_memory(address + offset, min(4096, length - offset),
                                                 space='vram'))
                    for offset in range(0, length, 4096))


def check_resource(session, name, address):
    data = (ROOT / 'src' / name).read_bytes()
    assert read_vram(session, address, len(data)) == data, f'{name} not loaded into VRAM'


def choose(session, key):
    session.press(key)
    session.emu.advance(180)  # artwork choices include disk loads


def click(session, x, y):
    session.move_mouse(x, y)
    session.button(True)
    session.emu.advance(180)
    session.button(False)


def check_art(session, field):
    art = FIELDS[field][3]
    check_resource(session, f'F{art}TILES.BIN' if art else 'L0TILES.BIN', 0x00000)
    check_resource(session, f'F{art}MAP.BIN' if art else 'L0MAP.BIN', 0x08000)
    check_resource(session, 'L1TILES.BIN', 0x10000)
    check_resource(session, 'SPRITES.BIN', 0x18000)


def ui_regions(path):
    # Fixed artwork and UI content, excluding the selected field's name/star.
    boxes = [(0, 0, 640, 16), (0, 16, 16, 428), (0, 416, 428, 480),
             (428, 0, 640, 104), (428, 280, 640, 416)]
    with Image.open(path) as image:
        return [image.convert('RGB').crop(box).tobytes() for box in boxes]


def check_field_offsets(session):
    tilemap = read_vram(session, 0x08000, 128 * 60 * 2)
    for row in range(60):
        for col in range(80):
            attribute = tilemap[(row * 128 + col) * 2 + 1]
            assert attribute >> 4 == (6 if 2 <= row < 52 and 2 <= col < 52 else 0)
    # A vacant cell in the preview board uses the field palette for its grid.
    attribute = read_vram(session, 0x0C000 + 22 * 256 + 2 * 2 + 1, 1)[0]
    assert attribute >> 4 == 6, 'board grid must follow the selected field'


def main():
    output = ROOT / 'output/style-studies'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='feldmarschall-appearance-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(directory)
        try:
            assert palette(session) == expected(0, 0)
            choose(session, '4')
            original = palette(session)
            fonts = read_vram(session, 0x10000, 206 * 32)
            for field in range(len(FIELDS)):
                choose(session, str(field + 1))
                assert palette(session) == expected(field, 0)
                assert palette(session)[32:96] == original[32:96], 'field changed armies'
                assert palette(session)[:192] == original[:192], 'field changed UI/text colors'
                assert palette(session)[224:] == original[224:], 'field changed other palettes'
                check_art(session, field)
                check_field_offsets(session)
                shot = output / f'game-field-{FIELDS[field][0]}.png'
                session.shot(shot)
                if field == 0:
                    classic_ui = ui_regions(shot)
                else:
                    assert ui_regions(shot) == classic_ui, 'field changed rendered classic UI'
            choose(session, 'Tab')
            last_field = len(FIELDS) - 1
            field_palette = palette(session)[192:224]
            for army in range(len(ARMIES)):
                choose(session, str(army + 1))
                assert palette(session) == expected(last_field, army)
                assert palette(session)[192:224] == field_palette, 'armies changed field'
                check_art(session, last_field)
            assert read_vram(session, 0x10000, 206 * 32) == fonts
            # Reject number keys outside the six army choices.
            choose(session, '7')
            assert palette(session) == expected(last_field, len(ARMIES) - 1)
            click(session, 500, 224)  # Polished tiles: fourth field
            click(session, 500, 328)  # Mint / rose: fifth army scheme
            assert palette(session) == expected(3, 4)
            check_art(session, 3)
            blue_attr = read_vram(session, 0x0C000 + 2 * 256 + 2 * 2 + 1, 1)[0]
            red_attr = read_vram(session, 0x0C000 + 42 * 256 + 2 * 2 + 1, 1)[0]
            assert blue_attr >> 4 == 2 and red_attr >> 4 == 1
            # Modern rank numbers replace only the tokens, on the board and as sprites.
            choose(session, 'Tab')
            choose(session, '2')
            check_resource(session, 'RANKTIL.BIN', 0x10000 + 206 * 32)
            check_resource(session, 'RANKSPR.BIN', 0x18000)
            assert read_vram(session, 0x10000, 206 * 32) == fonts
            click(session, 500, 384)  # Classic numbering
            check_art(session, 3)
            session.move_mouse(420, 420)
            session.shot(ROOT / 'build/test-shots/options.png')
            click(session, 476, 440)
            assert (directory / 'COLORS.DAT').read_bytes() == b'CLR6\x03\x04\x00\xa2'
            choose(session, '1')
            session.move_mouse(452, 172)
            session.button(True)
            session.move_mouse(300, 320)
            assert read_vram(session, 0x1FC0F, 1)[0] & 15 == 1
            check_art(session, 3)
            session.shot(output / 'game-dragged-piece.png')
            session.button(False)
            choose(session, 'Escape')
        finally:
            session.close()
        session = start(directory)
        try:
            session.emu.advance(240)
            assert palette(session) == expected(3, 4), 'preferences lost after restart'
            check_art(session, 3)
        finally:
            session.close()
        # Migrate retained profiles from the earlier color-only release.
        (directory / 'COLORS.DAT').write_bytes(b'CLR1\x01\x04\xa0')
        session = start(directory)
        try:
            assert palette(session) == expected(1, 1), 'retained preferences did not migrate'
            check_art(session, 1)
        finally:
            session.close()
        # Former shield preferences are discarded while retained colors survive.
        (directory / 'COLORS.DAT').write_bytes(b'CLR2\x04\x02\x03\xa0')
        session = start(directory)
        try:
            session.emu.advance(240)
            assert palette(session) == expected(2, 2)
            check_art(session, 2)
        finally:
            session.close()
        # Previous paper choices keep paper; removed surfaces fall back to it.
        for old_field in (2, 3, 4):
            checksum = 0xA5 ^ old_field ^ 2
            (directory / 'COLORS.DAT').write_bytes(b'CLR3' + bytes([old_field, 2, checksum]))
            session = start(directory)
            try:
                session.emu.advance(240)
                assert palette(session) == expected(2, 2)
                check_art(session, 2)
            finally:
                session.close()
        # Retain paper and replace saved decorative motifs with polished tiles.
        for old_field in (2, 3, 4, 5):
            checksum = 0xA5 ^ old_field ^ 2
            (directory / 'COLORS.DAT').write_bytes(b'CLR4' + bytes([old_field, 2, checksum]))
            session = start(directory)
            try:
                session.emu.advance(240)
                migrated = 2 if old_field == 2 else 3
                assert palette(session) == expected(migrated, 2)
                check_art(session, migrated)
            finally:
                session.close()
        # The modern numbering survives a restart.
        (directory / 'COLORS.DAT').write_bytes(b'CLR6\x01\x02\x01' + bytes([0xA5 ^ 1 ^ 2 ^ 1]))
        session = start(directory)
        try:
            assert palette(session) == expected(1, 2)
            check_resource(session, 'RANKTIL.BIN', 0x10000 + 206 * 32)
            check_resource(session, 'RANKSPR.BIN', 0x18000)
        finally:
            session.close()
        (directory / 'COLORS.DAT').write_bytes(b'CLR5\x01\x02\xa6')
        session = start(directory)
        try:
            assert palette(session) == expected(1, 2), 'CLR5 preferences did not migrate'
            check_art(session, 1)
        finally:
            session.close()
        (directory / 'COLORS.DAT').write_bytes(b'CLR5\xff\x02\x58')
        session = start(directory)
        try:
            assert palette(session) == expected(0, 0), 'invalid settings did not fall back'
            check_art(session, 0)
        finally:
            session.close()
    print('appearance options: all fields/colors, independence, original pieces, save/reload and migration passed')


if __name__ == '__main__':
    main()
