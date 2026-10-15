"""Evaluate policies on public forced histories, without importing oracle fields."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shlex
import shutil

from build_ai_mission_cases import public_analysis
from feldmarschall import ROOT, Engine, parse_square
from train_teacher_student import canonical_shuttle


def decide(case, executable):
    army = case['input']['army']
    engine = Engine(shlex.join([str(executable), '--difficulty', case['difficulty']]))
    try:
        engine.send(f"seed {case['source']['seed'] * 2 + army + 1}")
        engine.send('new ' + ('red', 'blue')[army])
        engine.send('setup ' + case['own_initial_setup'])
        for ply, event in enumerate(case['public_history']):
            if ply % 2 == army:
                # Consume policy decisions/state, then force the recorded public
                # action. This evaluates conditioning on the same history;
                # it is not an engine replay or an outcome counterfactual.
                engine.ask('go', 'move')
                engine.ask('played ' + ' '.join(event.split()[1:3]), 'playedok')
            engine.send(event)
        board_hex, lost_hex, state_hex = engine.ask('public', 'public').split()[1:]
        assert board_hex == case['input']['board_hex']
        assert lost_hex == case['input']['enemy_lost_hex']
        shuttle = case['input']['shuttle']
        expected = bytes(shuttle[str(a)][i] if shuttle[str(a)][i] is not None else 255
                         for i in range(3) for a in (0, 1)).hex()
        # Before an army's first move, its unused coordinates can be zero or
        # NOWHERE. Active two-square histories must still match exactly.
        assert canonical_shuttle(state_hex) == canonical_shuttle(expected)
        move = list(map(parse_square, engine.ask('go', 'move').split()))
        assert move in case['legal_moves']
        analysis = public_analysis(case['input'], case['public_history'], move, case['legal_moves'])
        return {'move': move, 'recent_move': analysis['chosen_move_recent'],
                'known_losing_capture': analysis['chosen_known_losing_capture'],
                'curated_alternative': any(move == a['move'] for a in case['analysis']['alternatives'])}
    finally:
        engine.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases', type=Path)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'build/feldmarschall-engine-mission-diagnostics')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    engines = {}
    for name, path in [('candidate', args.candidate), ('baseline', args.baseline)]:
        engines[name] = (args.out / name).resolve()
        shutil.copyfile(path, engines[name]); engines[name].chmod(0o755)
    cases = [json.loads(line) for line in args.cases.read_text().splitlines()]
    rows = [{'id': case['id'], 'category': case['category'], 'structural_status': case['analysis']['structural_status'],
             **{name: decide(case, executable) for name, executable in engines.items()}} for case in cases]
    result = {'scope': 'Public forced-history diagnostics; executed-move goal transfers and backtracking caches follow recorded actions. Decisions are legal and views/inventories/repetition match. No strength or exact historical replay claim.',
              'cases_sha256': hashlib.sha256(args.cases.read_bytes()).hexdigest(),
              'engine_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in engines.items()},
              'changed_cases': sum(row['candidate']['move'] != row['baseline']['move'] for row in rows),
              'categories': dict(Counter(row['category'] for row in rows)), 'positions': rows}
    (args.out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'positions'}, indent=2))


if __name__ == '__main__':
    main()
