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
    def __init__(self, observer, teacher, samples=8, depth=3, blend='raw', strategic=False, context=False, replies=None, diagnostic_truth=False, diagnostic_knowledge='all', information_strategy=None, belief_model=None, root_policy=None, world_sampling=None, campaign_strategy=None, paired_confidence=False, adaptive_depth=False, joint_belief_model=None, correction_anchor=None, belief_sweeps=None, root_capture_mode=None):
        if belief_sweeps is not None and (not belief_model or blend != 'correction' or diagnostic_truth or information_strategy or root_policy or world_sampling or campaign_strategy or paired_confidence or adaptive_depth or joint_belief_model or correction_anchor):
            raise ValueError('isolate honest rank-swap beliefs with a frozen belief model')
        self.belief_sweeps = belief_sweeps
        if root_capture_mode not in (None, 'counts', 'joint'):
            raise ValueError('unknown root capture belief mode')
        if root_capture_mode and (not joint_belief_model or blend != 'correction' or diagnostic_truth or information_strategy or root_policy or world_sampling or campaign_strategy or paired_confidence or adaptive_depth or correction_anchor or belief_sweeps is not None):
            raise ValueError('isolate honest root capture beliefs with a frozen joint model')
        self.root_capture_mode = root_capture_mode
        if correction_anchor not in (None, 'parent'):
            raise ValueError('unknown correction anchor')
        if correction_anchor and (diagnostic_truth or information_strategy or root_policy or world_sampling or campaign_strategy or paired_confidence or belief_model or adaptive_depth or joint_belief_model or blend != 'correction'):
            raise ValueError('isolate honest legal-parent correction anchor')
        self.correction_anchor = correction_anchor
        if world_sampling not in (None, 'latin', 'uniform') or campaign_strategy not in (None, 'activation', 'recurrence', 'flag-interceptor'):
            raise ValueError('unknown campaign experiment')
        if (world_sampling or campaign_strategy or paired_confidence) and (diagnostic_truth or information_strategy or root_policy):
            raise ValueError('campaign experiments require isolated honest teacher')
        if campaign_strategy and (world_sampling or belief_model or paired_confidence):
            raise ValueError('isolate campaign strategic hypothesis')
        if paired_confidence and (world_sampling or belief_model or blend != 'correction'):
            raise ValueError('isolate paired uncertainty correction experiment')
        if adaptive_depth and (diagnostic_truth or information_strategy or root_policy or world_sampling or campaign_strategy or paired_confidence or belief_model):
            raise ValueError('isolate honest adaptive depth experiment')
        if joint_belief_model and (diagnostic_truth or information_strategy or root_policy or world_sampling or campaign_strategy or paired_confidence or belief_model or adaptive_depth):
            raise ValueError('isolate honest joint setup belief experiment')
        self.joint_model = None
        if joint_belief_model:
            from campaign_joint_beliefs import JointSetupBeliefs
            self.joint_model = JointSetupBeliefs.load(joint_belief_model)
        self.adaptive_depth = adaptive_depth
        self.campaign_strategy = campaign_strategy
        self.campaign_module = None
        if campaign_strategy == 'activation':
            self.campaign_module = importlib.import_module('campaign_strategy')
        elif campaign_strategy == 'recurrence':
            from campaign_recurrence import RecurrenceEscape
            self.campaign_module = RecurrenceEscape()
        elif campaign_strategy == 'flag-interceptor':
            self.campaign_module = importlib.import_module('campaign_flag_guard')
        self.paired_confidence = paired_confidence
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
        self.world_sampler = self.belief_model
        if self.joint_model:
            self.world_sampler = self.joint_model
        if belief_sweeps is not None:
            from campaign_swap_beliefs import SwapBeliefs
            self.world_sampler = SwapBeliefs(self.belief_model, sweeps=belief_sweeps)
        if world_sampling:
            from campaign_sampling import StratifiedSampler, UniformSampler
            if world_sampling == 'uniform' and self.belief_model:
                raise ValueError('uniform averaging isolates handwritten behavioral weights')
            self.world_sampler = (StratifiedSampler(self.belief_model) if world_sampling == 'latin' else UniformSampler())
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
        search_depth = self.depth
        if self.adaptive_depth:
            from campaign_depth import depth_for_actions
            search_depth = depth_for_actions(self.depth, len(scores))
        weights, nodes = [], 0
        sampled = (self.world_sampler.sample_worlds(cells, list(bytes.fromhex(lost_hex)),
                   histories, self.rng, army, self.samples) if self.world_sampler else None)
        world_results = []
        for sample in range(self.samples):
            world, weight = (sampled[sample] if sampled is not None else
                             sample_world(cells, list(bytes.fromhex(lost_hex)), histories, self.rng, army))
            suffix = ' ' + context if self.context else ''
            self.teacher.stdin.write(f'search {army} {search_depth} {bytes(world).hex()} {shuttle}{suffix}\n'); self.teacher.stdin.flush()
            values = {}
            while True:
                words = self.teacher.stdout.readline().split()
                if not words: raise ValueError('teacher stopped')
                if words[0] == 'error': raise ValueError(words)
                if words[0] == 'done':
                    nodes += int(words[1]); reference = int(words[2]); break
                if words[0] == 'action': values[tuple(map(int, words[1:3]))] = tuple(map(int, words[3:5]))
            if set(values) != set(scores): raise ValueError('sampled world changes root legal actions')
            if self.paired_confidence:
                world_results.append((dict(values), reference))
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
        anchor_report = None
        if self.correction_anchor:
            from campaign_anchor import choices as anchored_choices
            choices, corrections, anchor_report = anchored_choices(scores, credit, totals, weights, parent)
        capture_report = None
        if self.root_capture_mode:
            from campaign_belief_values import adjustments as capture_adjustments
            changes, capture_report = capture_adjustments(cells[:],army,list(bytes.fromhex(lost_hex)),
                                                          histories,dict(scores),self.joint_model,self.root_capture_mode)
            for move, value in changes.items(): choices[move] += value
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
        campaign_adjustments = {}
        campaign_diagnostics = None
        if self.campaign_strategy:
            if self.campaign_strategy=='flag-interceptor':
                campaign_adjustments, campaign_diagnostics = self.campaign_module.evaluate(
                    cells[:],army,list(bytes.fromhex(lost_hex)),histories,dict(choices),shuttle)
            else:
                campaign_adjustments = self.campaign_module.adjustments(cells[:], army, list(bytes.fromhex(lost_hex)), histories, dict(choices))
            if any(move not in choices or not math.isfinite(value) for move, value in campaign_adjustments.items()):
                raise ValueError('invalid campaign adjustment')
            for move, value in campaign_adjustments.items():
                choices[move] += value
        # Keep unequivocal immediate victories at their native priority.
        wins = [move for move, score in scores.items() if score >= 30000]
        selected = parent if parent in wins else max(wins or choices, key=lambda move: (choices[move], move == parent, -move[0], -move[1]))
        selection = None
        if self.root_policy and not wins:
            selection = self.root_policy.distribution(scores,corrections)
            selected = self.root_policy.draw(selection,self.policy_rng)
        if self.paired_confidence:
            from campaign_search import paired_selection
            selected, selection = paired_selection(scores, credit, parent, world_results, weights)
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
        if self.paired_confidence:
            self.last_report['paired_selection'] = selection
        if self.adaptive_depth:
            self.last_report['adaptive_depth'] = search_depth
        if self.correction_anchor:
            self.last_report['correction_anchor'] = anchor_report
        if self.belief_sweeps is not None:
            self.last_report['swap_beliefs'] = self.world_sampler.last_report
        if self.root_capture_mode:
            self.last_report['root_capture_beliefs'] = capture_report
        if self.campaign_strategy:
            self.last_report['campaign_adjustments'] = [dict(move=m, adjustment=v) for m,v in campaign_adjustments.items()]
            if self.campaign_strategy == 'recurrence':
                self.last_report['recurrence'] = self.campaign_module.last_report
            if self.campaign_strategy == 'flag-interceptor':
                self.last_report['flag_interceptor'] = campaign_diagnostics
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
                if self.joint_model:
                    self.joint_model.observe(words)
                if command == 'new' and self.campaign_strategy == 'recurrence':
                    self.campaign_module.reset()
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
    parser.add_argument('--world-sampling', choices=('latin','uniform'), help='public-world sampling experiment')
    parser.add_argument('--campaign-strategy', choices=('activation','recurrence','flag-interceptor'), help='public-board strategic experiment')
    parser.add_argument('--paired-confidence', action='store_true', help='paired one-standard-error search override experiment')
    parser.add_argument('--adaptive-depth', action='store_true', help='eight-ply planning at roots with at most twelve public legal actions')
    parser.add_argument('--joint-belief-model', type=Path, help='frozen correlated Flag/Bomb setup-style prior with public event memory')
    parser.add_argument('--correction-anchor', choices=('parent',), help='center clipped continuation corrections on the legal native fallback')
    parser.add_argument('--belief-sweeps', type=int, help='independent rank-swap rejuvenation sweeps for the frozen belief model; zero is an unweighted proposal control')
    parser.add_argument('--root-capture-mode', choices=('counts','joint'), help='replace hidden-capture material expectation using public rank marginals')
    args = parser.parse_args()
    if args.samples < 1 or args.depth < 1: parser.error('positive samples and depth required')
    bot = TeacherBot(args.observer, args.teacher, samples=args.samples, depth=args.depth,
                     blend=args.blend, strategic=args.strategic, context=args.context, replies=args.replies,
                     diagnostic_truth=args.diagnostic_truth, diagnostic_knowledge=args.diagnostic_knowledge,
                     information_strategy=args.information_strategy, belief_model=args.belief_model,
                     root_policy=args.root_policy, world_sampling=args.world_sampling,
                     campaign_strategy=args.campaign_strategy, paired_confidence=args.paired_confidence,
                     adaptive_depth=args.adaptive_depth, joint_belief_model=args.joint_belief_model,
                     correction_anchor=args.correction_anchor, belief_sweeps=args.belief_sweeps,
                     root_capture_mode=args.root_capture_mode)
    bot.observer.send('difficulty ' + args.difficulty)
    bot.run()
