"""Exercise setup management, mandatory pre-game deployment, and rematches.

The emulator runs in a temporary runtime directory, leaving player saves alone.
"""
import re
import shutil
import tempfile
from pathlib import Path
from PIL import Image

from distribute import runtime_files
from test_colors import ROOT, start, choose, click, read_vram


def symbol(name):
    return int(re.search(r'al ([0-9A-F]+) \._' + name + r'\b',
                         (ROOT / 'src/FELDMARS.sym').read_text()).group(1), 16)


def text(session, row, first=54, width=25):
    header = (ROOT / 'src/gfx.h').read_text()
    fonts = [int(re.search(r'#define ' + name + r'\s+(\d+)', header).group(1))
             for name in ('L1_FONT', 'L1_FONT_PLATE')]
    cells = read_vram(session, 0x0C000 + row * 256 + first * 2, width * 2)
    result = ''
    for i in range(width):
        tile = cells[i * 2] | ((cells[i * 2 + 1] & 3) << 8)
        char = ' '
        for font in fonts:
            if font <= tile < font + 96:
                char = chr(tile - font + 32)
        result += char
    return result.strip()


def board(session):
    return bytes(session.emu.read_memory(symbol('board'), 100))


def counts(session):
    cells = board(session)
    return (sum(c < 0xFE and not c & 0x10 for c in cells),
            sum(c < 0xFE and c & 0x10 != 0 for c in cells))


