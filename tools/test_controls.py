"""Menu input ownership and controller-as-pointer integration in the real game.

The emulator API has no controller injection. A one-byte RTS replaces only
the JOYSTICK_GET wrapper in this temporary process; raw A/X/Y-equivalent
controller states feed the production movement, edge, click and drag logic.
No runtime files or player saves are modified.
"""
import shutil
import tempfile
from pathlib import Path

from distribute import runtime_files
from test_colors import ROOT, start, choose, click
from test_flow import text, symbol, board
from test_variants import position


class Pad:
    def __init__(self, session):
        self.session = session
        self.emu = session.emu
        self.address = symbol('input_poll_pad')
        self.original = self.emu.read_memory(self.address, 1)
        self.emu.request('breakpoint', address=symbol('input_read'))
        assert self.emu.advance(3)['reason'] == 'breakpoint'
        self.emu.write_memory(self.address, b'\x60')
        self.state()
        self.emu.request('breakpoint', action='remove', address=symbol('input_read'))
        self.emu.advance(3)

    def state(self, low=0, high=0, present=True):
        for name, value in (('pad_low', low ^ 255), ('pad_high', high ^ 255),
                             ('pad_present', 0 if present else 255)):
            self.emu.write_memory(symbol(name), bytes([value]))

    def position(self):
        data = self.emu.read_memory(symbol('input'), 4)
        return int.from_bytes(data[:2], 'little'), int.from_bytes(data[2:], 'little')

    def go(self, x, y, held=False):
        for _ in range(1000):
            px, py = self.position()
            dx, dy = x-px, y-py
            if abs(dx) <= 3 and abs(dy) <= 3:
                self.state(high=128 if held else 0)
                self.emu.advance(3)
                return
            low = (1 if dx > 3 else 2 if dx < -3 else 0) | (4 if dy > 3 else 8 if dy < -3 else 0)
            distances = [abs(d) for d in (dx, dy) if abs(d) > 3]
            high = 128 if held else 0
            if min(distances) < 16:
                high |= 64  # X: fine positioning
            elif min(distances) > 32:
                low |= 64   # Y: fast travel
            self.state(low, high)
            self.emu.advance(1)
        raise AssertionError(f'controller pointer never reached {(x,y)}; at {self.position()}')

    def click(self):
        self.state(high=128)
        self.emu.advance(4)
        self.state()
        self.emu.advance(180)

    def back(self):
        self.state(low=128)
        self.emu.advance(4)
        self.state()
        self.emu.advance(180)

    def start(self):
        self.state(low=16)
        self.emu.advance(4)
        self.state()
        self.emu.advance(180)

    def close(self):
        self.state(present=False)
        self.emu.advance(4)
        self.emu.write_memory(self.address, self.original)


def menu_keyboard(session):
    session.move_mouse(180, 156)  # park over Manage setups
    session.emu.advance(10)
    assert text(session, 19, 15, 1) == '>'
    choose(session, 'Down')
    assert text(session, 23, 15, 1) == '>', 'stationary mouse undid keyboard selection'
    choose(session, 'Return')
    assert text(session, 20, 12, 24) == "ATTACKER'S ADVANTAGE"
    # A stationary pointer over rule 1 must not undo keyboard rule selection.
    session.move_mouse(120, 160)
    session.emu.advance(10)
    choose(session, 'Down')
    assert text(session, 24, 11, 1) == '>'
    choose(session, 'Escape')
    # Real pointer movement takes selection back; a click works immediately.
    session.move_mouse(180, 252)
    session.emu.advance(10)
    assert text(session, 31, 15, 1) == '>'
    click(session, 180, 252)
    assert text(session, 9) == 'APPEARANCE OPTIONS'
    assert text(session, 57, 0, 53) == ''
    choose(session, 'Escape')
    choose(session, '1')
    choose(session, 'L')
    session.move_mouse(70, 144)
    session.emu.advance(10)
    first = text(session, 11)
    choose(session, 'Down')
    assert text(session, 11) != first, 'stationary mouse undid load-list navigation'
    choose(session, 'Escape')
    choose(session, 'Escape')
    # Pause menu selection and Enter must remain independent of parked pointer.
    choose(session, '2')
    choose(session, 'Return')
    choose(session, 'R')
    choose(session, 'Return')
    click(session, 40, 468)  # the visible Menu action below the move/battle text
    assert text(session, 55, 0, 53) == 'GAME PAUSED'
    session.move_mouse(180, 160)
    session.emu.advance(10)
    choose(session, 'Down')
    assert text(session, 24, 15, 1) == '>'
    choose(session, 'Return')
    assert text(session, 40, 10, 34) == 'GAME SAVED'
    assert text(session, 32, 17, 24) == 'MUSIC ON'
    choose(session, '4')
    assert text(session, 32, 17, 24) == 'MUSIC OFF'
    click(session, 180, 256)
    assert text(session, 32, 17, 24) == 'MUSIC ON'
    click(session, 180, 288)
    assert text(session, 36, 17, 24) == 'SOUND EFFECTS OFF'
    assert text(session, 32, 17, 24) == 'MUSIC ON'
    choose(session, '5')
    assert text(session, 36, 17, 24) == 'SOUND EFFECTS ON'
    choose(session, '3')


