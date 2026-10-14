"""Difficulty selection, saved-game compatibility, and real banked AI use."""
import shutil
import tempfile
from pathlib import Path
from distribute import runtime_files
from test_colors import ROOT, start, choose, click, read_vram
from test_variants import read, write
from test_flow import text, symbol


def checksum(data):
    value = 0x5713
    for byte in data:
        value = ((value << 5) ^ (value >> 11) ^ byte) & 0xffff
    return value.to_bytes(2, 'little')


def main():
    with tempfile.TemporaryDirectory(prefix='feldmarschall-ai-levels-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(directory)
        try:
            choose(session, '2')
            assert read(session, 'ai_difficulty', 1) == b'\x01'
            assert text(session, 45, 59, 12) == 'NORMAL'
            backdrop = read_vram(session, 0x8000, 60 * 256)
            palette = read_vram(session, 0x1FA00, 512)
            click(session, 490, 360)
            assert read(session, 'ai_difficulty', 1) == b'\x02'
            assert text(session, 45, 59, 12) == 'HARD'
            click(session, 490, 360)
            assert read(session, 'ai_difficulty', 1) == b'\0'
            choose(session, 'Right')
            assert read(session, 'ai_difficulty', 1) == b'\x01'
            choose(session, 'Left')
            assert read(session, 'ai_difficulty', 1) == b'\0'
            choose(session, 'Left')
            assert read(session, 'ai_difficulty', 1) == b'\x02'
            choose(session, 'C')
            assert read(session, 'game_rules', 1) == b'\0'
            assert read(session, 'ai_difficulty', 1) == b'\x02', 'Classic rules must preserve difficulty'
            assert read_vram(session, 0x8000, 60 * 256) == backdrop
            assert read_vram(session, 0x1FA00, 512) == palette
            session.move_mouse(10, 10)
            session.shot(ROOT / 'build/test-shots/ai-difficulty.png')
            choose(session, 'Return'); choose(session, 'R'); choose(session, 'Return')
            assert text(session, 9) == 'YOUR TURN'
            choose(session, 'Escape'); choose(session, '2')
            saved = (directory / 'GAME.DAT').read_bytes()
            # Last scene byte encodes side, marker and level, without changing
            # the legacy file size or invalidating old saved games.
            assert saved[-3] & 0x46 == 0x44
            choose(session, '3')
            write(session, 'ai_difficulty', [0])
            choose(session, '3')
            assert read(session, 'ai_difficulty', 1) == b'\x02'
            assert text(session, 9) == 'YOUR TURN'
            choose(session, 'Escape'); choose(session, '3')
            legacy = bytearray(saved)
            legacy[-3] &= 0x81
            legacy[-2:] = checksum(legacy[:-2])
            (directory / 'GAME.DAT').write_bytes(legacy)
            choose(session, '3')
            assert read(session, 'ai_difficulty', 1) == b'\x01', 'legacy saves default to Normal'
            choose(session, 'Escape'); choose(session, '3')
            # Every encoded level restores independently of session choice;
            # invalid encoded values safely fall back to Normal.
            for encoded in range(4):
                data = bytearray(saved)
                data[-3] = (data[-3] & 1) | 0x40 | (encoded << 1)
                data[-2:] = checksum(data[:-2])
                (directory / 'GAME.DAT').write_bytes(data)
                write(session, 'ai_difficulty', [2])
                choose(session, '3')
                assert read(session, 'ai_difficulty', 1)[0] == (encoded if encoded < 3 else 1)
                choose(session, 'Escape'); choose(session, '3')
            # Exercise the actual writer and reader for every valid level.
            for level in range(3):
                choose(session, '3')
                write(session, 'ai_difficulty', [level])
                choose(session, 'Escape'); choose(session, '2')
                actual = (directory / 'GAME.DAT').read_bytes()
                assert actual[-3] & 0x46 == 0x40 | (level << 1)
                choose(session, '3')
                write(session, 'ai_difficulty', [(level + 1) % 3])
                choose(session, '3')
                assert read(session, 'ai_difficulty', 1)[0] == level
                choose(session, 'Escape'); choose(session, '3')
            # Real banked demo calls must preserve the selected level and
            # mask all unrevealed ranks before entering the AI gateway.
            write(session, 'ai_difficulty', [2])
            address = symbol('ai_move')
            session.emu.request('breakpoint', address=address)
            choose(session, '6')
            assert session.emu.advance(600)['reason'] == 'breakpoint'
            assert read(session, 'ai_difficulty', 1) == b'\x02'
            cells = read(session, 'board', 100)
            owners = {bool(c & 16) for c in cells if c < 254 and c & 15 == 12}
            assert len(owners) == 1
            enemy = owners.pop()
            assert all(c >= 254 or bool(c & 16) != enemy or c & 32 or c & 15 == 12 for c in cells)
            session.emu.request('breakpoint', action='remove', address=address)
            session.emu.advance(120)
            assert read(session, 'ai_difficulty', 1) == b'\x02'
            print('AI levels: pointer/keyboard cycle, backdrop/palette, Classic independence, saved Hard, legacy Normal, banked Hard and concealed ranks: ok')
        finally:
            session.emu.close()


if __name__ == '__main__':
    main()
