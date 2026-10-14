"""Exercise coordinated jobs through the real banked game caller.

Inject a permitted view at the AI gateway; inspect the result before the play
scene restores its original truth. Each fixture runs in a disposable runtime.
"""
import json
import shutil
import tempfile
from pathlib import Path

from distribute import ROOT, runtime_files
from test_colors import start, choose
from test_flow import symbol
from feldmarschall import COUNTS, LAKES


def fixture(probe, blue):
    cells = [255] * 100
    for sq in LAKES:
        cells[sq] = 254
    pieces = {60: 7, 99: 11, 0: 11 | 16 | 32, 10: 10 | 16 | 32}
    lost = list(COUNTS)
    lost[11] -= 1; lost[10] -= 1
    expected = (50, 51)
    if probe:
        pieces.update({61: 8, 1: 10 | 16 | 32, 40: 12 | 16, 39: 12 | 16})
        lost[10] -= 2; lost[8] -= 1
        expected = (61, 41)
    else:
        pieces[50] = 3
    for sq, cell in pieces.items():
        cells[99-sq if blue else sq] = cell ^ (16 if blue else 0)
    if blue:
        expected = tuple(99-sq for sq in expected)
    return bytes(cells), bytes(lost), expected


def main():
    records = []
    gateway = symbol('ai_move')
    mission_entry = symbol('ai_mission_begin_banked')
    for level in (1, 2):
        for blue in (False, True):
            for probe in (False, True):
                with tempfile.TemporaryDirectory(prefix='feldmarschall-missions-') as tmp:
                    for filename in runtime_files():
                        shutil.copyfile(ROOT / 'src' / filename, tmp + '/' + filename)
                    session = start(Path(tmp))
                    try:
                        session.emu.write_memory(symbol('ai_difficulty'), bytes([level]))
                        session.emu.request('breakpoint', address=gateway)
                        choose(session, '6')
                        assert session.emu.request('status')['pc'] == gateway
                        before = session.emu.request('status')
                        stack = int.from_bytes(session.emu.read_memory(0x22, 2), 'little')
                        arguments = bytes(session.emu.read_memory(stack, 5))
                        from_ptr = int.from_bytes(arguments[:2], 'little')
                        lost_ptr = int.from_bytes(arguments[2:4], 'little')
                        to_ptr = before['a'] | before['x'] << 8
                        hardware_stack = 0x100 | ((before['sp'] + 1) & 255)
                        return_pc = int.from_bytes(session.emu.read_memory(hardware_stack, 2), 'little') + 1
                        view, lost, expected = fixture(probe, blue)
                        session.emu.write_memory(symbol('board'), view)
                        session.emu.write_memory(lost_ptr, lost)
                        session.emu.write_memory(stack + 4, bytes([16 if blue else 0]))
                        session.emu.request('breakpoint', action='remove', address=gateway)
                        session.emu.request('breakpoint', address=mission_entry, bank=24)
                        assert session.emu.advance(600)['reason'] == 'breakpoint'
                        assert session.emu.request('status')['ram_bank'] == 24
                        assert bytes(session.emu.read_memory(symbol('board'), 100)) == view
                        session.emu.request('breakpoint', action='remove', address=mission_entry, bank=24)
                        session.emu.request('breakpoint', address=gateway + 6)
                        assert session.emu.advance(600)['reason'] == 'breakpoint'
                        assert session.emu.request('status')['ram_bank'] == 23
                        got = (session.emu.read_memory(from_ptr, 1)[0], session.emu.read_memory(to_ptr, 1)[0])
                        assert got == expected, (level, blue, probe, got, expected)
                        assert bytes(session.emu.read_memory(symbol('board'), 100)) == view
                        session.emu.request('breakpoint', action='remove', address=gateway + 6)
                        session.emu.request('breakpoint', address=return_pc, bank=22)
                        assert session.emu.advance(2)['reason'] == 'breakpoint'
                        assert session.emu.request('status')['ram_bank'] == 22
                        records.append({'level': level, 'blue': blue, 'job': 'probe' if probe else 'vacate', 'move': got})
                    finally:
                        session.emu.close()
    (ROOT / 'build/test-ai-missions.json').write_text(json.dumps(records, indent=2) + '\n')
    print('AI missions: 8 banked jobs passed; masked views preserved and banks 22/23/24 restored')


if __name__ == '__main__':
    main()
