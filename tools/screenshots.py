"""Regenerate every screenshot in docs/ from the game in the AgentBridge emulator.

Usage:
  python3 tools/screenshots.py [--out docs] [--emu ...] [--rom ...]
  (or: make screenshots)

Plays through the game once, in a temporary copy of the runtime files so the
player's saves stay untouched, and captures each screen on the way. Before
every capture the screen's text is read back from VRAM, so a change in the
game's flow stops the script instead of producing a wrong picture. The
emulator runs frame by frame, so the same game gives the same screenshots;
a file is only rewritten when its pixels change.
"""
import argparse
import random
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from autoplay import FLAG, LAKE, BLUE, centre, red_moves  # noqa: E402
from distribute import runtime_files  # noqa: E402
from screenshot import Session, X16Agent  # noqa: E402
from test_colors import choose, click  # noqa: E402
from test_flow import board, counts, symbol, text, wait_for_next_red_turn  # noqa: E402
from test_variants import drag, new_match, position, write  # noqa: E402

ROMS = [ROOT.parent / 'emulator/rom.bin', ROOT.parent / 'emulator-win/rom.bin']


class Shots:
    """Captures into a scratch directory, then updates docs/ where pixels differ."""

    def __init__(self, session, scratch, out):
        self.session, self.scratch, self.out = session, scratch, out
        self.updated, self.unchanged = [], []

    def __call__(self, name, *, plate=None, info=None, row=None):
        if info is not None:
            assert text(self.session, 9) == info, f'{name}: info plate reads {text(self.session, 9)!r}, not {info!r}'
        if row is not None:
            line, first, width, expected = row
            assert text(self.session, line, first, width) == expected, \
                f'{name}: row {line} reads {text(self.session, line, first, width)!r}, not {expected!r}'
        fresh = self.scratch / name
        result = self.session.emu.screenshot(fresh.resolve())
        assert result['captured'], result
        target = self.out / name
        if target.exists():
            with Image.open(target) as old, Image.open(fresh) as new:
                if old.size == new.size and old.convert('RGB').tobytes() == new.convert('RGB').tobytes():
                    self.unchanged.append(name)
                    return
        shutil.copyfile(fresh, target)
        self.updated.append(name)
        print(f'updated {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}')


def start(emu, rom, directory):
    session = Session.__new__(Session)
    session.emu = X16Agent(emu, rom, fsroot=directory, options=['-prg', str(directory / 'FELDMARS.PRG'), '-run'])
    session.buttons = 0
    session.emu.advance(360)
    return session


def pin_dice(session, frame):
    """Set the frame counter that seeds the dice when the next screen opens.

    Disk loads can take a frame more or less when the host is busy, which
    would change random armies and the computer's moves.
    """
    session.emu.write_memory(symbol('input') + 7, bytes((frame & 255, frame >> 8)))


