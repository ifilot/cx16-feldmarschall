"""Play games through the emulator: Red makes random legal moves by mouse drags.

Usage:
  python3 tools/autoplay.py [--turns 100] [--seed 1] [--out build/autoplay.png]

Starts "Play against the computer", randomizes and confirms deployment,
then for every turn picks
a legal red move (an attack half of the time, when one exists) and drags the
piece there like a player would. It reads the board from emulator memory
(the _board symbol), checks that each turn changes it, and prints the final
position. A test for the play scene, the rules and the computer player.
"""
import argparse
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from screenshot import Session  # noqa: E402
from test_flow import text, wait_for_next_red_turn  # noqa: E402

GLYPHS = '123456789SBF'
EMPTY, LAKE, BLUE = 0xFF, 0xFE, 0x10
BOMB, FLAG, SCOUT = 10, 11, 8


def centre(sq):
    return 16 + (sq % 10) * 40 + 20, 16 + (sq // 10) * 40 + 20


def red_moves(board, shuttle=(None, None, 0)):
    """Legal red moves (from, to), following src/core/rules.c.

    shuttle is Red's last move and how often in a row it went back and
    forth: a further move back is barred by the two-squares rule.
    """
    last_src, last_dst, count = shuttle
    moves = []
    for sq, cell in enumerate(board):
        if cell >= LAKE or cell & BLUE or cell & 15 in (BOMB, FLAG):
            continue
        for dc, dr in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            c, r = sq % 10, sq // 10
            while True:
                c, r = c + dc, r + dr
                if not (0 <= c < 10 and 0 <= r < 10):
                    break
                other = board[r * 10 + c]
                banned = sq == last_dst and count >= 5 and r * 10 + c == last_src
                if other == EMPTY:
                    if not banned:
                        moves.append((sq, r * 10 + c))
                    if cell & 15 == SCOUT:
                        continue
                elif other < LAKE and other & BLUE and not banned:
                    moves.append((sq, r * 10 + c))
                break
    return moves


def show(board):
    rows = []
    for r in range(10):
        cells = []
        for cell in board[r * 10:r * 10 + 10]:
            cells.append(' .' if cell == EMPTY else ' ~' if cell == LAKE else
                         ('b' if cell & BLUE else 'r') + GLYPHS[cell & 15])
        rows.append(''.join(cells))
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--emu', default=str(ROOT.parent / 'x16-emulator/build/x16emu'))
    roms = [ROOT.parent / 'emulator/rom.bin', ROOT.parent / 'emulator-win/rom.bin']
    parser.add_argument('--rom', default=str(next((r for r in roms if r.exists()), roms[0])))
    parser.add_argument('--turns', type=int, default=100)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--out', default=str(ROOT / 'build/autoplay.png'))
    args = parser.parse_args()

    symbols = (ROOT / 'src/FELDMARS.sym').read_text()
    address = int(re.search(r'al ([0-9A-F]+) \._board\b', symbols).group(1), 16)
    random.seed(args.seed)
    session = Session(args.emu, args.rom)
    try:
        session.emu.advance(240)
        session.press('Return')
        session.emu.advance(120)
        session.press('2')
        session.emu.advance(20)
        session.press('Return')
        session.emu.advance(20)
        session.press('R')
        session.emu.advance(20)
        session.press('Return')
        session.emu.advance(20)
        shuttle = (None, None, 0)
        for turn in range(1, args.turns + 1):
            previous_turn = text(session, 11)
            board = session.emu.read_memory(address, 100)
            moves = red_moves(board, shuttle)
            if not moves:
                print(f'turn {turn}: Red has no moves')
                break
            attacks = [m for m in moves if board[m[1]] != EMPTY]
            move = random.choice(attacks if attacks and random.random() < 0.5 else moves)
            last_src, last_dst, count = shuttle
            count = count + 1 if count and move == (last_dst, last_src) else 1
            shuttle = (move[0], move[1], count)
            (x0, y0), (x1, y1) = centre(move[0]), centre(move[1])
            session.run([f'drag:{x0},{y0},{x1},{y1}'])
            session.emu.advance(320)    # battles and falls, Blue's thinking and its move
            if not wait_for_next_red_turn(session, previous_turn):
                print(f'turn {turn}: game ended')
                break
            after = session.emu.read_memory(address, 100)
            if after == board:
                raise SystemExit(f'turn {turn}: the move {move} changed nothing')
            if FLAG not in [c & 15 for c in after if c < LAKE and c & BLUE] or \
               FLAG not in [c & 15 for c in after if c < LAKE and not c & BLUE]:
                print(f'turn {turn}: a flag was captured')
                session.emu.advance(30)
                break
        print(show(session.emu.read_memory(address, 100)))
        session.shot(args.out)
    finally:
        session.close()


if __name__ == '__main__':
    main()
