"""Check final Flag-loss decisions for a public one-reply survival alternative.

Concealed capture branches deliberately overapproximate remaining ranks, making
the survival certificate conservative. No concealed identity enters the checker.
"""
from collections import Counter
import copy
import json
from pathlib import Path
import time

from ai_registry import ROOT
from analyze_template_conversion import POLICY, SOURCE, OUT
from feldmarschall import Position, battle, BOMB, FLAG, SCOUT, TWO_SQUARES, UNKNOWN
from tournament_store import Tournament, replay


def flag_threats(position, army):
    flags = [sq for sq, c in enumerate(position.cells) if c and c[:2] == [army, FLAG]]
    if not flags:
        return []
    target = flags[0]
    threats = []
    last_src, last_dst, count = position.shuttle[1-army]
    for source, cell in enumerate(position.cells):
        if cell is None or cell[0] == army:
            continue
        if source == last_dst and target == last_src and count >= TWO_SQUARES:
            continue
        distance = abs(source//10-target//10)+abs(source%10-target%10)
        if distance == 1 and (cell[1] < BOMB or cell[1] == UNKNOWN and cell[2]):
            threats.append(source)
        elif cell[1] == SCOUT and (source//10 == target//10 or source%10 == target%10):
            step = (1 if source < target else -1) if source//10 == target//10 else (10 if source < target else -10)
            if all(position.cells[sq] is None for sq in range(source+step, target, step)):
                threats.append(source)
    return threats


def branches(position, move):
    source, target = move
    actor, defender = position.cells[source], position.cells[target]
    ranks = [None] if defender is None else [defender[1]] if defender[1] != UNKNOWN else list(range(10 if defender[2] else 12))
    for rank in ranks:
        candidate = copy.deepcopy(position)
        candidate.record(source, target)
        candidate.cells[source] = None
        if rank == FLAG:
            yield None  # immediate win precedes any possible enemy reply
            continue
        outcome = 'attacker' if rank is None else battle(actor[1], rank)
        if outcome == 'attacker':
            candidate.cells[target] = actor.copy()
            candidate.cells[target][2] = True
        elif outcome == 'both':
            candidate.cells[target] = None
        else:
            candidate.cells[target] = [defender[0], rank, defender[2], True]
        yield candidate


def classify(position, army, move):
    outcomes = [False if branch is None else bool(flag_threats(branch, army)) for branch in branches(position, move)]
    return dict(guarantees_no_confirmed_flag_capture=not any(outcomes),
                confirmed_flag_capture_in_every_branch=all(outcomes), branches=len(outcomes))


def main():
    import hashlib
    plan = dict(epoch=time.time(), scope='All203 completed screening losses; final own decision before actual Flag capture, no runtime use or validation tuning.',
                source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                unknown_branch_support='All12 ranks for unmoved unknown, all10 mobile ranks for moved unknown; no private identities, no learned prior, no remaining-rank exclusions.',
                certificate='Every overapproximated capture branch wins immediately or leaves no legal confirmed enemy Flag capture. Unknown moved neighbors are certain mobile threats; long Scouts must be publicly identified. Enemy two-squares restriction respected. Hidden potential Scouts remain uncertain, so this does NOT certify survival against every hidden possibility.')
    (OUT/'survival-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    records = []
    with Tournament(SOURCE) as saved:
        games = [saved.game(row['id']) for row in saved.games()]
    for game in games:
        army = int(game['blue'] == POLICY)
        if game['reason'] != 'flag' or game['result'] != ('blue', 'red')[army]:
            continue
        states, _ = replay(game)
        ply = len(game['moves'])-2
        assert ply%2 == army
        position = Position()
        position.cells = [None if c is None else [c[0], c[1] if c[0] == army or c[3] else UNKNOWN, c[2], c[3]] for c in states[ply]]
        for index, (source, target) in enumerate(game['moves'][:ply]):
            owner = index%2
            last_source, last_target, count = position.shuttle[owner]
            count = count+1 if count and source == last_target and target == last_source else 1
            position.shuttle[owner] = (source, target, count)
        moves = position.moves(army)
        selected = game['moves'][ply]
        assert selected in moves
        classified = {move: classify(position, army, move) for move in moves}
        safe = [move for move, result in classified.items() if result['guarantees_no_confirmed_flag_capture']]
        records.append(dict(game_id=game['id'], army=army, ply=ply,
                            root_confirmed_flag_threats=flag_threats(position, army),
                            selected=list(selected), selected_result=classified[selected],
                            survival_alternatives=[list(move) for move in safe], legal_moves=len(moves),
                            final_attacker_publicly_revealed_before_own_move=position.cells[game['moves'][-1][0]][3],
                            final_attacker_rank_after_disclosure=states[-2][game['moves'][-1][0]][1]))
    summary = dict(flag_losses=len(records), root_confirmed_threat=sum(bool(r['root_confirmed_flag_threats']) for r in records),
                   selected_every_branch_confirmed_loss=sum(r['selected_result']['confirmed_flag_capture_in_every_branch'] for r in records),
                   missed_public_survival_alternative=sum(r['selected_result']['confirmed_flag_capture_in_every_branch'] and bool(r['survival_alternatives']) for r in records),
                   final_attacker_already_revealed=sum(r['final_attacker_publicly_revealed_before_own_move'] for r in records),
                   final_attacker_ranks=dict(Counter(r['final_attacker_rank_after_disclosure'] for r in records)))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == plan['source_sha256']
    (OUT/'public-survival.json').write_text(json.dumps(dict(summary=summary, records=records), indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
