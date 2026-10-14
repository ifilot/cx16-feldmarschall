"""Compare real bank-24 move observations with the native public-history tracker."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from feldmarschall import ROOT, Engine, GLYPHS, square_name
from test_colors import start, choose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT/'build/ai-memory-x16')
    parser.add_argument('--events', type=int, default=8)
    parser.add_argument('--rules', type=int, choices=range(64), default=0)
    args = parser.parse_args()
    runtime = args.runtime
    symbols = (runtime/'FELDMARS.sym').read_text()
    symbol = lambda name: int(re.search(r'al ([0-9A-F]+) \._'+name+r'\b', symbols).group(1), 16)
    mapping = (runtime/'FELDMARS.map').read_text()
    base = int(re.search(r'^MISSIONBSS\s+([0-9A-F]+)', mapping, re.M).group(1), 16)
    offset = int(re.search(r'ai_memory\.o:\n\s+MISSIONBSS\s+Offs=([0-9A-F]+)', mapping).group(1), 16)
    layout = (runtime/'memory-layout.s').read_text()
    assert re.search(r'_identities:\s+\.res\s+100,\$00\s+_count:\s+\.res\s+1,\$00\s+_pieces:\s+\.res\s+840,\$00', layout)
    base += offset
    gateway, banked = symbol('ai_memory_observe'), symbol('ai_memory_observe_banked')
    records, comparisons = [], 0
    with tempfile.TemporaryDirectory(prefix='feldmarschall-memory-') as tmp:
        for path in runtime.iterdir():
            if path.is_file(): shutil.copy2(path, Path(tmp)/path.name)
        session = start(Path(tmp))
        native = Engine(str(ROOT/'build/feldmarschall-engine-memory'))
        try:
            session.emu.write_memory(symbol('game_rules'), bytes([args.rules]))
            native.send('rules '+str(args.rules))
            session.emu.request('breakpoint', address=gateway)
            choose(session, '6')
            for event in range(args.events):
                before = session.emu.request('status')
                assert before['pc'] == gateway and before['ram_bank'] == 22, before
                stack = int.from_bytes(session.emu.read_memory(0x22, 2), 'little')
                to, src = session.emu.read_memory(stack, 2)
                outcome = before['a']
                cells = bytes(session.emu.read_memory(symbol('board'), 100))
                if event == 0:
                    native.send('new red')
                    native.send('setup '+''.join(GLYPHS[cells[sq] & 15] for sq in range(60, 100)))
                notification = f'moved {square_name(src)} {square_name(to)}' if outcome == 3 else (
                    f'battle {square_name(src)} {square_name(to)} {GLYPHS[cells[src]&15]} {GLYPHS[cells[to]&15]}')
                native.send(notification)
                hw_stack = 0x100 | ((before['sp']+1) & 255)
                return_pc = int.from_bytes(session.emu.read_memory(hw_stack, 2), 'little')+1
                session.emu.request('breakpoint', action='remove', address=gateway)
                session.emu.request('breakpoint', address=banked, bank=24)
                assert session.emu.advance(600)['reason'] == 'breakpoint'
                assert session.emu.request('status')['ram_bank'] == 24
                session.emu.request('breakpoint', action='remove', address=banked, bank=24)
                session.emu.request('breakpoint', address=gateway+6)
                assert session.emu.advance(2)['reason'] == 'breakpoint'
                assert session.emu.request('status')['ram_bank'] == 24
                state = bytes(session.emu.read_memory(base, 941))
                for sq, identity in enumerate(state[:100]):
                    if identity == 255: continue
                    data = state[101+identity*10:111+identity*10]
                    expected = [sq, identity, *data[:8], int.from_bytes(data[8:10], 'little')]
                    got = list(map(int, native.ask('memory '+square_name(sq), 'history').split()))
                    assert got == expected, (event, sq, got, expected)
                    comparisons += 1
                session.emu.request('breakpoint', action='remove', address=gateway+6)
                session.emu.request('breakpoint', address=return_pc)
                assert session.emu.advance(2)['reason'] == 'breakpoint'
                assert session.emu.request('status')['ram_bank'] == 22
                session.emu.request('breakpoint', action='remove', address=return_pc)
                records.append({'event': event, 'notification': notification, 'bank_restored': 22,
                                'state_sha256': hashlib.sha256(state).hexdigest()})
                if event+1 < args.events:
                    session.emu.request('breakpoint', address=gateway)
                    assert session.emu.advance(600)['reason'] == 'breakpoint'
        finally:
            native.close(); session.emu.close()
    report = {'events': records, 'rules': args.rules, 'live_piece_history_comparisons': comparisons, 'mismatches': 0,
              'native_sha256': hashlib.sha256((ROOT/'build/feldmarschall-engine-memory').read_bytes()).hexdigest(),
              'runtime_provenance': json.loads((runtime/'provenance.json').read_text())}
    (runtime/f'banked-observations-rules-{args.rules}.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'AI memory: {args.events} real banked events, {comparisons} native/X16 piece histories matched; bank 22 restored')


if __name__ == '__main__':
    main()
