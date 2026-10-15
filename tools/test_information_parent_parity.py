"""Forced-prefix diagnostic parity of old/new native Context Teacher parents.

This is not a strength test. Both current adapters have the information module
disabled; only their frozen native observer/teacher binaries differ. Replay
code derives public battle events, but bots receive only their own initial
setup plus those public events. No enemy setup or referee board is passed in.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from ai_registry import ROOT, build_policy, get_policy
from feldmarschall import GLYPHS, square_name
from teacher_bot import TeacherBot
from tournament_store import Tournament, replay


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def public_events(game, states):
    events = []
    for ply, (src, dst) in enumerate(game['moves']):
        squares = square_name(src) + ' ' + square_name(dst)
        source, target = states[ply][src], states[ply][dst]
        events.append('moved ' + squares if target is None else
                      'battle ' + squares + ' ' + GLYPHS[source[1]] + ' ' + GLYPHS[target[1]])
    return events


def run(tournament_path, candidate, samples=2, decisions=140, allowed_extra_defines=()):
    if decisions < 100:
        raise ValueError('parity audit requires at least 100 decisions')
    baseline = 'teacher-context-v1-normal'
    specs = [get_policy(p) for p in (baseline, candidate)]
    extra_defines=set(specs[1]['defines'])-set(specs[0]['defines'])
    assert extra_defines <= set(allowed_extra_defines)
    assert specs[0]['defines'] == [d for d in specs[1]['defines'] if d not in extra_defines]
    assert specs[0]['teacher_defines'] == specs[1]['teacher_defines']
    bundles = [build_policy(p) for p in (baseline, candidate)]
    # Use longest retained game per family: this covers several phases and
    # includes public movement and combat history while keeping runtime bounded.
    with Tournament(tournament_path) as tournament:
        longest = {}
        for row in tournament.games():
            if row['result'] == 'error' or row['plies'] < 20:
                continue
            if row['family'] not in longest or row['plies'] > longest[row['family']]['plies']:
                longest[row['family']] = row
        games = [tournament.game(row['id']) for _, row in sorted(longest.items())]
    if not games:
        raise ValueError('no sufficiently long complete games')
    bots = [TeacherBot(executable.parent / 'observer', executable.parent / 'teacher',
                       samples=samples, depth=4, blend='correction', strategic=True,
                       context=True, information_strategy=None)
            for executable, _ in bundles]
    rng = random.Random(1980103)
    tested, orientations, families = [], Counter(), Counter()
    try:
        quota = (decisions + 2 * len(games) - 1) // (2 * len(games))
        for game in games:
            states, _ = replay(game)
            events = public_events(game, states)
            for army in (0, 1):
                eligible = list(range(army, min(len(events), 500), 2))
                selected = set(rng.sample(eligible, min(quota, len(eligible))))
                if not selected:
                    continue
                for bot in bots:
                    bot.rng.seed(game['seed'])
                    bot.observer.send('new ' + ('red', 'blue')[army])
                    bot.observer.send('rules 0')
                    bot.observer.send('difficulty normal')
                    bot.observer.send('seed ' + str(game['seed']))
                    bot.observer.send('setup ' + game[('red_setup', 'blue_setup')[army]])
                for ply, event in enumerate(events[:max(selected)+1]):
                    if ply % 2 == army:
                        if ply in selected:
                            public = [b.observer.ask('public', 'public') for b in bots]
                            assert public[0] == public[1], (game['id'], army, ply, 'public')
                            strategies = [b.observer.ask('strategy', 'strategy') for b in bots]
                            assert strategies[0] == strategies[1], (game['id'], army, ply, 'strategy')
                            chosen = [bot.choose() for bot in bots]
                            assert chosen[0] == chosen[1], (game['id'], army, ply, chosen)
                            reports = [bot.last_report for bot in bots]
                            assert reports[0] == reports[1], dict(game=game['id'], army=army,
                                                                  ply=ply, old=reports[0], new=reports[1])
                            tested.append(dict(game=game['id'], family=game['family'], army=army,
                                               ply=ply, selected=chosen[0],
                                               report_sha256=signature(reports[0])))
                            orientations[army] += 1
                            families[game['family']] += 1
                        else:
                            # Populate ordinary native strategic history even
                            # when no teacher decision is sampled at this turn.
                            native = [b.observer.ask('go', 'move') for b in bots]
                            assert native[0] == native[1], (game['id'], army, ply, 'native')
                        # Prefix action is fixed by retained evidence, rather
                        # than following either tested choice into a new game.
                        for bot in bots:
                            bot.observer.ask('played ' + ' '.join(event.split()[1:3]), 'playedok')
                    for bot in bots:
                        bot.observer.send(event)
        assert len(tested) >= decisions, (len(tested), decisions)
        assert all(orientations[army] >= 50 for army in (0, 1)), orientations
    finally:
        for bot in bots:
            bot.close()
    return dict(kind='forced-public-prefix-parent-parity-diagnostic', strength_evidence=False,
                passed=True, tested_decisions=len(tested), orientations=dict(orientations),
                families=dict(families), samples=samples, depth=4, blend='correction',
                strategic=True, context=True, information_strategy=None,
                compared='chosen action, entire last_report, root public board and strategic context',
                public_input='own setup and public moves/battles only; no enemy setup',
                tournament=str(tournament_path),
                tournament_sha256=hashlib.sha256(tournament_path.read_bytes()).hexdigest(),
                baseline=baseline, candidate_parent=candidate,
                allowed_extra_defines=list(allowed_extra_defines),actual_extra_defines=sorted(extra_defines),
                native_receipts=[receipt for _, receipt in bundles], decisions=tested)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tournament', type=Path,
                        default=ROOT/'docs/ai-information-pilot-2026-10-15/validation/teacher-context-v1-normal.fmtour')
    parser.add_argument('--candidate', default='teacher-info-corridor-v1-normal')
    parser.add_argument('--samples', type=int, default=2)
    parser.add_argument('--decisions', type=int, default=140)
    args = parser.parse_args()
    print(json.dumps(run(args.tournament, args.candidate, args.samples, args.decisions), indent=2))
