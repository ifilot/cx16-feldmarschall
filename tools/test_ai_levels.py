"""Difficulty selection, saved-game compatibility, and real banked AI use."""
import shutil
import re
import tempfile
import json
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
    mapping=(ROOT/'src/FELDMARS.map').read_text()
    memory_base=int(re.search(r'^MISSIONBSS\s+([0-9A-F]+)',mapping,re.M).group(1),16)
    memory_base+=int(re.search(r'ai_memory\.o:\n\s+MISSIONBSS\s+Offs=([0-9A-F]+)',mapping).group(1),16)
    build_record = ROOT/'src/ai-build.json'
    release = json.loads(build_record.read_text()) if build_record.exists() else {}
    q24 = 'AI_TEMPLATE_PRIOR_Q24' in release.get('defines', [])
    if q24:
        belief_base=int(re.search(r'^BELIEFBSS\s+([0-9A-F]+)',mapping,re.M).group(1),16)-0xa000
        def cache_write(value):
            for name in ('cache_valid','cache_hit'):
                session.emu.write_memory(belief_base+release['belief_bss_symbols'][name]['offset'],bytes([value]),space='banked_ram',bank=25)
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
            # GAME.DAT omits observer history. Loading must clear a warm tracker
            # and safely use the cold-history model, rather than stale identities.
            session.emu.write_memory(memory_base-0xa000,bytes([0])*941,space='banked_ram',bank=24)
            if q24: cache_write(165)
            choose(session, '3')
            history=bytes(session.emu.read_memory(memory_base-0xa000,941,space='banked_ram',bank=24))
            if q24:
                # The inference release immediately synchronizes a fresh public
                # snapshot, then marks opening ancestry unavailable. It must not
                # retain the poisoned pre-load token identities or infer origins.
                layout = json.loads(build_record.read_text())['memory_bss_symbols']
                def private(name):
                    item = layout[name]
                    return bytes(session.emu.read_memory(memory_base-0xa000+item['offset'], item['size'], space='banked_ram', bank=24))
                cells = read(session, 'board', 100)
                identities, pieces = private('identities'), private('pieces')
                occupied = [sq for sq,cell in enumerate(cells) if cell < 254]
                assert private('count') == bytes([len(occupied)])
                assert private('template_history_valid') == b'\x02', 'loaded saves cannot reconstruct opening origins'
                for name in ('cache_valid','cache_hit'):
                    assert bytes(session.emu.read_memory(belief_base+release['belief_bss_symbols'][name]['offset'],1,space='banked_ram',bank=25)) == b'\0', 'loading invalidates a warm inference cache'
                for square, cell in enumerate(cells):
                    if cell >= 254:
                        assert identities[square] == 255
                    else:
                        token = identities[square]
                        assert token < len(occupied)
                        piece = pieces[token*10:(token+1)*10]
                        assert piece[:6] == bytes([square,square,cell&16,0,0,(cell&15) if cell&32 else 12])
            else:
                assert history==bytes([255])*100+bytes(841), 'loading clears all public observer history'
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
