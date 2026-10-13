"""Check how games end, through the developer scenarios (src/scenes/dev.c).

Usage:
  python3 tools/test_endings.py          (or: make test-endings)

Types DEV at the main menu, plays each scenario like a player would, and
checks exact result artwork, reasons, controls and restoration of the board
and selected palettes. Runs in a temporary runtime directory.
"""
import shutil
import tempfile
from pathlib import Path
from PIL import Image

from distribute import runtime_files
from test_colors import ROOT, start, choose, click, read_vram
from test_flow import text, board
from test_variants import drag

# Reason text is dynamic on layer 1; artwork and the large title are layer 0.
REASON = 42

# scenario key, Red's move (or None: Blue moves first), info plate, plate title, reason
ENDINGS = [
    ('1', None, 'OPPONENT WINS', 'DEFEAT', 'YOU HAVE NO MOVES LEFT'),
    ('2', (64, 54), 'YOU WIN', 'VICTORY', 'OPPONENT HAS NO MOVES LEFT'),
    ('3', (64, 54), 'DRAW', 'DRAW', 'NEITHER ARMY CAN MOVE'),
    ('4', (10, 0), 'YOU WIN', 'VICTORY', 'YOU CAPTURED THE ENEMY FLAG'),
    ('5', None, 'OPPONENT WINS', 'DEFEAT', 'OPPONENT CAPTURED YOUR FLAG'),
]


def plate(session, row):
    return text(session, row, 20, 40)


def result(session, title, reason, key):
    prefix, name = {'VICTORY': ('WIN', 'victory'), 'DEFEAT': ('LOSS', 'defeat'),
                    'DRAW': ('DRAW', 'draw')}[title]
    assert plate(session, REASON) == reason, f'scenario {key}: wrong reason'
    for resource, address in ((prefix+'TIL.BIN', 0), (prefix+'MAP.BIN', 0x8000),
                              ('ENDPAL.BIN', 0x1FA00+9*32)):
        expected = (ROOT / 'src' / resource).read_bytes()
        assert read_vram(session, address, len(expected)) == expected, resource
    assert read_vram(session, 0x1FA00, 2) == bytes(2), 'backdrop must be pure black'
    session.move_mouse(10, 10)
    session.emu.advance(2)
    shot = ROOT / f'build/test-shots/ending-{key}.png'
    session.shot(shot)
    with Image.open(shot) as actual, Image.open(ROOT / f'build/preview/ending-{name}.png') as expected:
        for region in ((152, 112, 488, 320), (200, 64, 440, 96)):
            assert actual.convert('RGB').crop(region).tobytes() == expected.convert('RGB').crop(region).tobytes(), 'artwork, frame or heading changed in emulator'
        assert actual.convert('RGB').getpixel((100, 100)) == (0, 0, 0)


def scenario(session, key):
    assert text(session, 9) == 'DEVELOPER', 'the developer scenarios are not listed'
    choose(session, key)


def main():
    with tempfile.TemporaryDirectory(prefix='feldmarschall-endings-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        # Exercise restoration of a non-default field, army palette and ranks.
        (directory / 'COLORS.DAT').write_bytes(b'CLR6'+bytes((3, 5, 1, 0xA5 ^ 3 ^ 5 ^ 1)))
        session = start(directory)
        try:
            assert text(session, 55, 0, 53) == 'CHOOSE AN OPTION'
            for key in 'DEV':
                session.press(key)
            session.emu.advance(30)
            assert text(session, 11) == 'TEST SCENARIOS'
            for key, move, info, title, reason in ENDINGS:
                field_map = read_vram(session, 0x8000, 60*256)
                palette = read_vram(session, 0x1FA00, 512)
                scenario(session, key)
                if move:
                    assert text(session, 9) == 'YOUR TURN', f'scenario {key} should start with Red'
                    drag(session, *move, wait=400)
                else:
                    session.emu.advance(400)    # Blue thinks, moves and its battle plays out
                result(session, title, reason, key)
                final_board = board(session)
                if key == '1':
                    # Mouse choice restores the board, palette and pieces exactly.
                    click(session, 300, 392)
                    assert text(session, 9) == info
                    assert read_vram(session, 0x8000, 60*256) == field_map
                    assert read_vram(session, 0x1FA00, 512) == palette
                    assert board(session) == final_board
                    session.move_mouse(10, 10)
                    choose(session, 'Space')
                    result(session, title, reason, key)
                    # Arrow selection and Enter support keyboard-only review.
                    choose(session, 'Down')
                    choose(session, 'Return')
                    assert text(session, 9) == info
                    choose(session, 'Space')
                    choose(session, '1')        # New game
                    assert text(session, 20, 12, 24) == "ATTACKER'S ADVANTAGE"
                    choose(session, 'Escape')   # Back to the menu
                else:
                    choose(session, 'Escape')   # Main menu, still listing the scenarios
                    assert read_vram(session, 0x8000, 60*256) == field_map
                    assert read_vram(session, 0x1FA00, 512) == palette
                assert text(session, 11) == 'TEST SCENARIOS'

            # Rescue: Red's major reaches Blue's back row.
            scenario(session, '6')
            drag(session, 14, 4)
            assert text(session, 9) == 'RESCUE A PIECE'
            choose(session, 'Return')           # skip it; Blue moves
            session.emu.advance(200)
            assert text(session, 9) == 'YOUR TURN'
            choose(session, 'Escape')
            choose(session, '3')                # quit to the menu
            choose(session, 'Escape')           # back to the main menu
            assert text(session, 55, 0, 53) == 'CHOOSE AN OPTION'
        finally:
            session.close()
    print(f'endings: {len(ENDINGS)} illustrated outcomes, exact artwork/frame, black backdrop, mouse/keyboard controls, board/palette restoration, new game and rescue passed')


if __name__ == '__main__':
    main()
