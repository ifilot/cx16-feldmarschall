"""Public two-turn interceptor coverage before historical Flag losses.

The final captor identity selects descriptive prefixes offline. Coverage itself
uses a masked public board, exact own ranks, and only a disclosed intruder rank.
No strategy implementation or new match is produced by this analysis.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from feldmarschall import FLAG, GLYPHS, Position, battle
from tournament_store import Tournament, replay


from campaign_flag_guard import clone, coverage, public_position


def analyze(path, policy):
    counters = Counter()
    windows = Counter()
    rows = []
    with Tournament(path) as tournament:
        games = [tournament.game(g['id']) for g in tournament.games()
                 if g['result'] != 'error' and g['reason'] == 'flag'
                 and policy in (g['red'], g['blue'])
                 and g['result'] != ('red' if g['red'] == policy else 'blue')]
    for game in games:
        side = int(game['blue'] == policy)
        states, _ = replay(game)
        position = Position()
        position.place(0, game['red_setup'])
        position.place(1, game['blue_setup'])
        identities = {sq: sq for sq, c in enumerate(position.cells) if c}
        ids = []
        positions = []
        for src, dst in game['moves']:
            ids.append(dict(identities))
            positions.append(clone(position))
            a, d = position.cells[src], position.cells[dst]
            if d is None:
                position.move(src, dst)
                identities[dst] = identities.pop(src)
            else:
                outcome = battle(a[1], d[1])
                identity = identities.pop(src)
                if outcome == 'attacker':
                    identities[dst] = identity
                elif outcome == 'both':
                    identities.pop(dst)
                position.fight(src, dst, a[1], d[1])
        last = len(game['moves'])-1
        killer_id = ids[last][game['moves'][-1][0]]
        game_has_known_close = False
        game_has_reserve_abandonment = False
        for turns in range(1, 7):
            ply = last-(2*turns-1)
            if ply < 0:
                continue
            root = positions[ply]
            intruder = next(sq for sq, identity in ids[ply].items() if identity == killer_id)
            enemy = root.cells[intruder]
            flag = next(sq for sq, c in enumerate(root.cells) if c and c[0] == side and c[1] == FLAG)
            distance = abs(intruder//10-flag//10) + abs(intruder % 10-flag % 10)
            windows[f'{turns}_turns_rank_disclosed'] += bool(enemy[3])
            windows[f'{turns}_turns_disclosed_distance2or3'] += bool(enemy[3]) and distance in (2, 3)
            if not enemy[3]:
                continue
            masked = public_position(root, side)
            before = coverage(masked, side, intruder)
            if before['immediate'] or not before['approaches']:
                continue
            game_has_known_close = True
            counters['prefixes_with_public_two_turn_approach'] += 1
            counters['prefixes_already_covered'] += before['covered']
            src, dst = game['moves'][ply]
            row = dict(game=game['id'], family=game['family'], own_turns_before_capture=turns,
                       decision_ply=ply, intruder=intruder, intruder_public_rank=GLYPHS[enemy[1]],
                       flag=flag, manhattan_distance=distance, recorded_move=[src, dst],
                       recorded_move_is_quiet=root.cells[dst] is None, before=before)
            if root.cells[dst] is None:
                after = clone(masked)
                after.move(src, dst)
                after_report = coverage(after, side, intruder)
                row['after_recorded_quiet_move'] = after_report
                abandoned = before['covered'] and not after_report['covered']
                row['abandons_interception_coverage'] = abandoned
                counters['quiet_moves_abandoning_coverage'] += abandoned
                game_has_reserve_abandonment |= abandoned
            defenses = []
            for a, b in masked.moves(side):
                if masked.cells[b] is not None:
                    continue
                branch = clone(masked)
                branch.move(a, b)
                report = coverage(branch, side, intruder)
                if report['covered']:
                    defenses.append(dict(move=[a, b], guard_rank=GLYPHS[masked.cells[a][1]],
                                         eliminates_approach=not report['approaches'],
                                         guard_squares=report['guards'],
                                         covers_every_disclosed_intruder=all(coverage(branch, side, sq)['covered']
                                             for sq, c in enumerate(branch.cells) if c and c[0] != side
                                             and c[3] and c[1] < 10)))
            row['quiet_defensive_deployments'] = defenses
            counters['prefixes_with_covering_alternative'] += bool(defenses)
            counters['quiet_prefixes_with_covering_alternative'] += bool(defenses) and row['recorded_move_is_quiet']
            counters['prefixes_with_alternative_covering_all_disclosed_intruders'] += any(d['covers_every_disclosed_intruder'] for d in defenses)
            rows.append(row)
        counters['games_with_public_two_turn_approach'] += game_has_known_close
        counters['games_with_quiet_abandonment'] += game_has_reserve_abandonment
    return dict(kind='public-flag-interceptor-opportunity-audit', strength_evidence=False,
                tournament=str(path), tournament_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                policy=policy, flag_losses=len(games), counters=dict(counters), windows=dict(windows), rows=rows,
                analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                runtime_module_sha256=hashlib.sha256(Path(__file__).with_name('campaign_flag_guard.py').read_bytes()).hexdigest(),
                unique_games_with_covering_alternative=len({r['game'] for r in rows if r['quiet_defensive_deployments']}),
                unique_games_with_alternative_covering_all_disclosed_intruders=len({r['game'] for r in rows
                    if any(d['covers_every_disclosed_intruder'] for d in r['quiet_defensive_deployments'])}),
                scope='At each of the last six defender decisions, label the eventual captor offline; local coverage uses only its disclosed rank and the masked public board.',
                source_observations=['ai.c flag_threats detects one-move attacks and applies a900-point defense difference; it does not represent an interceptor reserve against a two-enemy-move approach.',
                                     'ai.c plan may pursue enemies within distance2of own Flag but does not prove future interception coverage.',
                                     'ai_mission.c cooperatively approaches enemy Flag/Bomb objectives; its guard terminology concerns enemy fortification, not an own-Flag reserve role.'],
                proposal='A two-turn interception mission: identify every disclosed intruder that can reach a Flag attack in one advance, and retain/deploy a friendly piece that can remove it afterward. Rank-asymmetric interception is distinguished from simply occupying its route. Do not promise protection when no legal coverage-restoring action exists.',
                limits=['A local two-turn response against one disclosed intruder is not a full minimax proof against all enemy moves.',
                        'Covered interception may require a material sacrifice; it only establishes removal of the immediate local Flag attacker.',
                        'This retrospective cohort is mechanism development evidence, not fresh strength validation.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tournament', type=Path)
    parser.add_argument('--policy', default='teacher-context-v1-normal')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    text = json.dumps(analyze(args.tournament, args.policy), indent=2)+'\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end='')
