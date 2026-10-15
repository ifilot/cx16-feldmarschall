"""Public inference and conversion diagnostics on completed screening games.

Full opponent setups are used only after prediction for offline correctness.
This never feeds a policy or changes a validation cohort.
"""
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import time

from ai_registry import ROOT
from campaign_template_beliefs import TemplateMixtureBeliefs
from feldmarschall import GLYPHS, LAKES, setup_squares
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay

POLICY = 'student-template-flag-bomb-v1-normal'
SOURCE = ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior'/f'{POLICY}.fmtour'
OUT = ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-conversion-screen'


def flag_prediction(model):
    """Original-square probabilities from the model's public history alone."""
    known = {o: r for (owner, o), r in model.known.items() if owner != model.army}
    moved = {o for owner, o in model.moved if owner != model.army}
    weights, _ = model.posterior()
    disclosed = [o for o, r in known.items() if r == 11]
    if disclosed:
        return [float(o == disclosed[0]) for o in range(40)], True
    unknown = [o for o in range(40) if o not in known and o not in moved]
    assert unknown
    return [sum(w for w, t in zip(weights[:-1], model.templates) if t[o] == 11)
            + (weights[-1]/len(unknown) if o in unknown else 0.) for o in range(40)], False


def optimistic_miner_distance(model, flag_origin):
    """Lower bound: ignore every mobile blocker/guard; respect our immobiles."""
    target = setup_squares(1-model.army)[flag_origin]
    miners = [sq for sq, token in model.tokens.items()
              if token[0] == model.army and model.known[token] == 7]
    # PIECE_MINER is glyph8 / index7. No concealed enemy identity is consulted.
    blocked = set(LAKES) | {sq for sq, token in model.tokens.items()
                           if token[0] == model.army and model.known[token] >= 10}
    queue = deque((sq, 0) for sq in miners)
    visited = set(miners)
    while queue:
        sq, distance = queue.popleft()
        if sq == target:
            return len(miners), distance
        for neighbor in (sq-10, sq+10, sq-1, sq+1):
            if not 0 <= neighbor < 100 or abs(neighbor//10-sq//10)+abs(neighbor%10-sq%10) != 1:
                continue
            if neighbor not in blocked and neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance+1))
    return len(miners), None


def main():
    OUT.mkdir(exist_ok=False, parents=True)
    source_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    plan = dict(source=str(SOURCE.relative_to(ROOT)), source_sha256=source_sha,
                frozen_before_analysis_epoch=time.time(), selection='All400 completed native template screening attempts, including unscored errors. No validation games.',
                confidence_threshold=.9, gate='First own decision with inferred Flag probability>=0.9 before public Flag disclosure.',
                scope='Descriptive screening diagnostics; no causal or playing-strength claim. Truth used only for offline correctness after prediction.',
                path_bound='Ignore all mobile blockers/guards; block lakes and own Bomb/Flag. Finite distance does not prove a safe route or a win.')
    (OUT/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    records = []
    with Tournament(SOURCE) as saved:
        assert saved.metadata()['status'] == 'complete'
        games = [saved.game(row['id']) for row in saved.games()]
    assert len(games) == 400
    for game in games:
        army = int(game['blue'] == POLICY)
        model = TemplateMixtureBeliefs()
        model.observe(['new', ('red', 'blue')[army]])
        model.observe(['setup', game[('red_setup', 'blue_setup')[army]]])
        states, _ = replay(game)
        events = public_events(game, states)
        outcome = 'error' if game['result'] == 'error' else 'draw' if game['result'] == 'draw' else 'win' if game['result'] == ('red', 'blue')[army] else 'loss'
        record = dict(game_id=game['id'], pair_id=game['pair_id'], army=army, outcome=outcome,
                      reason=game['reason'], plies=game['plies'], first_confident=None,
                      first_flag_disclosure=None)
        for ply, event in enumerate(events):
            if ply%2 == army:
                probabilities, disclosed = flag_prediction(model)
                assert abs(sum(probabilities)-1) < 1e-9
                if disclosed and record['first_flag_disclosure'] is None:
                    record['first_flag_disclosure'] = ply
                if not disclosed and record['first_confident'] is None and max(probabilities) >= .9:
                    chosen = max(range(40), key=lambda o: probabilities[o])
                    miners, lower_bound = optimistic_miner_distance(model, chosen)
                    # Prediction and reachability above see no opponent setup.
                    true_origin = game[('blue_setup', 'red_setup')[army]].index('F')
                    record['first_confident'] = dict(ply=ply, probability=probabilities[chosen],
                        predicted_origin=chosen, correct=chosen == true_origin,
                        own_miners=miners, optimistic_miner_distance=lower_bound)
            model.observe(event.split())
        records.append(record)
    confident = [r for r in records if r['first_confident'] is not None]
    correct = [r for r in confident if r['first_confident']['correct']]
    summary = dict(attempts=len(records), outcomes=dict(Counter(r['outcome'] for r in records)),
                   confident_before_disclosure=len(confident), correct_confident=len(correct),
                   confident_outcomes=dict(Counter(r['outcome'] for r in confident)),
                   correct_confident_outcomes=dict(Counter(r['outcome'] for r in correct)),
                   wrong_confident_outcomes=dict(Counter(r['outcome'] for r in confident if not r['first_confident']['correct'])),
                   no_miners_at_correct_confidence=sum(r['first_confident']['own_miners'] == 0 for r in correct),
                   no_optimistic_miner_route_at_correct_confidence=sum(r['first_confident']['optimistic_miner_distance'] is None for r in correct),
                   endings={outcome: dict(Counter(r['reason'] for r in records if r['outcome'] == outcome)) for outcome in ('win', 'draw', 'loss', 'error')})
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_sha
    (OUT/'result.json').write_text(json.dumps(dict(summary=summary, records=records), indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
