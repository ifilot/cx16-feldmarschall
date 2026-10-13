"""Check how games end, through the developer scenarios (src/scenes/dev.c).

Usage:
  python3 tools/test_endings.py          (or: make test-endings)

Types DEV at the main menu, plays each scenario like a player would, and
checks the info plate and the result plate: who won, why, and that the
plate's choices work. Runs in a temporary runtime directory.
"""
import shutil
import tempfile
from pathlib import Path

from distribute import runtime_files
from test_colors import ROOT, start, choose
from test_flow import text
from test_variants import drag

# the result plate (PAUSE_* in src/scenes/play.c)
PLATE_COL, PLATE_W, TITLE, REASON = 7, 40, 21, 23

# scenario key, Red's move (or None: Blue moves first), info plate, plate title, reason
ENDINGS = [
    ('1', None, 'OPPONENT WINS', 'DEFEAT', 'YOU HAVE NO MOVES LEFT'),
    ('2', (64, 54), 'YOU WIN', 'VICTORY', 'OPPONENT HAS NO MOVES LEFT'),
    ('3', (64, 54), 'DRAW', 'DRAW', 'NEITHER ARMY CAN MOVE'),
    ('4', (10, 0), 'YOU WIN', 'VICTORY', 'YOU CAPTURED THE ENEMY FLAG'),
    ('5', None, 'OPPONENT WINS', 'DEFEAT', 'OPPONENT CAPTURED YOUR FLAG'),
]


def plate(session, row):
    return text(session, row, PLATE_COL, PLATE_W)


def scenario(session, key):
    assert text(session, 9) == 'DEVELOPER', 'the developer scenarios are not listed'
    choose(session, key)


def main():
    with tempfile.TemporaryDirectory(prefix='feldmarschall-endings-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(directory)
        try:
            assert text(session, 11) == 'MAIN MENU'
            for key in 'DEV':
                session.press(key)
            session.emu.advance(30)
            assert text(session, 11) == 'TEST SCENARIOS'
            for key, move, info, title, reason in ENDINGS:
                scenario(session, key)
                if move:
                    assert text(session, 9) == 'YOUR TURN', f'scenario {key} should start with Red'
                    drag(session, *move, wait=400)
                else:
                    session.emu.advance(400)    # Blue thinks, moves and its battle plays out
                assert (text(session, 9), plate(session, TITLE), plate(session, REASON)) == (info, title, reason), \
                    f'scenario {key}: {text(session, 9)!r}, {plate(session, TITLE)!r}, {plate(session, REASON)!r}'
                session.shot(ROOT / f'build/test-shots/ending-{key}.png')
                if key == '1':
                    # View the board hides the plate; Space brings it back.
                    choose(session, '2')
                    assert plate(session, TITLE) == '' and text(session, 9) == info
                    choose(session, 'Space')
                    assert plate(session, TITLE) == title
                    choose(session, '1')        # New game
                    assert text(session, 20, 12, 24) == "1  ATTACKER'S ADVANTAGE"
                    choose(session, 'Escape')   # Back to the menu
                else:
                    choose(session, 'Escape')   # Main menu, still listing the scenarios
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
            assert text(session, 11) == 'MAIN MENU'
        finally:
            session.close()
    print(f'endings: {len(ENDINGS)} endings with their result plates, view board, new game and rescue passed')


if __name__ == '__main__':
    main()
