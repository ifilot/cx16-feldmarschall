"""Check that the X16 build of the computer player matches the native build.

Usage:
  python3 tools/parity.py [--positions 100] [--seed 1]

Plays random games to collect positions, turns each into one army's view
(enemy pieces it has not seen become unknown), and asks both builds for a
move with the same random seed: the native engine (build/feldmarschall-engine,
"think") and BRIDGE.PRG running in the AgentBridge emulator (src/bridge).
Every move must be identical. Requires `make` and `make native`.
"""
import argparse
import json
import random
import sys
from pathlib import Path

from feldmarschall import (BLUE, COUNTS, LAKES, RED, ROOT, UNKNOWN, Engine, Position, random_setup)

sys.path.insert(0, str(ROOT.parent / 'x16-emulator/api/python'))
from x16agent import X16Agent  # noqa: E402

MAILBOX = 0x0400
EMPTY, LAKE, CELL_BLUE, CELL_REVEALED, CELL_MOVED = 0xFF, 0xFE, 0x10, 0x20, 0x40


def view(truth, army):
    """The army's view in the byte encoding of src/core (board.h, pieces.h)."""
    cells, lost = [], [0] * 12
    on_board = [0] * 12
    for sq, cell in enumerate(truth.cells):
        if sq in LAKES:
            cells.append(LAKE)
            continue
        if cell is None:
            cells.append(EMPTY)
            continue
        owner, kind, moved, revealed = cell
        if owner != army:
            on_board[kind] += 1
            if not revealed:
                kind = UNKNOWN
        cells.append(kind | (CELL_BLUE if owner == BLUE else 0) |
                     (CELL_REVEALED if revealed else 0) | (CELL_MOVED if moved else 0))
    for kind in range(12):
        lost[kind] = COUNTS[kind] - on_board[kind]
    return cells, lost


def positions(count, rng):
    """Positions from random games, at a spread of moments."""
    found = []
    while len(found) < count:
        truth = Position()
        truth.place(RED, random_setup(rng))
        truth.place(BLUE, random_setup(rng))
        side = RED
        for ply in range(rng.randrange(0, 400)):
            moves = truth.moves(side)
            if not moves:
                break
            src, dst = rng.choice(moves)
            if truth.cells[dst] is None:
                truth.move(src, dst)
            else:
                truth.fight(src, dst, truth.cells[src][1], truth.cells[dst][1])
                if not any(c and c[1] == 11 for c in truth.cells if c and c[0] != side):
                    break
            side = 1 - side
        if truth.moves(side):
            found.append((side, *view(truth, side)))
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--positions', type=int, default=100)
    parser.add_argument('--repetitions', type=int, choices=range(1, 256), default=1,
                        help='repeated decisions on each fixed view; 129 saturates quiet-turn pressure')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--emu', default=str(ROOT.parent / 'x16-emulator/build/x16emu'))
    roms = [ROOT.parent / 'emulator/rom.bin', ROOT.parent / 'emulator-win/rom.bin']
    parser.add_argument('--rom', default=str(next((r for r in roms if r.exists()), roms[0])))
    parser.add_argument('--difficulty', choices=('easy', 'normal', 'hard'), default='normal')
    parser.add_argument('--rules', type=int, default=0)
    parser.add_argument('--bridge', type=Path, default=ROOT / 'src/BRIDGE.PRG')
    parser.add_argument('--engine', default=str(ROOT / 'build/feldmarschall-engine'))
    parser.add_argument('--reference', help='also compare fresh decisions with another native engine')
    parser.add_argument('--json-out', type=Path)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    tests = positions(args.positions, rng)
    native = Engine(args.engine, 'native')
    native.send('difficulty ' + args.difficulty)
    native.send(f'rules {args.rules}')
    reference = Engine(args.reference, 'reference') if args.reference else None
    emu = X16Agent(args.emu, args.rom, fsroot=ROOT / 'src', options=['-prg', str(args.bridge), '-run'])
    mismatches, slowest = 0, 0
    timings = []
    try:
        emu.advance(120)
        for n, (army, cells, lost) in enumerate(tests, 1):
            seed = rng.randrange(1, 65536)
            answer = native.ask(f'think {army} {seed} {bytes(lost).hex()} {bytes(cells).hex()} {args.repetitions}', 'best')
            expected = tuple(int(v) for v in answer.split())
            if reference:
                reference_answer = reference.ask(f'think {army} {seed} {bytes(lost).hex()} {bytes(cells).hex()} {args.repetitions}', 'best')
                if tuple(map(int, reference_answer.split())) != expected:
                    raise SystemExit(f'position {n}: optimized decision differs from reference')

            emu.write_memory(MAILBOX + 1, bytes([army, seed & 255, seed >> 8]) + bytes(lost) + bytes(cells))
            emu.write_memory(MAILBOX + 118, bytes([('easy', 'normal', 'hard').index(args.difficulty), args.rules]))
            emu.write_memory(MAILBOX + 120, bytes([args.repetitions]))
            emu.write_memory(MAILBOX, bytes([3 if args.repetitions > 1 else 1]))
            for frames in range(1, 600 * args.repetitions):
                emu.advance(1)
                if emu.read_memory(MAILBOX, 1)[0] == 2:
                    break
            else:
                raise SystemExit(f'position {n}: the X16 did not answer')
            slowest = max(slowest, frames)
            timings.append(frames)
            got = tuple(emu.read_memory(MAILBOX + 116, 2))
            if got != expected:
                mismatches += 1
                print(f'position {n}: native {expected}, X16 {got}')
    finally:
        native.close()
        if reference: reference.close()
        emu.close()
    unit = 'per move' if args.repetitions == 1 else f'per {args.repetitions}-call batch'
    print(f'{len(tests)} positions, {mismatches} mismatches; '
          f'the X16 took at most {slowest} frames ({slowest / 60:.2f} s) {unit}')
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps({
            'difficulty': args.difficulty, 'positions': len(tests), 'seed': args.seed,
            'repetitions': args.repetitions,
            'rules': args.rules, 'mismatches': mismatches, 'max_frames': slowest,
            'mean_frames': sum(timings) / len(timings),
            'p95_frames': sorted(timings)[int(0.95 * (len(timings)-1))],
            'frame_samples': timings,
        }, indent=2) + '\n')
    sys.exit(1 if mismatches else 0)


if __name__ == '__main__':
    main()
