"""Two autonomous armies, private AI views, pause/no-save/resume and demo results."""
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from distribute import runtime_files
from test_colors import ROOT, start, choose, click, read_vram
from test_flow import symbol, text, board, counts
from test_variants import position, read, write


def pause(session):
    choose(session, 'Escape')
    assert text(session, 55, 0, 53) == 'GAME PAUSED'


def check_setups(session):
    cells = board(session)
    red = bytes(c & 15 for c in cells[60:])
    blue = bytes(cells[(3 - i // 10) * 10 + i % 10] & 15 for i in range(40))
    expected = Counter(dict(enumerate([1, 1, 2, 3, 4, 4, 4, 5, 8, 1, 6, 1])))
    assert Counter(red) == Counter(blue) == expected, 'invalid random army'
    assert red != blue, 'demo armies have identical home-oriented setups'
    assert red != bytes(c & 15 for c in cells[:40]), 'demo armies have identical screen layouts'
    return red, blue


def main():
    with tempfile.TemporaryDirectory(prefix='feldmarschall-demo-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(directory)
        try:
            # Save a player's prepared layout; demos must leave it intact.
            choose(session, '1')
            choose(session, 'R')
            prepared = board(session)[60:]
            choose(session, 'Escape')
            reset = symbol('ai_reset')
            session.emu.request('breakpoint', address=reset)
            click(session, 180, 316)  # sixth menu entry, Watch demo
            first_setups = check_setups(session)
            session.emu.request('breakpoint', action='remove', address=reset)
            session.emu.advance(1)
            assert read(session, 'view_show_all', 1) == b'\x01'
            # Observe eight real AI turns. Spectator visibility must never leak
            # enemy ranks to either AI, and own ranks must remain available.
            address = symbol('ai_move')
            session.emu.request('breakpoint', address=address)
            for i in range(8):
                assert session.emu.advance(600)['reason'] == 'breakpoint'
                assert text(session, 9) in ('RED COMPUTER', 'BLUE COMPUTER')
                cells = board(session)
                hidden_sides = {bool(c & 16) for c in cells if c < 254 and c & 15 == 12}
                assert len(hidden_sides) == 1, 'AI sees true ranks of unrevealed enemies'
                enemy = hidden_sides.pop()
                if i == 0:
                    first_enemy = enemy
                assert enemy == (first_enemy if i % 2 == 0 else not first_enemy), 'both computers must alternate'
                for cell in cells:
                    if cell < 254 and bool(cell & 16) == enemy and not cell & 32:
                        assert cell & 15 == 12, 'unrevealed enemy rank leaked'
                session.emu.request('breakpoint', action='remove', address=address)
                session.emu.advance(1)
                session.emu.request('breakpoint', address=address)
            session.emu.request('breakpoint', action='remove', address=address)
            pause(session)
            snapshot = board(session)
            assert all(c >= 254 or c & 15 < 12 for c in snapshot), 'AI did not restore truth'
            session.emu.advance(600)
            assert board(session) == snapshot, 'paused demo advanced'
            assert text(session, 24, 17, 24) == 'MUSIC ON', repr(text(session, 28, 7, 40))
            assert text(session, 28, 17, 24) == 'SOUND EFFECTS ON'
            assert text(session, 32, 17, 24) == 'QUIT TO MENU'
            assert not (directory / 'GAME.DAT').exists()
            choose(session, '2')  # sound replaces Save in demos
            assert read(session, 'sound_music_enabled', 1) == b'\0'
            assert not (directory / 'GAME.DAT').exists(), 'demo created a save'
            (directory / 'GAME.DAT').write_bytes(b'preserved saved game')
            choose(session, '3')
            assert read(session, 'sound_effects_enabled', 1) == b'\0'
            assert read(session, 'sound_music_enabled', 1) == b'\0'
            choose(session, '3')
            choose(session, '2')
            assert read(session, 'sound_effects_enabled', 1) == b'\x01'
            assert read(session, 'sound_music_enabled', 1) == b'\x01'
            assert (directory / 'GAME.DAT').read_bytes() == b'preserved saved game'
            choose(session, '1')
            session.emu.advance(300)
            assert board(session) != snapshot, 'resumed demo stopped playing'
            pause(session)
            choose(session, '4')
            choose(session, '1')
            assert board(session)[60:] == prepared, 'demo replaced prepared army'
            choose(session, 'Escape')

            # Both armies autonomously rescue their strongest casualty.
            session.emu.request('breakpoint', address=reset)
            choose(session, '6')
            assert check_setups(session) != first_setups, 'new demo reused both setups'
            session.emu.request('breakpoint', action='remove', address=reset)
            session.emu.advance(1)
            pause(session)
            position(session, {0: 255, 9: 0x1B, 10: 1, 80: 0x11, 99: 11})
            write(session, 'game_rules', [32])
            lost = bytearray(24)
            lost[0] = lost[12] = 1
            write(session, 'rules_lost', lost)
            write(session, 'rules_known_lost', lost)
            choose(session, '1')
            session.emu.advance(200)
            assert read(session, 'rules_rescues', 2) == b'\x01\x01', 'a demo rescue required human input'
            pause(session)
            choose(session, '4')

            # Deterministic flag capture, result review, and another demo.
            choose(session, '6')
            pause(session)
            position(session, {0: 0x1B, 9: 0x1A, 10: 0, 99: 11})
            write(session, 'game_rules', [0])
            choose(session, '1')
            session.emu.advance(300)
            assert 'RED WINS' in text(session, 12, 0, 80)
            assert text(session, 42, 0, 80) == 'RED CAPTURED THE BLUE FLAG'
            choose(session, '2')
            assert text(session, 9) == 'RED WINS'
            choose(session, 'space')
            session.emu.request('breakpoint', address=address)
            choose(session, '1')
            assert read(session, 'view_show_all', 1) == b'\x01'
            assert counts(session) == (40, 40)
            session.emu.request('breakpoint', action='remove', address=address)
            session.emu.advance(180)
            session.shot(ROOT / 'build/test-shots/demo.png')
            pause(session)
            choose(session, '4')
            # Ordinary play still waits for the player with Blue concealed.
            choose(session, '2')
            choose(session, 'Return')
            choose(session, 'Return')
            assert text(session, 9) == 'YOUR TURN'
            assert read(session, 'view_show_all', 1) == b'\0'
            snapshot = board(session)
            session.emu.advance(300)
            assert board(session) == snapshot
            print('demo: varied distinct legal setups, both AI views and turns, pause/no-save/resume, prepared setup, rescues, result/restart, normal play: ok')
        finally:
            session.emu.close()


if __name__ == '__main__':
    main()