def play(session, turns, seed):
    """Red makes random legal moves by dragging, as in tools/autoplay.py."""
    rng = random.Random(seed)
    shuttle = (None, None, 0)
    for _ in range(turns):
        before = board(session)
        previous_turn = text(session, 11)
        moves = red_moves(before, shuttle)
        attacks = [m for m in moves if before[m[1]] != 0xFF]
        move = rng.choice(attacks if attacks and rng.random() < 0.5 else moves)
        last_src, last_dst, count = shuttle
        shuttle = (move[0], move[1], count + 1 if count and move == (last_dst, last_src) else 1)
        drag(session, *move)
        assert wait_for_next_red_turn(session, previous_turn), 'game ended before the planned screenshot'
        after = board(session)
        assert after != before, f'the move {move} changed nothing'
        flags = [c & BLUE for c in after if c < LAKE and c & 15 == FLAG]
        assert len(flags) == 2, 'a flag fell: choose another --seed or fewer turns'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--emu', default=str(ROOT.parent / 'x16-emulator/build/x16emu'))
    parser.add_argument('--rom', default=str(next((r for r in ROMS if r.exists()), ROMS[0])))
    parser.add_argument('--out', default=str(ROOT / 'docs'))
    parser.add_argument('--turns', type=int, default=14, help='moves played before docs/play.png')
    parser.add_argument('--seed', type=int, default=3, help='seed of those moves')
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix='feldmarschall-shots-') as tmp:
        directory, scratch = Path(tmp) / 'runtime', Path(tmp) / 'shots'
        directory.mkdir()
        scratch.mkdir()
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(args.emu, args.rom, directory)
        shot = Shots(session, scratch, out)
        try:
            shot('title.png')
            session.press('Return')
            session.emu.advance(180)
            # The main menu and About.
            session.move_mouse(10, 10)
            shot('menu.png', row=(55, 0, 53, 'CHOOSE AN OPTION'))
            choose(session, '5')
            shot('about.png')
            choose(session, 'Escape')

            # The empty pre-game deployment shows the whole layout.
            choose(session, '2')
            choose(session, 'Return')
            session.move_mouse(150, 236)
            shot('board-layout.png', info='DEPLOY YOUR ARMY')
            choose(session, 'Escape')
            choose(session, 'Escape')

            # Manage setups: drag, load, save.
            pin_dice(session, 1000)
            choose(session, '1')
            assert text(session, 9) == 'MANAGE SETUPS'
            session.run(['drag:452,172,196,356', 'drag:492,172,236,356', 'move:533,412', 'down', 'move:300,322', 'wait:3'])
            shot('deploy-drag.png')
            session.run(['up', 'wait:3'])
            choose(session, 'L')
            session.run(['move:96,108', 'wait:5'])
            shot('deploy-load.png')
            session.run(['down', 'wait:2', 'up', 'wait:5'])
            assert counts(session)[0] == 40, 'a built-in deployment was not loaded'
            choose(session, 'S')
            session.run(['Backspace'] * 16 + ['M', 'Y', 'Space', 'F', 'O', 'R', 'T', 'wait:3'])
            shot('deploy-save.png')
            choose(session, 'Escape')
            choose(session, 'R')
            choose(session, 'S')
            choose(session, 'Return')
            shot('manage-setups.png', info='SETUP SAVED')
            choose(session, 'Return')

            # Play: rules, the approved setup, a few moves and the game menu.
            choose(session, '2')
            shot('game-settings.png', row=(20, 12, 24, "ATTACKER'S ADVANTAGE"))
            choose(session, 'Return')
            session.move_mouse(10, 10)
            shot('prepare-play.png', info='READY TO PLAY')
            pin_dice(session, 2000)
            choose(session, 'Return')
            play(session, args.turns, args.seed)
            shot('play.png', info='YOUR TURN')
            choose(session, 'Escape')
            shot('game-menu.png', row=(55, 0, 53, 'GAME PAUSED'))
            choose(session, '1')

            # Rescue: a captured Marshal, and a Major on Blue's back row.
            new_match(session, '6')
            position(session, {10: 4, 0: 0xFF, 1: 0x1B})
            lost = bytearray(24)
            lost[0] = 1
            write(session, 'rules_lost', lost)
            drag(session, 10, 0)
            shot('rescue.png', info='RESCUE A PIECE')
            choose(session, 'Return')
            session.emu.advance(320)
            choose(session, 'Escape')
            choose(session, '3')

            # The end of a game: the developer scenario where Blue takes Red's last mover.
            for key in 'DEV':
                session.press(key)
            choose(session, '1')
            session.emu.advance(400)
            session.move_mouse(330, 300)
            shot('game-over.png', row=(42, 20, 40, 'YOU HAVE NO MOVES LEFT'))
            choose(session, 'Escape')       # the scenarios
            choose(session, 'Escape')       # the main menu

            # Both computer armies are face up for spectators.
            write(session, 'game_rules', [0])
            pin_dice(session, 1000)
            choose(session, '6')
            session.move_mouse(420, 420)
            shot('demo.png')
            choose(session, 'Escape')
            choose(session, '4')

            # Options last, since they change the colors of every other screen.
            choose(session, '4')
            click(session, 500, 224)    # Polished Tiles
            click(session, 500, 328)    # Mint / Rose
            session.move_mouse(420, 420)
            shot('options.png')
        finally:
            session.close()
    print(f'screenshots: {len(shot.updated)} updated, {len(shot.unchanged)} unchanged')


if __name__ == '__main__':
    main()
