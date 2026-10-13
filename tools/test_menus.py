"""Menu states render visibly before activation; floating rules preserve VERA."""
import re
import shutil
import tempfile
from pathlib import Path
from distribute import runtime_files
from test_colors import ROOT, start, choose, read_vram
from test_variants import read
from test_flow import text


def constant(name):
    return int(re.search(r'#define '+name+r'\s+(\d+)', (ROOT/'src/gfx.h').read_text()).group(1))


def tile(session, col, row):
    data = read_vram(session, 0xC000+row*256+col*2, 2)
    return data[0] | ((data[1] & 3) << 8)


def main():
    with tempfile.TemporaryDirectory(prefix='feldmarschall-menus-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT/'src'/name, directory/name)
        session = start(directory)
        try:
            assert tile(session, 18, 13) == constant('L1_MENU_TITLE')
            assert tile(session, 14, 16) == constant('L1_MENU_RULE')
            assert text(session, 19, 17, 9) == 'SETUPS'
            assert text(session, 23, 17, 9) == 'SKIRMISH'
            assert text(session, 27, 17, 9) == 'LOAD GAME'
            session.move_mouse(180, 188)
            session.emu.advance(3)
            assert tile(session, 14, 22) == constant('L1_BUTTON_HOVER')
            backdrop = read_vram(session, 0x8000, 60*256)
            palette = read_vram(session, 0x1FA00, 512)
            session.button(True)
            assert text(session, 55, 0, 53) == 'CHOOSE AN OPTION', 'button activated before its press animation'
            assert tile(session, 14, 22) == constant('L1_BUTTON_PRESSED')
            session.shot(ROOT/'build/test-shots/menu-pressed.png')
            session.button(False)
            session.emu.advance(30)
            assert text(session, 9) == 'NEW GAME'
            assert tile(session, 18, 12) == constant('L1_NEW_TITLE')
            assert read_vram(session, 0x8000, 60*256) == backdrop
            assert read_vram(session, 0x1FA00, 512) == palette
            session.move_mouse(140, 160)
            session.button(True)
            assert tile(session, 38, 19) == constant('L1_TOGGLE_ON')
            assert read_vram(session, 0x1FA00+7*32+7*2, 2) == bytes([0xA4, 0x02]), 'toggle green lost during palette application'
            assert read(session, 'game_rules', 1) == b'\x01'
            session.shot(ROOT/'build/test-shots/rule-toggle.png')
            session.button(False)
            session.emu.advance(30)
            assert read(session, 'game_rules', 1) == b'\x01'
            assert tile(session, 38, 19) == constant('L1_TOGGLE_ON')
            session.move_mouse(324, 164)
            session.button(True)
            session.button(False)
            assert read(session, 'game_rules', 1) == b'\0'
            assert tile(session, 38, 19) == constant('L1_TOGGLE_OFF')
            choose(session, 'C')
            assert read(session, 'game_rules', 1) == b'\0'
            choose(session, 'Escape')
            assert read_vram(session, 0x8000, 60*256) == backdrop
            choose(session, '2')
            choose(session, 'Return')
            choose(session, 'R')
            choose(session, 'Return')
            choose(session, 'Escape')
            assert tile(session, 18, 14) == constant('L1_GAME_TITLE')
            assert tile(session, 14, 17) == constant('L1_MENU_RULE')
            before = read_vram(session, 0xC000, 60*256)
            session.move_mouse(180, 196)
            session.emu.advance(10)
            after = read_vram(session, 0xC000, 60*256)
            for row in range(60):
                for col in range(80):
                    if 14 <= col < 40 and (19 <= row < 22 or 23 <= row < 26):
                        continue
                    offset = row*256+col*2
                    assert before[offset:offset+2] == after[offset:offset+2], 'pause hover repainted unrelated GUI'
            session.button(True)
            assert tile(session, 14, 23) == constant('L1_BUTTON_PRESSED')
            session.shot(ROOT/'build/test-shots/pause-pressed.png')
            session.button(False)
            session.emu.advance(60)
            assert text(session, 40, 10, 34) == 'GAME SAVED'
            choose(session, '1')
            assert text(session, 9) == 'YOUR TURN'
            assert (ROOT/'src/L1TILES.BIN').stat().st_size//32 <= 1024
            assert 0x10000+(ROOT/'src/L1TILES.BIN').stat().st_size <= 0x18000
            print('menus: serif headings, highlight/press frames, delayed action, floating rules/palette, classic reset and VRAM limits: ok')
        finally:
            session.emu.close()


if __name__ == '__main__':
    main()
