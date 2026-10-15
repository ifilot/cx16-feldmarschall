"""Coverage of the frozen two-turn interceptor in template screening losses."""
from collections import Counter
import hashlib
import json
import time

from analyze_template_conversion import POLICY, SOURCE, OUT
from campaign_flag_guard import evaluate
from feldmarschall import Position, UNKNOWN
from tournament_store import Tournament, replay


def main():
    plan = dict(epoch=time.time(), source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                sample='Last four own decisions in all Flag-capture losses of the400 completed native-template screening games.',
                comparison='Existing public-flag-interceptor-v1, equal zero baseline scores to identify structural repair opportunity. Test the actual saved quiet move against the repair set; captures retain existing control.',
                boundary='Public ranks/movement and own setup only. This is an opportunity audit, not a replacement move test or a strength claim.')
    (OUT/'interception-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    records = []
    with Tournament(SOURCE) as saved:
        games = [saved.game(row['id']) for row in saved.games()]
    for game in games:
        army = int(game['blue'] == POLICY)
        if game['reason'] != 'flag' or game['result'] != ('blue', 'red')[army]:
            continue
        states, _ = replay(game)
        for ply in range(max(army, len(game['moves'])-8), len(game['moves'])-1, 2):
            assert ply%2 == army
            position = Position()
            position.cells = [None if c is None else [c[0], c[1] if c[0] == army or c[3] else UNKNOWN, c[2], c[3]] for c in states[ply]]
            for index, (source, target) in enumerate(game['moves'][:ply]):
                owner = index%2
                last_source, last_target, count = position.shuttle[owner]
                count = count+1 if count and source == last_target and target == last_source else 1
                position.shuttle[owner] = (source, target, count)
            # Native public protocol packs low type nibble, owner, disclosure, moved.
            cells = [255 if c is None else c[1] | c[0]*16 | int(c[3])*32 | int(c[2])*64 for c in position.cells]
            shuttle = [position.shuttle[a][i] for i in range(3) for a in (0, 1)]
            moves = {move: 0. for move in position.moves(army)}
            adjustments, report = evaluate(cells, army, None, None, moves, shuttle)
            selected = game['moves'][ply]
            assert selected in moves
            records.append(dict(game_id=game['id'], ply=ply, turns_before_last=(len(game['moves'])-2-ply)//2,
                                selected=list(selected), selected_is_quiet=position.cells[selected[1]] is None,
                                selected_demoted=adjustments[selected] < 0, report=report))
    affected = [r for r in records if r['selected_demoted']]
    summary = dict(roots=len(records), reasons=dict(Counter(r['report']['reason'] for r in records)),
                   actual_quiet_move_would_be_demoted=len(affected), affected_games=len({r['game_id'] for r in affected}),
                   demoted_by_turns_before_last=dict(Counter(r['turns_before_last'] for r in affected)))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == plan['source_sha256']
    (OUT/'interception-opportunities.json').write_text(json.dumps(dict(summary=summary, records=records), indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
