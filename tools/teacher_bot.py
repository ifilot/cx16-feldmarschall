"""Public-input desktop teacher adapter; shared actions averaged over sampled worlds."""
import argparse
import json
import importlib
import math
from pathlib import Path
import random
import shlex
import subprocess
import sys

from feldmarschall import ROOT, Engine, GLYPHS, LAKES, Position, valid_setup, parse_square, square_name
from train_ai_student import sample_world


class TeacherBot:
    def __init__(self, observer, teacher, samples=8, depth=3, blend='raw', strategic=False, context=False, replies=None, diagnostic_truth=False, diagnostic_knowledge='all', information_strategy=None, belief_model=None, root_policy=None):
        if information_strategy not in (None, 'lifetime', 'objectives', 'followthrough'):
            raise ValueError('unknown information strategy')
        if information_strategy and diagnostic_truth:
            raise ValueError('fair information strategies cannot use diagnostic truth')
        if belief_model and (diagnostic_truth or information_strategy):
            raise ValueError('calibrated beliefs require an isolated fair strategy')
        if root_policy and (diagnostic_truth or information_strategy or belief_model or blend != 'correction'):
            raise ValueError('root selection requires isolated public correction-blend teacher')
        self.root_policy = None
        self.policy_rng = None
        if root_policy:
            from root_policy import RootPolicy, MOVE_SEED_DOMAIN
            self.root_policy = RootPolicy.load(root_policy)
            self.policy_rng = random.Random(1 ^ MOVE_SEED_DOMAIN)
        self.belief_model = None
        if belief_model:
            from calibrated_beliefs import BeliefModel
            self.belief_model = BeliefModel.load(belief_model)
        self.information_strategy = information_strategy
        self.information_module = importlib.import_module('info_' + information_strategy) if information_strategy else None
        self.observer = Engine(shlex.quote(str(observer)))
        command = [str(teacher)] + (['--strategic'] if strategic else [])
        if context: command.append('--context')
        if replies is not None: command += ['--replies',str(replies)]
        self.teacher = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.samples, self.depth, self.blend = samples, depth, blend
        self.rng = random.Random(1)
        self.last_report = None
        self.context = context
        self.diagnostic_truth = diagnostic_truth
        if diagnostic_knowledge not in ('all', 'flag-spy', 'flag'): raise ValueError('invalid diagnostic knowledge')
        self.diagnostic_knowledge = diagnostic_knowledge
        self.truth = None
        self.truth_setups = [None, None]
        self.side = 0
        self.truth_plies = 0

    def diagnostic_event(self, words):
        """Track privileged setup plus public events, isolated to the ablation."""
        command = words[0]
        if command == 'opponent-setup' and not self.diagnostic_truth:
            raise ValueError('public teacher rejects opponent setup')
        if not self.diagnostic_truth:
            return
        if command == 'new':
            self.side = int(words[1] == 'blue')
            self.truth = None
            self.truth_setups = [None, None]
            self.truth_plies = 0
        elif command in ('setup', 'opponent-setup') and len(words) == 2:
            if self.truth is not None or not valid_setup(words[1]):
                raise ValueError('invalid or late diagnostic setup')
            self.truth_setups[self.side if command == 'setup' else 1-self.side] = words[1]
            if all(self.truth_setups):
                self.truth = Position()
                for army, setup in enumerate(self.truth_setups): self.truth.place(army, setup)
        elif command in ('moved', 'battle'):
            if self.truth is None: raise ValueError('diagnostic teacher needs both armies')
            src, dst = map(parse_square, words[1:3])
            source, target = self.truth.cells[src], self.truth.cells[dst]
            if source is None or (src, dst) not in self.truth.moves(source[0]):
                raise ValueError('illegal diagnostic event')
            if command == 'moved':
                if target is not None: raise ValueError('occupied diagnostic quiet destination')
                self.truth.move(src, dst)
            else:
                ranks = tuple(GLYPHS.index(g) for g in words[3:5])
                if target is None or ranks != (source[1], target[1]):
                    raise ValueError('diagnostic battle differs from physical ranks')
                self.truth.fight(src, dst, *ranks)
            self.truth_plies += 1

    def choose(self):
        if self.diagnostic_truth:
            if self.truth is None: raise ValueError('diagnostic teacher needs both armies')
            truth = bytes(254 if sq in LAKES else 255 if cell is None else cell[1] | (16 if cell[0] else 0)
                          for sq, cell in enumerate(self.truth.cells))
            command = {'all':'diagnostic-truth','flag-spy':'diagnostic-flag-spy','flag':'diagnostic-flag'}[self.diagnostic_knowledge]
            self.observer.ask(command + ' ' + truth.hex(), 'diagnostic-truthok')
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
        sampled = (self.belief_model.sample_worlds(cells, list(bytes.fromhex(lost_hex)),
                   histories, self.rng, army, self.samples) if self.belief_model else None)
        for sample in range(self.samples):
            world, weight = (sampled[sample] if sampled is not None else
                             sample_world(cells, list(bytes.fromhex(lost_hex)), histories, self.rng, army))
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
        information_adjustments = {}
        if self.information_module:
            # Modules receive only the same public root view as the masked
            # teacher. Rank hypotheses and scored futures contain no referee data.
            information_adjustments = self.information_module.adjustments(
                cells[:], army, list(bytes.fromhex(lost_hex)), histories, dict(choices))
            if any(move not in choices or not math.isfinite(value)
                   for move, value in information_adjustments.items()):
                raise ValueError('invalid information-strategy adjustment')
            for move, value in information_adjustments.items(): choices[move] += value
        # Keep unequivocal immediate victories at their native priority.
        wins = [move for move, score in scores.items() if score >= 30000]
        selected = parent if parent in wins else max(wins or choices, key=lambda move: (choices[move], move == parent, -move[0], -move[1]))
        selection = None
        if self.root_policy and not wins:
            selection = self.root_policy.distribution(scores,corrections)
            selected = self.root_policy.draw(selection,self.policy_rng)
        self.observer.ask(f'played {square_name(selected[0])} {square_name(selected[1])}', 'playedok')
        self.last_report = {'army': army, 'parent': parent, 'selected': selected, 'nodes': nodes,
                            'effective_samples': sum(weights)**2 / sum(w*w for w in weights),
                            'values': [{'move': move, 'value': value, 'parent_score': scores[move],
                                        'correction': corrections[move], 'sample_mean': means[move]}
                                       for move, value in choices.items()]}
        if self.diagnostic_truth:
            self.last_report.update(information_model=('diagnostic-full-enemy-ranks' if self.diagnostic_knowledge == 'all' else 'diagnostic-'+self.diagnostic_knowledge),
                                    board_hex=board_hex, truth_plies=self.truth_plies)
        if self.information_strategy:
            self.last_report.update(information_strategy=self.information_strategy,
                                    information_adjustments=[dict(move=move, adjustment=value)
                                                             for move, value in information_adjustments.items()])
        if self.root_policy:
            self.last_report['root_selection'] = selection or {'forced_immediate_win': True}
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
                self.diagnostic_event(words)
                if command == 'opponent-setup': continue
                if command == 'feldmarschall':
                    name = 'DIAGNOSTIC ' + self.diagnostic_knowledge + ' teacher' if self.diagnostic_truth else 'public-teacher'
                    print(f'id name {name}\nid author cx16-feldmarschall tools\nok', flush=True)
                elif command == 'isready': print('readyok', flush=True)
                elif command == 'seed':
                    self.rng.seed(int(words[1])); self.observer.send(line.strip())
                    if self.root_policy:
                        from root_policy import MOVE_SEED_DOMAIN
                        self.policy_rng.seed(int(words[1]) ^ MOVE_SEED_DOMAIN)
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
    parser.add_argument('--diagnostic-truth', action='store_true', help='DIAGNOSTIC ONLY: requires privileged enemy setup and a truth-enabled observer')
    parser.add_argument('--diagnostic-knowledge', choices=('all', 'flag-spy', 'flag'), default='all', help='privileged ranks exposed to the diagnostic teacher')
    parser.add_argument('--information-strategy', choices=('lifetime', 'objectives', 'followthrough'), help='fair public-input information experiment')
    parser.add_argument('--belief-model', type=Path, help='frozen public-history belief likelihood tables')
    parser.add_argument('--root-policy', type=Path, help='frozen public-score probability selection settings')
    args = parser.parse_args()
    if args.samples < 1 or args.depth < 1: parser.error('positive samples and depth required')
    bot = TeacherBot(args.observer, args.teacher, args.samples, args.depth, args.blend, args.strategic, args.context, args.replies, args.diagnostic_truth, args.diagnostic_knowledge, args.information_strategy, args.belief_model, args.root_policy)
    bot.observer.send('difficulty ' + args.difficulty)
    bot.run()
