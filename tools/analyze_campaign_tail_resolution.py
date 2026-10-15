"""Audit weighted lower-quarter resolution without outcomes or extra rollouts."""
from collections import Counter
import hashlib
import json
import math
import random
import shlex
import statistics

from ai_registry import ROOT, build_policy
from feldmarschall import Engine, square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay
from train_ai_student import sample_world


def minimum_tail_support(weights, alpha=.25):
    """Fewest distinct observations capable of filling an alpha probability tail."""
    budget = alpha*sum(weights)
    for count, weight in enumerate(sorted(weights, reverse=True), 1):
        budget -= weight
        if budget <= 1e-12:
            return count
    raise ValueError('positive probability weights required')


def run():
    folder = ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon'
    destination = folder/'cvar-tail-resolution.json'
    if destination.exists():
        raise ValueError('preserve completed research evidence')
    source_roots = folder/'quiescence-mechanism.json'
    historical = json.loads(source_roots.read_text())
    source = ROOT/historical['source']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == historical['source_sha256']
    selections = {}
    for row in historical['roots']:
        selections.setdefault((row['game'], row['army']), {})[row['ply']] = row
    executable, _ = build_policy('teacher-context-v1-normal')
    observer = Engine(shlex.quote(str(executable.parent/'observer')))
    records = []
    try:
        with Tournament(source) as tournament:
            for (game_id, army), targets in sorted(selections.items()):
                game = tournament.game(game_id)
                states, _ = replay(game)
                events = public_events(game, states)
                seed = game['seed']*2+army+1
                rng = random.Random(seed)
                for command in ('new '+('red', 'blue')[army], 'rules 0', 'difficulty normal',
                                'seed '+str(seed), 'setup '+game[('red_setup', 'blue_setup')[army]]):
                    observer.send(command)
                for ply, event in enumerate(events[:max(targets)+1]):
                    if ply % 2 == army:
                        if ply in targets:
                            public = observer.ask('public', 'public')
                            assert hashlib.sha256(public.encode()).hexdigest() == targets[ply]['public_sha256']
                            _, board, lost, _ = public.split()
                            cells = list(bytes.fromhex(board)); lost = list(bytes.fromhex(lost))
                            histories = {sq: list(map(int, observer.ask('memory '+square_name(sq), 'history').split()))
                                         for sq, cell in enumerate(cells)
                                         if cell < 254 and bool(cell & 16) != bool(army) and not cell & 32}
                            weights = [sample_world(cells, lost, histories, rng, army)[1] for _ in range(8)]
                            ess = sum(weights)**2/sum(weight*weight for weight in weights)
                            assert math.isclose(ess, targets[ply]['reports']['fixed4']['effective_samples'])
                            records.append(dict(game=game_id, army=army, family=game['family'], ply=ply,
                                                weights=weights, effective_samples=ess,
                                                max_normalized_weight=max(weights)/sum(weights),
                                                fewest_tail_observations=minimum_tail_support(weights)))
                        observer.ask('go', 'move')
                        observer.ask('played '+' '.join(event.split()[1:3]), 'playedok')
                    observer.send(event)
    finally:
        observer.close()
    summary = dict(roots=len(records), alpha=.25, samples=8,
                   effective_samples_min=min(r['effective_samples'] for r in records),
                   effective_samples_median=statistics.median(r['effective_samples'] for r in records),
                   fewest_tail_observations=dict(Counter(r['fewest_tail_observations'] for r in records)),
                   roots_with_atom_exceeding_quarter=sum(r['max_normalized_weight'] >= .25 for r in records),
                   unweighted_tail_observations=2)
    result = dict(schema='historical-cvar-tail-resolution-v1', strength_evidence=False,
                  historical_roots_sha256=hashlib.sha256(source_roots.read_bytes()).hexdigest(),
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  worlds='Exactly original weighted sampler streams and eight draws; saved effective sample sizes matched on every root.',
                  summary=summary, roots=records)
    destination.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    run()
