"""Baseline opponents that speak the engine protocol (docs/protocol.md).

Usage:
  python3 tools/bots.py random     any legal move
  python3 tools/bots.py greedy     takes what it knows it beats, probes with
                                   cheap pieces, otherwise advances

Like the native engine, a bot only knows its own pieces and what battles and
long scout moves have revealed. They anchor the rating scale and show how
another program can join the arena.
"""
import random
import sys

from feldmarschall import (BLUE, RED, SCOUT, UNKNOWN, VALUES, Position, battle, parse_square,
                      random_setup, square_name)

CHEAP = {6, 7, SCOUT}                     # sergeants, miners and scouts probe the enemy


class Bot:
    def __init__(self, kind):
        self.kind = kind
        self.rng = random.Random(1)
        self.army = RED
        self.view = Position()

    def new(self, army):
        self.army = army
        self.view = Position()
        self.view.place(1 - army, '?' * 40, known=False)

    def choose(self):
        moves = self.view.moves(self.army)
        if not moves or self.kind == 'random':
            return self.rng.choice(moves) if moves else None
        cells = self.view.cells

        def target(move):
            return cells[move[1]]

        def known_loss(move):
            t = target(move)
            return t and t[1] != UNKNOWN and battle(cells[move[0]][1], t[1]) != 'attacker'

        safe = [m for m in moves if not known_loss(m)] or moves
        wins = [m for m in safe if target(m) and target(m)[1] != UNKNOWN]
        if wins:
            return max(wins, key=lambda m: (VALUES[target(m)[1]], self.rng.random()))
        probes = [m for m in safe if target(m) and cells[m[0]][1] in CHEAP]
        if probes and self.rng.random() < 0.5:
            return self.rng.choice(probes)
        ahead = [m for m in safe if not target(m) and
                 (m[1] // 10 < m[0] // 10 if self.army == RED else m[1] // 10 > m[0] // 10)]
        return self.rng.choice(ahead or safe)

    def run(self):
        for line in sys.stdin:
            words = line.split()
            if not words:
                continue
            command, args = words[0], words[1:]
            if command == 'feldmarschall':
                self.reply(f'id name {self.kind}-bot', 'id author cx16-feldmarschall tools', 'ok')
            elif command == 'isready':
                self.reply('readyok')
            elif command == 'seed':
                self.rng.seed(int(args[0]))
            elif command == 'new':
                self.new(BLUE if args and args[0] == 'blue' else RED)
            elif command == 'setup':
                glyphs = args[0] if args else random_setup(self.rng)
                self.view.place(self.army, glyphs)
                if not args:
                    self.reply(f'setup {glyphs}')
            elif command == 'go':
                move = self.choose()
                self.reply(f'move {square_name(move[0])} {square_name(move[1])}' if move else 'move none')
            elif command == 'moved':
                self.view.move(parse_square(args[0]), parse_square(args[1]))
            elif command == 'battle':
                self.view.fight(parse_square(args[0]), parse_square(args[1]),
                                '123456789SBF'.index(args[2]), '123456789SBF'.index(args[3]))
            elif command == 'quit':
                break

    @staticmethod
    def reply(*lines):
        for line in lines:
            print(line)
        sys.stdout.flush()


if __name__ == '__main__':
    Bot(sys.argv[1] if len(sys.argv) > 1 else 'random').run()
