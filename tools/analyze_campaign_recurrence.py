"""Find public recurrence opportunities in a saved tournament, without playing.

Uniform candidate scores isolate the recurrence mechanism. This does not assert
that the original teacher's score margins would permit an escape, nor that an
escape wins. Physical setup ranks are used by the referee to replay outcomes;
the tested mechanism receives only the observer's allowed public view.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
from statistics import median

from campaign_recurrence import RecurrenceEscape, SETTINGS
from feldmarschall import LAKES, Position
from tournament_store import Tournament


def analyze(path, policy):
    rows = []
    endings = {}
    quiet_runs = []
    scored = 0
    with Tournament(path) as tournament:
        for summary in tournament.games():
            if summary['result'] == 'error':
                continue
            game = tournament.game(summary['id'])
            side = int(game['blue'] == policy)
            if game['red'] != policy and game['blue'] != policy:
                continue
            scored += 1
            endings[game['reason']] = endings.get(game['reason'], 0) + 1
            position = Position()
            position.place(0, game['red_setup'])
            position.place(1, game['blue_setup'])
            mechanism = RecurrenceEscape()
            active = penalized = quiet = longest = 0
            for ply, (src, dst) in enumerate(game['moves']):
                assert (src, dst) in position.moves(ply % 2)
                if ply % 2 == side:
                    cells = [254 if sq in LAKES else 255 if c is None else
                             (16 if c[0] else 0) | (32 if c[3] else 0)
                             | (64 if c[2] else 0)
                             | (c[1] if c[0] == side or c[3] else 12)
                             for sq, c in enumerate(position.cells)]
                    values = mechanism.adjustments(cells, side, [], {},
                                                   dict.fromkeys(position.moves(side), 0))
                    active += mechanism.last_report['active']
                    penalized += values.get((src, dst), 0) < 0
                defender = position.cells[dst]
                if defender is None:
                    quiet += 1
                    longest = max(longest, quiet)
                    position.move(src, dst)
                else:
                    quiet = 0
                    position.fight(src, dst, position.cells[src][1], defender[1])
            quiet_runs.append(longest)
            if active:
                rows.append(dict(game=game['id'], result=game['result'], reason=game['reason'],
                                 active_roots=active, recorded_move_penalized=penalized,
                                 longest_quiet_plies=longest))
    return dict(tournament=str(path), source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                policy=policy, settings=SETTINGS, scored_games=scored, endings=endings,
                note='Uniform candidate scores isolate opportunities; not a strength test or native-score gate audit.',
                median_longest_quiet_plies=median(quiet_runs), max_quiet_plies=max(quiet_runs),
                games_at_least_100_quiet_plies=sum(n >= 100 for n in quiet_runs),
                games_with_active_roots=len(rows), rows=rows,
                hypothesis='A memory of recent friendly formations can break alternating-actor loops that evade the native penalty for reversing only the previous own move.',
                primary_source=dict(title='Tabu Search—Part I', author='Fred Glover', year=1989,
                                    url='https://doi.org/10.1287/ijoc.1.3.190',
                                    application='Short-term memory and diversification inspiration; this is not an application with theoretical strength guarantees.'),
                native_source_observation=dict(file='src/core/ai.c',
                    finding='score() applies BACKTRACK only when from == last_to[army] and to == last_from[army]; alternating actors can bypass this local test. plan() has persistent goals and quiet-turn pressure already, so the new mechanism tests a different multi-move memory.'),
                limitations=[
                    'Opportunity audit uses uniform candidate scores, not original teacher corrected scores.',
                    'The six draw traces are mechanism development evidence; they must not be reused as validation seeds.',
                    'Even converting all six historical draws to wins would add only 3/276 = 1.087 percentage points; decisive games may also change.',
                    'A recurring formation may be necessary defense. The bounded penalty and score aspiration reduce but do not eliminate this risk.',
                    'Native gate audit separately tests real frozen native scores; it is still fixed-prefix evidence, not a new game outcome.'])


def native_gate_audit(path, policy):
    """Actual frozen native root scores on fixed prefixes from every draw.

    Every decision is scored to preserve native planning history and recurrence
    state. Ten predetermined mid/late prefixes per draw are reported. Recorded
    actions remain fixed; this never becomes a new strength game.
    """
    from ai_registry import build_policy
    from feldmarschall import Engine, GLYPHS, parse_square, square_name
    executable, receipt = build_policy(policy)
    observer = Engine(shlex.quote(str(executable.parent / 'observer')))
    rows = []
    totals = dict(decisions=0, active_decisions=0, decisions_with_penalized_moves=0)
    try:
        with Tournament(path) as tournament:
            games = [tournament.game(g['id']) for g in tournament.games()
                     if g['result'] == 'draw' and policy in (g['red'], g['blue'])]
        for game in games:
            side = int(game['blue'] == policy)
            observer.send('new ' + ('red', 'blue')[side])
            observer.send('rules 0')
            observer.send('difficulty normal')
            observer.send('seed ' + str(game['seed']))
            observer.send('setup ' + game[('red_setup', 'blue_setup')[side]])
            position = Position()
            position.place(0, game['red_setup'])
            position.place(1, game['blue_setup'])
            module = RecurrenceEscape()
            selected_plies = {100 + 90*n + side for n in range(10)}
            for ply, (src, dst) in enumerate(game['moves']):
                if ply % 2 == side:
                    army, public, lost, shuttle = observer.ask('public', 'public').split()
                    observer.send('ranked')
                    scores = {}
                    while True:
                        words = observer.read().split()
                        if words[0] == 'candidate':
                            scores[tuple(map(int, words[1:3]))] = int(words[3])
                        elif words[0] == 'move':
                            parent = tuple(map(parse_square, words[1:3]))
                            break
                        elif words[0] == 'error':
                            raise ValueError(words)
                    assert (src, dst) in scores
                    values = module.adjustments(list(bytes.fromhex(public)), side,
                                                list(bytes.fromhex(lost)), {}, scores)
                    totals['decisions'] += 1
                    totals['active_decisions'] += module.last_report['active']
                    totals['decisions_with_penalized_moves'] += any(values.values())
                    if ply in selected_plies:
                        winner = max(scores, key=lambda m: (scores[m]+values[m], m == parent,
                                                            -m[0], -m[1]))
                        rows.append(dict(game=game['id'], side=side, ply=ply,
                                         **module.last_report, parent=parent,
                                         corrected_native_choice=winner,
                                         changes_native_choice=winner != parent,
                                         candidates=[dict(move=m, score=scores[m], adjustment=values[m])
                                                     for m in scores]))
                    observer.ask('played ' + square_name(src) + ' ' + square_name(dst), 'playedok')
                a, d = position.cells[src], position.cells[dst]
                event = ('moved ' + square_name(src) + ' ' + square_name(dst) if d is None else
                         'battle ' + square_name(src) + ' ' + square_name(dst)
                         + ' ' + GLYPHS[a[1]] + ' ' + GLYPHS[d[1]])
                if d is None:
                    position.move(src, dst)
                else:
                    position.fight(src, dst, a[1], d[1])
                observer.send(event)
    finally:
        observer.close()
    return dict(kind='frozen-native-score-gate-forced-prefix-diagnostic', strength_evidence=False,
                public_inputs='own setup and public moved/battle events; no enemy setup or physical board',
                tournament=str(path), tournament_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                policy=policy, native_build_receipt=receipt, settings=SETTINGS,
                sample_rule='Own-side ply offset plus 100,190,280,370,460,550,640,730,820,910 in every scored draw',
                **totals, sampled_decisions=len(rows),
                sampled_active=sum(r['active'] for r in rows),
                sampled_changed_native_choice=sum(r['changes_native_choice'] for r in rows), rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tournament', type=Path)
    parser.add_argument('--policy', default='teacher-context-v1-normal')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--native-gate', action='store_true')
    args = parser.parse_args()
    function = native_gate_audit if args.native_gate else analyze
    result = json.dumps(function(args.tournament, args.policy), indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result)
    else:
        print(result, end='')
