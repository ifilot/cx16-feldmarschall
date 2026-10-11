"""Stratego rules, positions and engine processes for the test tools.

Follows src/core (rules.c, pieces.c, board.c): the same board numbering
(square 0 is a10, square 99 is j1), the same piece types and the same
battle rules. Used by the referee (arena.py), the baseline bots (bots.py)
and the parity test (parity.py). The protocol is described in
docs/protocol.md.
"""
import random
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GLYPHS = '123456789SBF'
MARSHAL, MINER, SCOUT, SPY, BOMB, FLAG = 0, 7, 8, 9, 10, 11
UNKNOWN = 12
COUNTS = [1, 1, 2, 3, 4, 4, 4, 5, 8, 1, 6, 1]
VALUES = [400, 200, 100, 75, 45, 30, 15, 25, 10, 100, 20, 1000]
LAKES = {42, 43, 52, 53, 46, 47, 56, 57}
RED, BLUE = 0, 1
STEPS = ((0, -1), (1, 0), (0, 1), (-1, 0))
TWO_SQUARES = 5           # moves in a row between the same two squares (rules.h)


def square_name(sq):
    return f'{"abcdefghij"[sq % 10]}{10 - sq // 10}'


def parse_square(name):
    m = re.fullmatch(r'([a-j])(10|[1-9])', name)
    if not m:
        raise ValueError(f'not a square: {name}')
    return (10 - int(m.group(2))) * 10 + 'abcdefghij'.index(m.group(1))


def setup_squares(army):
    """The home squares of an army in deployment order: front row first, a to j."""
    rows = [3, 2, 1, 0] if army == BLUE else [6, 7, 8, 9]
    return [r * 10 + c for r in rows for c in range(10)]


def battle(attacker, defender):
    """'attacker', 'defender' or 'both': the pieces that win (rules.c)."""
    if defender == FLAG:
        return 'attacker'
    if defender == BOMB:
        return 'attacker' if attacker == MINER else 'defender'
    if attacker == SPY and defender == MARSHAL:
        return 'attacker'
    if attacker == defender:
        return 'both'
    return 'attacker' if attacker < defender else 'defender'


def valid_setup(glyphs):
    return len(glyphs) == 40 and all(glyphs.count(g) == n for g, n in zip(GLYPHS, COUNTS))


def random_setup(rng):
    """A random deployment: flag on the back row, bombs beside and before it."""
    cells = [None] * 40                       # deployment order: index 30-39 is the back row
    flag = 30 + rng.randrange(10)
    cells[flag] = 'F'
    bombs = 0
    for n in (flag - 10, flag - 1 if flag % 10 else None, flag + 1 if flag % 10 < 9 else None):
        if n is not None and cells[n] is None:
            cells[n] = 'B'
            bombs += 1
    pool = [g for g, n in zip(GLYPHS, COUNTS) for _ in range(n)]
    pool.remove('F')
    for _ in range(bombs):
        pool.remove('B')
    rng.shuffle(pool)
    return ''.join(c if c else pool.pop() for c in cells)


def presets():
    """The ten built-in deployments of src/core/presets.c, as (name, glyphs)."""
    source = (ROOT / 'src/core/presets.c').read_text()
    names = re.findall(r'^    "([A-Z ]+)",$', source.split('preset_names')[1].split('};')[0], re.M)
    table = source.split('presets[PRESETS] = {')[1].split('};')[0]
    armies = [''.join(re.findall(r'"([^"]*)"', block)) for block in table.split(',')[:-1]]
    return list(zip(names, armies))


class Position:
    """A board of (army, type, moved, revealed) pieces; None is empty or a lake."""

    def __init__(self):
        self.cells = [None] * 100
        self.shuttle = {RED: (None, None, 0), BLUE: (None, None, 0)}

    def record(self, src, dst):
        """Note a move for the two-squares rule (rules_record in rules.c)."""
        army = self.cells[src][0]
        last_src, last_dst, count = self.shuttle[army]
        count = count + 1 if count and src == last_dst and dst == last_src else 1
        self.shuttle[army] = (src, dst, count)

    def place(self, army, glyphs, known=True):
        for sq, g in zip(setup_squares(army), glyphs):
            self.cells[sq] = [army, GLYPHS.index(g) if known else UNKNOWN, False, False]

    def moves(self, army):
        """Legal moves (from, to) of an army whose own types are known,
        without one that would break the two-squares rule."""
        result = []
        last_src, last_dst, count = self.shuttle[army]
        for sq, cell in enumerate(self.cells):
            if not cell or cell[0] != army or cell[1] in (BOMB, FLAG):
                continue
            banned = last_src if sq == last_dst and count >= TWO_SQUARES else None
            for dc, dr in STEPS:
                c, r = sq % 10, sq // 10
                while True:
                    c, r = c + dc, r + dr
                    to = r * 10 + c
                    if not (0 <= c < 10 and 0 <= r < 10) or to in LAKES:
                        break
                    other = self.cells[to]
                    if other is None:
                        if to != banned:
                            result.append((sq, to))
                        if cell[1] == SCOUT:
                            continue
                    elif other[0] != army and to != banned:
                        result.append((sq, to))
                    break
        return result

    def move(self, src, dst):
        """A quiet move; a move over several squares reveals a scout."""
        self.record(src, dst)
        cell = self.cells[src]
        if abs(src // 10 - dst // 10) + abs(src % 10 - dst % 10) > 1:
            cell[1], cell[3] = SCOUT, True
        cell[2] = True
        self.cells[dst], self.cells[src] = cell, None

    def fight(self, src, dst, attacker, defender):
        """A battle with known ranks; returns the outcome and the fallen cells."""
        self.record(src, dst)
        a, d = self.cells[src], self.cells[dst]
        a[1], d[1] = attacker, defender
        a[2] = a[3] = d[3] = True
        outcome = battle(attacker, defender)
        fallen = []
        if outcome in ('defender', 'both'):
            fallen.append(a)
        if outcome in ('attacker', 'both'):
            fallen.append(d)
        self.cells[src] = None
        self.cells[dst] = a if outcome == 'attacker' else (d if outcome == 'defender' else None)
        return outcome, fallen


class Engine:
    """A program speaking the protocol, started as a subprocess."""

    def __init__(self, command, name=None):
        self.name = name or command
        self.process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        text=True, bufsize=1, cwd=ROOT)
        self.send('stratego')
        while self.read() != 'ok':
            pass

    def send(self, line):
        self.process.stdin.write(line + '\n')
        self.process.stdin.flush()

    def read(self):
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f'{self.name} stopped')
        return line.strip()

    def ask(self, line, prefix):
        self.send(line)
        while True:
            answer = self.read()
            if answer.startswith(prefix):
                return answer[len(prefix):].strip()
            if answer.startswith('error'):
                raise RuntimeError(f'{self.name}: {answer} (after "{line}")')

    def close(self):
        try:
            self.send('quit')
            self.process.stdin.close()
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()


def new_rng(seed):
    return random.Random(seed)
