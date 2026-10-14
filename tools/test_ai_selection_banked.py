"""Compare real bank-24 deployments with native code through the game gateway."""
import ctypes
import argparse
import json
import re
from pathlib import Path
import shutil
import tempfile

from distribute import ROOT, runtime_files
from test_colors import start
from test_ai_selection import SelectionTests, next_random


def call(session, name, argument, symbol):
    before = session.emu.request('status')
    stack = before['sp']
    # A synthetic JSR return ends at a breakpoint in unused low RAM. The
    # actual function, software stack, gateway and bank restoration run intact.
    session.emu.write_memory(0x100 | ((stack - 1) & 255), b'\xff')
    session.emu.write_memory(0x100 | stack, b'\x01')
    session.emu.request('breakpoint', address=0x200)
    session.emu.request('set_registers', pc=symbol(name), a=argument & 255,
                        x=argument >> 8, sp=(stack - 2) & 255)
    assert session.emu.advance(30)['reason'] == 'breakpoint'
    after = session.emu.request('status')
    assert after['pc'] == 0x200 and after['sp'] == stack
    assert after['ram_bank'] == before['ram_bank']
    session.emu.request('breakpoint', action='remove', address=0x200)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT/'src')
    parser.add_argument('--out', type=Path, default=ROOT/'build/test-ai-selection-banked.json')
    args = parser.parse_args()
    symbols = (args.runtime/'FELDMARS.sym').read_text()
    def symbol(name):
        return int(re.search(r'al ([0-9A-F]+) \._'+name+r'\b', symbols).group(1), 16)
    SelectionTests.setUpClass()
    lib = SelectionTests.lib
    cells, level, rules = SelectionTests.cells, SelectionTests.level, SelectionTests.rules
    tickets = {}
    rejected = []
    for seed in range(1, 65536):
        draw = next_random(seed)
        if draw > 65530:
            rejected.append(seed)
        else:
            tickets.setdefault((draw - 1) % 10, seed)
    seeds = [*tickets.values(), *rejected]
    reports = []
    with tempfile.TemporaryDirectory(prefix='feldmarschall-selection-') as tmp:
        for name in runtime_files():
            shutil.copyfile(args.runtime / name, Path(tmp) / name)
        session = start(Path(tmp))
        try:
            session.emu.request('set_registers', ram_bank=22)
            cases = [('setup_ai', level, rules) for level, rules in [(1,0),(2,0),(0,0),(1,63),(2,1)]]
            cases.append(('setup_random', 1, 0))
            for function, difficulty, options in cases:
                for blue in (0, 1):
                    for seed in seeds:
                        level.value, rules.value = difficulty, options
                        lib.board_clear(); lib.random_seed(seed); getattr(lib, function)(blue)
                        expected = bytes(cells)
                        session.emu.write_memory(symbol('board'), bytes([255] * 100))
                        session.emu.write_memory(symbol('ai_difficulty'), bytes([difficulty]))
                        session.emu.write_memory(symbol('game_rules'), bytes([options]))
                        call(session, 'board_clear', 0, symbol)
                        call(session, 'random_seed', seed, symbol)
                        call(session, function, blue, symbol)
                        assert bytes(session.emu.read_memory(symbol('board'), 100)) == expected, (difficulty, options, blue, seed)
                        expected_next = lib.random_next()
                        call(session, 'random_next', 0, symbol)
                        status = session.emu.request('status')
                        assert status['a'] | status['x'] << 8 == expected_next
                        reports.append({'function': function, 'difficulty': difficulty, 'rules': options, 'blue': blue, 'seed': seed})
        finally:
            session.emu.close()
    args.out.write_text(json.dumps(reports, indent=2) + '\n')
    print(f'Deployment selection: {len(reports)} real banked calls match native layouts and RNG; bank 22 restored')


if __name__ == '__main__':
    main()
