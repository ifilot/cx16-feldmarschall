"""Public-input desktop teacher adapter; shared actions averaged over sampled worlds."""
import argparse
import json
from pathlib import Path
import random
import shlex
import subprocess
import sys

from feldmarschall import ROOT, Engine, parse_square, square_name
from train_ai_student import sample_world


class TeacherBot:
    def __init__(self, observer, teacher, samples=8, depth=3, blend='raw', strategic=False, context=False, replies=None):
        self.observer = Engine(shlex.quote(str(observer)))
        command = [str(teacher)] + (['--strategic'] if strategic else [])
        if context: command.append('--context')
        if replies is not None: command += ['--replies',str(replies)]
        self.teacher = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.samples, self.depth, self.blend = samples, depth, blend
        self.rng = random.Random(1)
        self.last_report = None
        self.context = context

    def choose(self):
        army_text, board_hex, lost_hex, shuttle = self.observer.ask('public', 'public').split()
        army, cells = int(army_text), list(bytes.fromhex(board_hex))
        histories = {sq: list(map(int, self.observer.ask('memory ' + square_name(sq), 'history').split()))
                     for sq, cell in enumerate(cells) if cell < 254 and bool(cell & 16) != bool(army) and not cell & 32}
        # Capture strategic state before ranked() speculatively transfers the
        # chosen actor's goal. Each sampled continuation starts from this same
        # permitted history, then explicitly follows its own proposed action.
        context = self.observer.ask('strategy', 'strategy') if self.context else ''
        self.observer.send('ranked')
        scores, credit = {}, {}
        while True:
            words = self.observer.read().split()
            if words[0] == 'move':
                if words[1] == 'none': return None
                parent = tuple(map(parse_square, words[1:3])); break
            if words[0] in ('candidate', 'credit'):
                (scores if words[0] == 'candidate' else credit)[tuple(map(int, words[1:3]))] = int(words[3])
            if words[0] == 'error': raise ValueError(words)
        totals = {move: [0.0, 0.0, 0.0] for move in scores}
        weights, nodes = [], 0
        for _ in range(self.samples):
            world, weight = sample_world(cells, list(bytes.fromhex(lost_hex)), histories, self.rng, army)
            suffix = ' ' + context if self.context else ''
            self.teacher.stdin.write(f'search {army} {self.depth} {bytes(world).hex()} {shuttle}{suffix}\n'); self.teacher.stdin.flush()
            values = {}
            while True:
                words = self.teacher.stdout.readline().split()
                if not words: raise ValueError('teacher stopped')
                if words[0] == 'error': raise ValueError(words)
                if words[0] == 'done':
                    nodes += int(words[1]); reference = int(words[2]); break
                if words[0] == 'action': values[tuple(map(int, words[1:3]))] = tuple(map(int, words[3:5]))
            if set(values) != set(scores): raise ValueError('sampled world changes root legal actions')
            weights.append(weight)
            for move, (future, immediate) in values.items():
                totals[move][0] += weight * future
                totals[move][1] += weight * immediate
                totals[move][2] += weight * reference
        choices, corrections, means = {}, {}, {}
        for move, (future, immediate, reference) in totals.items():
            future /= sum(weights); immediate /= sum(weights); reference /= sum(weights)
            correction = max(-192, min(192, future - immediate - reference + credit.get(move, 0)))
            corrections[move] = correction
            means[move] = (future, immediate, reference)
            choices[move] = future + scores[move] * .01 if self.blend == 'raw' else scores[move] + correction
        # Keep unequivocal immediate victories at their native priority.
        wins = [move for move, score in scores.items() if score >= 30000]
        selected = parent if parent in wins else max(wins or choices, key=lambda move: (choices[move], move == parent, -move[0], -move[1]))
        self.observer.ask(f'played {square_name(selected[0])} {square_name(selected[1])}', 'playedok')
        self.last_report = {'army': army, 'parent': parent, 'selected': selected, 'nodes': nodes,
                            'effective_samples': sum(weights)**2 / sum(w*w for w in weights),
                            'values': [{'move': move, 'value': value, 'parent_score': scores[move],
                                        'correction': corrections[move], 'sample_mean': means[move]}
                                       for move, value in choices.items()]}
        return selected

    def close(self):
        self.observer.close()
        self.teacher.stdin.close(); self.teacher.wait(timeout=10); self.teacher.stdout.close()

    def run(self):
        try:
            for line in sys.stdin:
                words = line.split()
                if not words: continue
                command = words[0]
                if command == 'feldmarschall':
                    print('id name public-teacher\nid author cx16-feldmarschall tools\nok', flush=True)
                elif command == 'isready': print('readyok', flush=True)
                elif command == 'seed': self.rng.seed(int(words[1])); self.observer.send(line.strip())
                elif command == 'rules':
                    if int(words[1]) != 0: raise ValueError('teacher supports Classic only')
                    self.observer.send(line.strip())
                elif command == 'go':
                    move = self.choose()
                    print('move ' + ' '.join(map(square_name, move)) if move else 'move none', flush=True)
                elif command == 'public': print('public ' + self.observer.ask('public', 'public'), flush=True)
                elif command == 'played': print(self.observer.ask(line.strip(), 'playedok') or 'playedok', flush=True)
                elif command == 'quit': break
                elif command == 'setup' and len(words) == 1:
                    print('setup ' + self.observer.ask('setup', 'setup'), flush=True)
                else: self.observer.send(line.strip())
        finally: self.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer', type=Path, default=ROOT / 'build/feldmarschall-teacher-observer')
    parser.add_argument('--teacher', type=Path, default=ROOT / 'build/feldmarschall-teacher')
    parser.add_argument('--samples', type=int, default=8)
    parser.add_argument('--depth', type=int, default=3)
    parser.add_argument('--blend', choices=('raw', 'correction'), default='raw')
    parser.add_argument('--strategic', action='store_true')
    parser.add_argument('--difficulty', choices=('normal', 'hard'), default='normal')
    parser.add_argument('--context', action='store_true', help='preserve permitted root strategic history in rollouts')
    parser.add_argument('--replies', type=int, choices=(1,2,3), help='plausible first opponent replies (supported teacher builds only)')
    args = parser.parse_args()
    if args.samples < 1 or args.depth < 1: parser.error('positive samples and depth required')
    bot = TeacherBot(args.observer, args.teacher, args.samples, args.depth, args.blend, args.strategic, args.context, args.replies)
    bot.observer.send('difficulty ' + args.difficulty)
    bot.run()
