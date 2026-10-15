"""Replay the fixed public repair-opportunity prefixes through the runtime.

Uniform existing move scores isolate mission activation; no choices are played
and no strength result follows. Timings describe this host and these prefixes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time

from campaign_flag_guard import evaluate
from feldmarschall import LAKES, Position
from tournament_store import Tournament


def run(source, opportunities, policy='teacher-context-v1-normal'):
    evidence = json.loads(opportunities.read_text())
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    assert evidence['tournament_sha256'] == source_sha
    selected = {}
    for row in evidence['rows']:
        if row['quiet_defensive_deployments']:
            selected.setdefault(row['game'], set()).add(row['decision_ply'])
    measurements = []
    with Tournament(source) as tournament:
        for game_id, plies in selected.items():
            game = tournament.game(game_id)
            side = int(game['blue'] == policy)
            position = Position()
            position.place(0, game['red_setup'])
            position.place(1, game['blue_setup'])
            for ply, (src, dst) in enumerate(game['moves']):
                if ply in plies:
                    cells = [254 if sq in LAKES else 255 if c is None else
                             (c[1] if c[0] == side or c[3] else 12)
                             | (16 if c[0] else 0) | (64 if c[2] else 0) | (32 if c[3] else 0)
                             for sq, c in enumerate(position.cells)]
                    shuttle = bytes([position.shuttle[a][0] if position.shuttle[a][2] else 255 for a in (0, 1)]
                                    + [position.shuttle[a][1] if position.shuttle[a][2] else 255 for a in (0, 1)]
                                    + [position.shuttle[a][2] for a in (0, 1)]).hex()
                    moves = dict.fromkeys(position.moves(side), 0)
                    start = time.perf_counter()
                    changes, report = evaluate(cells, side, [], {}, moves, shuttle)
                    elapsed = time.perf_counter()-start
                    assert all(changes[m] == 0 for m in moves if position.cells[m[1]] is not None)
                    assert (changes, report) == evaluate(cells, side, [], {}, moves, shuttle)
                    measurements.append(dict(game=game_id, ply=ply, milliseconds=elapsed*1000,
                                             candidates=len(moves), active=report['active'],
                                             reason=report['reason'], demoted=report['demoted_moves']))
                a, d = position.cells[src], position.cells[dst]
                if d is None:
                    position.move(src, dst)
                else:
                    position.fight(src, dst, a[1], d[1])
                if ply >= max(plies):
                    break
    return dict(kind='flag-interceptor-historical-public-root-runtime-audit', strength_evidence=False,
                tournament_sha256=source_sha, opportunities_sha256=hashlib.sha256(opportunities.read_bytes()).hexdigest(),
                uniform_scores=True, sampled_roots=len(measurements), active=sum(x['active'] for x in measurements),
                repeated_calls_identical=True, capture_scores_unchanged=True,
                median_milliseconds=statistics.median(x['milliseconds'] for x in measurements),
                maximum_milliseconds=max(x['milliseconds'] for x in measurements), rows=measurements,
                module_sha256=hashlib.sha256(Path(__file__).with_name('campaign_flag_guard.py').read_bytes()).hexdigest(),
                audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tournament', type=Path, required=True)
    parser.add_argument('--opportunities', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(run(args.tournament, args.opportunities), indent=2)+'\n')