def main():
    with tempfile.TemporaryDirectory(prefix='feldmarschall-flow-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(directory)
        try:
            session.move_mouse(10, 10)
            session.shot(ROOT / 'build/test-shots/menu.png')
            field_map = read_vram(session, 0x8000, 60 * 256)
            palette = read_vram(session, 0x1FA00, 512)
            choose(session, '3')
            assert text(session, 9) == 'NO SAVED GAME', 'Continue needs GAME.DAT'
            choose(session, '2')
            assert text(session, 20, 12, 24) == "1  ATTACKER'S ADVANTAGE"
            assert read_vram(session, 0x8000, 60 * 256) == (ROOT / 'src/MNMAP.BIN').read_bytes()
            assert read_vram(session, 0x1FAE0, 32) == (ROOT / 'src/MNPAL.BIN').read_bytes()
            session.shot(ROOT / 'build/test-shots/game-settings.png')
            # Artwork must render pixel-for-pixel, without tile approximations.
            with Image.open(ROOT / 'build/test-shots/game-settings.png') as shot, Image.open(ROOT / 'build/preview/new-game-art.png') as art:
                for region in ((32, 8, 608, 136), (8, 340, 632, 416)):
                    assert shot.convert('RGB').crop(region).tobytes() == art.convert('RGB').crop(region).tobytes(), 'menu artwork differs from the exact asset'
            menu_tiles = (ROOT / 'src/MNL1TIL.BIN').read_bytes()
            assert read_vram(session, 0x10000, len(menu_tiles)) == menu_tiles

            choose(session, 'Return')
            assert read_vram(session, 0x8000, 60 * 256) == field_map, 'leaving settings must restore field artwork'
            assert read_vram(session, 0x1FA00, 512) == palette, 'leaving settings must restore the full palette'
            game_tiles = (ROOT / 'src/L1TILES.BIN').read_bytes()
            assert read_vram(session, 0x10000, len(game_tiles)) == game_tiles, 'leaving settings must restore piece tiles'
            assert text(session, 9) == 'DEPLOY YOUR ARMY'
            assert counts(session) == (0, 40), 'Play must not invent a player deployment'
            assert 'START' in text(session, 56, 0, 53)
            choose(session, 'Return')
            assert text(session, 9) == 'DEPLOY YOUR ARMY', 'incomplete Start must be disabled'
            assert counts(session) == (0, 40)
            choose(session, 'Escape')
            assert text(session, 20, 12, 24) == "1  ATTACKER'S ADVANTAGE"
            choose(session, 'Escape')
            choose(session, '1')
            assert text(session, 9) == 'MANAGE SETUPS'
            assert counts(session) == (0, 0)
            assert 'BACK' in text(session, 56, 0, 53) and 'START' not in text(session, 56, 0, 53)
            choose(session, 'Return')
            assert text(session, 11) == 'MAIN MENU', 'Back must work with an incomplete setup'
            choose(session, '1')
            choose(session, 'R')
            assert text(session, 9) == 'SETUP COMPLETE'
            original = board(session)[60:]
            assert counts(session) == (40, 0)
            choose(session, 'S')
            choose(session, 'Return')
            assert text(session, 9) == 'SETUP SAVED'
            saved = (directory / 'DEPLOY.DAT').read_bytes()
            assert saved[:8] == b'STRDEP01' and saved[24:64] == original
            session.shot(ROOT / 'build/test-shots/manage-setups.png')
            choose(session, 'N')
            assert counts(session) == (0, 0)
            choose(session, 'L')
            click(session, 300, 72)  # first saved setup, in the Yours column
            assert board(session)[60:] == original
            assert text(session, 9) == 'SETUP COMPLETE'
            choose(session, 'Return')
            assert text(session, 11) == 'MAIN MENU', 'setup management must not start a match'
            # Mouse entry into Play also goes through deployment, even for a complete setup.
            click(session, 160, 208)
            assert text(session, 20, 12, 24) == "1  ATTACKER'S ADVANTAGE"
            click(session, 490, 426)
            assert text(session, 9) == 'READY TO PLAY'
            assert board(session)[60:] == original and counts(session) == (40, 40)
            session.move_mouse(10, 10)
            session.shot(ROOT / 'build/test-shots/prepare-play.png')
            choose(session, 'Return')
            assert text(session, 9) == 'YOUR TURN'
            assert board(session)[60:] == original, 'match must use the approved arrangement'
            # Escape opens the game menu; a saved game continues from the main menu.
            choose(session, 'Escape')
            assert text(session, 21, 10, 34) == 'GAME MENU'
            session.shot(ROOT / 'build/test-shots/game-menu.png')
            position = board(session)
            choose(session, '2')
            assert text(session, 33, 10, 34) == 'GAME SAVED'
            assert (directory / 'GAME.DAT').read_bytes()[:8] == b'STRGAM01'
            choose(session, 'Escape')
            assert text(session, 21, 10, 34) == '', 'Escape resumes the game'
            assert text(session, 9) == 'YOUR TURN'
            choose(session, 'Escape')
            choose(session, '3')
            assert text(session, 11) == 'MAIN MENU'
            choose(session, '3')
            assert text(session, 9) == 'YOUR TURN'
            assert board(session) == position, 'the saved game must continue where it was saved'
            # Reduced legal position: a marshal can capture the adjacent enemy flag.
            # This exercises the real battle/game-over path without playing a long match.
            position = bytearray([0xFF] * 100)
            for lake in (42, 43, 52, 53, 46, 47, 56, 57):
                position[lake] = 0xFE
            position[99], position[41], position[31], position[0] = 11, 0, 0x1B, 0x10
            session.emu.write_memory(symbol('board'), position)
            session.run(['drag:76,196,76,156'])
            session.emu.advance(320)
            assert text(session, 9) == 'YOU WIN'
            choose(session, 'Return')
            assert text(session, 20, 12, 24) == "1  ATTACKER'S ADVANTAGE", 'new games must return to rules settings'
            choose(session, 'Return')
            assert text(session, 9) == 'READY TO PLAY'
            assert board(session)[60:] == original
            choose(session, 'Escape')
            assert text(session, 20, 12, 24) == "1  ATTACKER'S ADVANTAGE"
            choose(session, 'Escape')
            assert text(session, 11) == 'MAIN MENU'
        finally:
            session.close()
        session = start(directory)
        try:
            choose(session, '1')
            choose(session, 'L')
            click(session, 300, 72)
            assert board(session)[60:] == original, 'saved setup must load after restart'
            assert text(session, 9) == 'SETUP COMPLETE'
        finally:
            session.close()
    print('flow: manage/save/load, incomplete Start, approved setup, mouse entry and rematch passed')


if __name__ == '__main__':
    main()