def controller(session):
    pad = Pad(session)
    try:
        # Clamp all edges without letting the physical mouse snap the pointer back.
        session.move_mouse(10, 10)
        pad.state(low=10)  # up+left
        pad.emu.advance(30)
        assert pad.position() == (0, 0)
        pad.state(low=5 | 64)  # down+right, fast
        pad.emu.advance(120)
        assert pad.position() == (639, 479)
        pad.state()
        pad.emu.advance(10)
        assert pad.position() == (639, 479), 'mouse state snapped back after pad release'
        # Controller-only main-menu click, deployment pickup and drag.
        pad.go(180, 156)
        pad.click()
        assert text(session, 9) in ('MANAGE SETUPS', 'SETUP COMPLETE'), f'pad menu click: {text(session, 9)!r}, {text(session, 11)!r}, position={pad.position()}'
        choose(session, 'N')  # fixture: empty the setup saved by the keyboard test
        pad.go(452, 172)
        pad.state(high=128)
        pad.emu.advance(4)
        pad.go(36, 276, held=True)
        pad.state()
        pad.emu.advance(10)
        assert board(session)[60] == 0, 'gamepad drag did not place the Marshal'
        assert text(session, 11) == '39 TO PLACE'
        # Mouse and pad share the cursor: genuine mouse movement still works.
        session.move_mouse(100, 100)
        session.emu.advance(5)
        assert pad.position() == (100, 100)
        # B is edge-triggered; holding it must not back out of several scenes.
        pad.state(low=128)
        pad.emu.advance(180)
        assert text(session, 55, 0, 53) == 'CHOOSE AN OPTION'
        pad.emu.advance(180)
        assert text(session, 55, 0, 53) == 'CHOOSE AN OPTION'
        pad.state()
        pad.emu.advance(4)
        pad.go(180, 188)
        pad.click()
        assert text(session, 20, 12, 24) == "ATTACKER'S ADVANTAGE"
        pad.state(low=16)
        pad.emu.advance(180)
        assert text(session, 9) == 'DEPLOY YOUR ARMY'
        pad.emu.advance(180)
        assert text(session, 9) == 'DEPLOY YOUR ARMY', 'held Start repeated across scenes'
        pad.state()
        pad.emu.advance(4)
        pad.go(280, 452)  # Random deployment button
        pad.click()
        assert text(session, 9) == 'READY TO PLAY'
        pad.start()
        assert text(session, 9) == 'YOUR TURN'
        position(session, {60: 6, 9: 0x16})
        pad.go(36, 276)
        pad.state(high=128)
        pad.emu.advance(4)
        pad.go(36, 236, held=True)
        pad.state()
        pad.emu.advance(8)
        assert board(session)[50] & 15 == 6 and not board(session)[50] & 16, 'gamepad could not move a piece during play'
        pad.go(40, 468)
        pad.click()
        assert text(session, 55, 0, 53) == 'GAME PAUSED'
        pad.go(200, 224)
        pad.click()
        assert text(session, 55, 0, 53) == 'CHOOSE AN OPTION'
        # Disconnection releases a drag safely, and keyboard remains usable.
        pad.go(180, 156)
        pad.click()
        choose(session, 'N')
        pad.go(452, 172)
        pad.state(high=128)
        pad.emu.advance(4)
        pad.state(present=False)
        pad.emu.advance(10)
        choose(session, 'Escape')
        assert text(session, 55, 0, 53) == 'CHOOSE AN OPTION'
    finally:
        pad.close()


def main():
    assert '#define APP_VERSION "v0.2.0"' in (ROOT / 'src/app_info.h').read_text()
    with tempfile.TemporaryDirectory(prefix='feldmarschall-controls-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(directory)
        try:
            menu_keyboard(session)
            controller(session)
        finally:
            session.close()
    print('controls: keyboard/pointer ownership, load/rule/pause menus, visible actions, gamepad movement/click/drag, Start/B edges, mouse handoff and disconnect passed')


if __name__ == '__main__':
    main()
