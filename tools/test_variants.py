"""Check Masters options and information disclosure in the real X16 build."""
import shutil
import tempfile
from pathlib import Path
from distribute import runtime_files
from test_colors import ROOT, start, choose, click, read_vram
from test_flow import symbol, text, board
from autoplay import centre


def read(session, name, n):
    return bytes(session.emu.read_memory(symbol(name), n))


def write(session, name, data):
    session.emu.write_memory(symbol(name), bytes(data))


def position(session, pieces):
    cells = bytearray([0xFF] * 100)
    for sq in (42, 43, 52, 53, 46, 47, 56, 57):
        cells[sq] = 0xFE
    cells[99], cells[0], cells[9] = 11, 0x1B, 0x18
    for sq, cell in pieces.items():
        cells[sq] = cell
    write(session, 'board', cells)
    # Keep the fixture's display in sync with its injected board position.
    tilemap = bytearray(read_vram(session, 0xC000, 60 * 256))
    for sq, cell in enumerate(cells):
        for y in range(5):
            for x in range(5):
                offset = (2 + sq // 10 * 5 + y) * 256 + (2 + sq % 10 * 5 + x) * 2
                if cell < 0xFE:
                    token = 12 if cell & 0x10 else cell & 15
                    tile = 206 + token * 25 + y * 5 + x
                    attr = (2 if cell & 0x10 else 1) << 4 | tile >> 8
                else:
                    tile = 1 if x == y == 0 else 2 if y == 0 else 3 if x == 0 else 0
                    attr = 0x60 if tile else 0
                tilemap[offset:offset + 2] = bytes((tile & 255, attr))
    for offset in range(0, len(tilemap), 4096):
        session.emu.write_memory(0xC000 + offset, tilemap[offset:offset + 4096], space='vram')


def drag(session, source, destination, wait=320):
    x, y = centre(source)
    u, v = centre(destination)
    session.run([f'drag:{x},{y},{u},{v}'])
    session.emu.advance(wait)


def new_match(session, keys):
    choose(session, 'Escape')       # the game menu, or the main menu after a game
    choose(session, '3')            # quit to the main menu (there: no saved game)
    choose(session, '2')
    choose(session, 'C')
    for key in keys:
        choose(session, key)
    choose(session, 'Return')
    choose(session, 'R')
    choose(session, 'Return')
    assert text(session, 9) == 'YOUR TURN'
    assert read(session, 'rules_rescues', 2) == b'\0\0'
    assert read(session, 'rules_lost', 24) == bytes(24)


def main():
    with tempfile.TemporaryDirectory(prefix='feldmarschall-variants-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(directory)
        try:
            choose(session, '2')
            assert read(session, 'game_rules', 1) == b'\0'
            click(session, 140, 256)  # Moving Bombs enables Exploding Bombs.
            assert read(session, 'game_rules', 1) == b'\x0c'
            choose(session, '3')
            assert read(session, 'game_rules', 1) == b'\0', 'disabling explosions disables moving bombs'
            choose(session, 'Down')
            choose(session, 'space')
            assert read(session, 'game_rules', 1) == b'\x0c', 'arrow/Space controls must work'
            choose(session, 'Escape')
            new_match(session, '1')
            position(session, {60: 0, 50: 0x10})
            drag(session, 60, 50)
            assert board(session)[50] & 15 == 0 and not board(session)[50] & 0x10
            assert read(session, 'rules_lost', 24)[12] == 1, 'equal rank attacker survives'

            new_match(session, '2')
            position(session, {60: 0, 50: 0x16})
            drag(session, 60, 50, 10)
            message = text(session, 57, 0, 37)
            assert 'SERGEANT' not in message and 'DEFENDER' in message, message
            # The defender token in the battle bar must be its hidden back.
            hidden_tile = 206 + 12 * 25
            tile = read_vram(session, 0xC000 + 54 * 256 + 46 * 2, 2)
            assert tile[0] | ((tile[1] & 3) << 8) == hidden_tile
            session.emu.advance(310)
            assert read(session, 'rules_lost', 24)[12 + 6] == 1
            assert read(session, 'rules_known_lost', 24)[12 + 6] == 0
            tray = read(session, 'tray', 40)
            assert tray[0] == 0x1C and all(c == 0xFF for c in tray[1:]), 'hidden casualty must not leak through rank-specific tray slots'

            new_match(session, '2')
            position(session, {60: 8, 50: 0x16})
            drag(session, 60, 50, 10)
            assert 'SERGEANT' in text(session, 57, 0, 37), 'Scout must disclose the defender'
            session.emu.advance(310)
            assert board(session)[50] & 0x20

            new_match(session, '3')
            position(session, {60: 0, 50: 0x1A})
            drag(session, 60, 50)
            assert board(session)[60] == board(session)[50] == 0xFF
            assert read(session, 'rules_lost', 24)[0] == 1
            assert read(session, 'rules_lost', 24)[22] == 1

            new_match(session, '4')
            position(session, {60: 10})
            drag(session, 60, 50)
            assert board(session)[50] & 15 == 10, 'player can move a bomb'
            position(session, {60: 10, 50: 0x16})
            drag(session, 60, 50)
            assert board(session)[60] == 10, 'bomb may never attack'

            new_match(session, '5')
            position(session, {10: 11, 99: 0xFF, 0: 0xFF, 1: 0x1B})
            drag(session, 10, 0)
            assert text(session, 9) == 'YOU WIN', 'flag reaching enemy back row ends the game'
            choose(session, 'Return')
            assert text(session, 20, 12, 24) == "1  ATTACKER'S ADVANTAGE"
            assert read(session, 'game_rules', 1) == b'\x10', 'rematch retains session preferences'
            choose(session, 'Return')
            choose(session, 'Return')

            new_match(session, '6')
            position(session, {10: 4, 0: 0xFF, 1: 0x1B})
            lost = bytearray(24)
            lost[0] = 1
            write(session, 'rules_lost', lost)
            drag(session, 10, 0)
            assert text(session, 9) == 'RESCUE A PIECE'
            session.shot(ROOT / 'docs/rescue.png')
            click(session, 452, 172)  # Captured Marshal.
            click(session, *centre(60))
            assert board(session)[60] & 15 == 0 and not board(session)[60] & 0x10
            assert read(session, 'rules_rescues', 2)[0] == 1
            assert read(session, 'rules_lost', 24)[0] == 0
            # The computer can rescue too, without a player dialog.
            new_match(session, '6')
            position(session, {60: 6, 89: 0x14, 9: 0xFF, 99: 0xFF, 98: 11})
            lost = bytearray(24)
            lost[12] = 1
            write(session, 'rules_lost', lost)
            drag(session, 60, 50)
            assert read(session, 'rules_rescues', 2)[1] == 1
            assert any(c & 15 == 0 and c & 0x10 for c in board(session)[:40] if c < 0xFE)
            # A non-default field and army palette must survive the illustrated menu.
            choose(session, 'Escape')
            choose(session, '3')  # Quit to the main menu.
            choose(session, '4')
            choose(session, '4')  # Ivory Paper.
            choose(session, 'Tab')
            choose(session, '3')  # Forest / Ivory armies.
            choose(session, 'Return')
            field_map = read_vram(session, 0x8000, 60 * 256)
            palette = read_vram(session, 0x1FA00, 512)
            choose(session, '2')
            assert read_vram(session, 0x8000, 60 * 256) == (ROOT / 'src/MNMAP.BIN').read_bytes()
            choose(session, 'Return')
            assert read_vram(session, 0x8000, 60 * 256) == field_map
            assert read_vram(session, 0x1FA00, 512) == palette
        finally:
            session.close()
    print('variants: settings, tie wins, silent disclosure/tray, Scout exception, bombs, flag victory and both rescues passed')


if __name__ == '__main__':
    main()
