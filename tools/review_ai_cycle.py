"""Extract public failure cases from the new cycle's Classic baseline tournaments."""
from collections import Counter, defaultdict
import hashlib
import json

from ai_cycle import BASE, plan, score
from build_ai_diagnostics import permitted_view
from build_ai_mission_cases import public_analysis
from feldmarschall import Position, GLYPHS, battle, square_name
from tournament_store import Tournament


def review():
    config = plan(); identity = config['baseline']
    buckets = defaultdict(list)
    for path in sorted((BASE/'tournaments/baseline').glob('*.fmtour')):
        with Tournament(path) as tournament:
            if tournament.metadata()['status'] != 'complete':
                raise ValueError(f'Baseline is still running: {path}')
            for row in tournament.games():
                if identity not in (row['red'], row['blue']) or score(row, identity) == 1:
                    continue
                game = tournament.game(row['id'])
                key = (row['family'], 'stall' if row['result'] == 'draw' else 'loss')
                stable = hashlib.sha256((path.name + str(row['id'])).encode()).hexdigest()
                buckets[key].append((stable, path, game))
    selected = [entry for key in sorted(buckets) for entry in sorted(buckets[key])[:2]]
    records, summaries = [], []
    for _, path, game in selected:
        army = int(game['blue'] == identity)
        position = Position()
        for side in range(2): position.place(side, game['red_setup' if side == 0 else 'blue_setup'])
        lost, history = [[0]*12, [0]*12], []
        candidates, last_battle = [], 0
        known_losses = []
        for ply, (src, dst) in enumerate(game['moves']):
            mover, target = position.cells[src], position.cells[dst]
            if ply % 2 == army:
                legal = position.moves(army)
                assert (src, dst) in legal
                known_loss = target is not None and target[3] and battle(mover[1], target[1]) == 'defender'
                if known_loss: known_losses.append(dict(ply=ply, rank=GLYPHS[mover[1]], target=GLYPHS[target[1]]))
                repeat = (src, dst) in [tuple(map(parse, event.split()[1:3])) for event in history[army::2][-40:]]
                if known_loss or repeat and ply > 100 or ply >= len(game['moves']) - 2:
                    info = permitted_view(position, army, lost)
                    candidates.append(dict(input=info, public_history=list(history), chosen_move=[src,dst],
                        legal_moves=[list(m) for m in legal], source=dict(archive=str(path.relative_to(BASE)),
                        game_index=game['id'], seed=game['seed'], group=game['family'], ply=ply),
                        own_initial_setup=game['blue_setup' if army else 'red_setup'],
                        category='known_losing_capture' if known_loss else 'repetition' if repeat else 'late_position',
                        difficulty='normal'))
            squares = square_name(src) + ' ' + square_name(dst)
            if target is None:
                history.append('moved ' + squares); position.move(src,dst)
            else:
                history.append(f'battle {squares} {GLYPHS[mover[1]]} {GLYPHS[target[1]]}')
                _, fallen = position.fight(src,dst,mover[1],target[1]); last_battle=ply+1
                for side, rank, _, _ in fallen: lost[side][rank] += 1
        # One root per game: prioritize a visible specialist sacrifice, then a
        # repeated quiet action, then the last permitted decision.
        if not candidates: continue
        chosen = min(candidates, key=lambda r: (r['category'] != 'known_losing_capture',
                        (bytes.fromhex(r['input']['board_hex'])[r['chosen_move'][0]] & 15) not in (7,8,9),
                        r['category'] != 'repetition', -r['source']['ply']))
        chosen['id'] = hashlib.sha256((path.name + ':' + str(game['id'])).encode()).hexdigest()[:20]
        chosen['analysis'] = public_analysis(chosen['input'], chosen['public_history'], chosen['chosen_move'], chosen['legal_moves'])
        records.append(chosen)
        summaries.append(dict(id=chosen['id'], tournament=str(path.relative_to(BASE)), match=game['id'],
            family=game['family'], result=game['result'], army=army, plies=game['plies'],
            quiet_tail=game['plies']-last_battle, known_losing_captures=known_losses,
            selected_ply=chosen['source']['ply'], symptom=chosen['category'],
            permanent_flag_route_blockage=chosen['analysis']['permanent_flag_route_blockage']))
    (BASE/'public-cases.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in records))
    report=dict(scope='Public failure review; outcomes select games, never AI features. Symptoms and alternatives do not prove a better continuation.',
                identity=identity, games=len(summaries), symptoms=dict(Counter(r['symptom'] for r in summaries)),
                cases=summaries)
    (BASE/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def parse(name):
    from feldmarschall import parse_square
    return parse_square(name)


if __name__ == '__main__':
    print(json.dumps(review(),indent=2))
