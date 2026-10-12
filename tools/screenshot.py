"""Boot FELDMARS.PRG in the X16 AgentBridge emulator and capture screenshots.

Usage:
  python3 tools/screenshot.py [--out build/screenshot.png] [--keys "Tab ..."]

Keys are SDL key names separated by spaces. Special tokens:
  wait:N            advance N frames
  shot:PATH         capture a screenshot
  move:X,Y          move the mouse pointer to screen pixel (X, Y)
  down / up         press / release the left mouse button
  drag:X,Y,X2,Y2    press at (X, Y), move to (X2, Y2) in steps, release
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'x16-emulator/api/python'))
from x16agent import X16Agent  # noqa: E402


class Session:
    def __init__(self, emu, rom):
        fsroot = ROOT / 'src'
        self.emu = X16Agent(emu, rom, fsroot=fsroot,
                            options=['-prg', str(fsroot / 'FELDMARS.PRG'), '-run'])
        self.buttons = 0

    def press(self, key):
        self.emu.request('key', key=key, down=True)
        self.emu.advance(3)
        self.emu.request('key', key=key, down=False)
        self.emu.advance(3)

    def read_mouse(self):
        # the KERNAL keeps sprite 0 (the pointer) at the mouse position
        data = self.emu.read_memory(0x1FC02, 4, space='vram')
        return data[0] | data[1] << 8, data[2] | data[3] << 8

    def move_mouse(self, x, y, step=255):
        """Steer the relative mouse until the KERNAL pointer reaches (x, y)."""
        for _ in range(200):
            cx, cy = self.read_mouse()
            dx, dy = x - cx, y - cy
            if dx == 0 and dy == 0:
                return
            self.emu.request('mouse', dx=max(-step, min(step, dx)), dy=max(-step, min(step, dy)),
                             buttons=self.buttons)
            self.emu.advance(2)
        raise RuntimeError(f'mouse did not reach {(x, y)}')

    def button(self, down):
        self.buttons = 1 if down else 0
        self.emu.request('mouse', buttons=self.buttons)
        self.emu.advance(3)

    def shot(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        result = self.emu.screenshot(path.resolve())
        assert result['captured'], result
        print(f'saved {path}')

    def run(self, tokens):
        for token in tokens:
            if token.startswith('wait:'):
                self.emu.advance(int(token[5:]))
            elif token.startswith('shot:'):
                self.shot(token[5:])
            elif token.startswith('move:'):
                self.move_mouse(*(int(v) for v in token[5:].split(',')))
            elif token in ('down', 'up'):
                self.button(token == 'down')
            elif token.startswith('drag:'):
                x0, y0, x1, y1 = (int(v) for v in token[5:].split(','))
                self.move_mouse(x0, y0)
                self.button(True)
                self.move_mouse(x1, y1, step=12)    # a hand-paced drag
                self.button(False)
            else:
                self.press(token)

    def close(self):
        self.emu.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--emu', default=str(ROOT.parent / 'x16-emulator/build/x16emu'))
    roms = [ROOT.parent / 'emulator/rom.bin', ROOT.parent / 'emulator-win/rom.bin']
    parser.add_argument('--rom', default=str(next((r for r in roms if r.exists()), roms[0])))
    parser.add_argument('--out', default=str(ROOT / 'build/screenshot.png'))
    parser.add_argument('--keys', default='')
    parser.add_argument('--boot', type=int, default=240, help='frames to boot and load')
    args = parser.parse_args()

    session = Session(args.emu, args.rom)
    try:
        session.emu.advance(args.boot)
        session.run(args.keys.split())
        session.shot(args.out)
    finally:
        session.close()


if __name__ == '__main__':
    main()
