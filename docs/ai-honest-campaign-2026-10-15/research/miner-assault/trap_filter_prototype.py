"""Public-only bounded last-Miner filter. Research prototype, no engine driver.

The native selected move is the default. Overrides require a known adversarial
trap witness and a separate sufficient two-turn resource-survival certificate.
Unknown hypothetical fights invalidate a trap witness rather than sampling truth.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
from feldmarschall import Position, COUNTS, LAKES, battle
from gate_incidence import gate


def clone(p):
    q = Position()
    q.cells = [None if c is None else c[:] for c in p.cells]
    q.shuttle = dict(p.shuttle)
    return q


def public_copy(p, army):
    q = clone(p)
    for c in q.cells:
        if c and c[0] != army and not c[3]:
            c[1] = 12
    return q


def distance(a, b):
    return abs(a // 10 - b // 10) + abs(a % 10 - b % 10)


def neighbors(sq):
    return [n for n in range(100) if n not in LAKES and distance(sq, n) == 1]


def play(p, move):
    src, dst = move
    a, d = p.cells[src], p.cells[dst]
    if d:
        if a[1] >= 12 or d[1] >= 12:
            return False
        p.fight(src, dst, a[1], d[1])
    else:
        p.move(src, dst)
    return True


def possible_ranks(p, army, lost):
    remaining = [n - dead for n, dead in zip(COUNTS, lost)]
    for c in p.cells:
        if c and c[0] != army and c[3]:
            remaining[c[1]] -= 1
    if min(remaining) < 0:
        return None
    return {sq: [c[1]] if c[3] else [r for r, n in enumerate(remaining)
            if n > 0 and (not c[2] or r < 10)]
            for sq, c in enumerate(p.cells) if c and c[0] != army}


def flag_screen_safe(p, army, possible):
    """Sufficient own-Flag survival for two enemy turns; no general safety claim."""
    flags = [sq for sq, c in enumerate(p.cells) if c and c[:2] == [army, 11]]
    if len(flags) != 1:
        return False
    flag = flags[0]
    if any(p.cells[n] is None or p.cells[n][:2] != [army, 10]
           for n in neighbors(flag)):
        return False
    return all(7 not in ranks or distance(sq, flag) > 2
               for sq, ranks in possible.items())


def preserving_retreats(p, army, miner, possible):
    """Return legal quiet first steps with an advance-fixed safe second step.

    Every enemy rank capable of killing/exchanging the Miner is a one-step
    mover. Manhattan lower bounds therefore remain sound despite blockers,
    lakes, adversarial captures elsewhere, or enemy shuttle restrictions.
    The second square starts empty (or is the vacated first-step source), and
    any enemy able to reach it early is a Miner-losing Scout/Spy. No permanent
    mobility, Flag-capture route, or favorable material trade is established.
    """
    lethal = [sq for sq, ranks in possible.items()
              if any(r < 10 and battle(r, 7) != 'defender' for r in ranks)]
    found = []
    for first in p.moves(army):
        if first[0] != miner or p.cells[first[1]] is not None:
            continue
        if any(distance(sq, first[1]) <= 1 for sq in lethal):
            continue
        q = clone(p)
        play(q, first)
        for second in q.moves(army):
            if second[0] != first[1] or second[1] == miner or q.cells[second[1]]:
                continue
            if any(distance(sq, second[1]) <= 2 for sq in lethal):
                continue
            found.append(dict(first=list(first), second=list(second),
                              horizon='Miner survives first two enemy turns'))
            break
    return found


def trap_witness(p, army, move, flag, max_nodes=20000):
    """Exists disclosed quiet enemy reply; all friendly replies lose Miner.

    Includes ally rescue captures and shuttle-legal replies. A possible own
    terminal Flag capture or any unresolved combat aborts this witness. The
    witness enemy captures themselves establish enemy mobility after each
    friendly reply, excluding an enemy-no-moves terminal at that point.
    """
    q = clone(p)
    play(q, move)
    nodes = 0
    for enemy_step in q.moves(1 - army):
        src, dst = enemy_step
        if not q.cells[src][3] or q.cells[src][1] >= 10 or q.cells[dst]:
            continue
        r = clone(q)
        play(r, enemy_step)
        replies = r.moves(army)
        if not replies:
            continue
        certificates = []
        for reply in replies:
            nodes += 1
            if nodes > max_nodes:
                return None, nodes, True
            # Capturing the sole deduced Flag wins even if its nibble is hidden.
            if reply[1] == flag:
                break
            s = clone(r)
            if not play(s, reply):
                break
            miners = [sq for sq, c in enumerate(s.cells)
                      if c and c[:2] == [army, 7]]
            if not miners:
                certificates.append(dict(reply=list(reply), result='Miner died in known combat'))
                continue
            target = miners[0]
            killer = next((capture for capture in s.moves(1 - army)
                if capture[1] == target and s.cells[capture[0]][3]
                and s.cells[capture[0]][1] < 10
                and battle(s.cells[capture[0]][1], 7) != 'defender'), None)
            if killer is None:
                break
            certificates.append(dict(reply=list(reply), enemy_capture=list(killer)))
        else:
            return dict(enemy_quiet_reply=list(enemy_step),
                        friendly_reply_certificates=certificates), nodes, False
    return None, nodes, False


def filter_move(position, army, lost, selected, max_nodes=20000):
    """Pure public function. Original move on every unsupported/capped case."""
    selected = tuple(selected)
    report = dict(selected=list(selected), move=list(selected), changed=False, nodes=0)
    p = public_copy(position, army)
    g = gate(p, army)
    if not g or selected[0] != g['miner'] or p.cells[selected[1]]:
        return report
    if selected not in p.moves(army):
        return report
    possible = possible_ranks(p, army, lost)
    if possible is None or not flag_screen_safe(p, army, possible):
        report['bailout'] = 'own Flag two-turn screen not certified'
        return report
    retreats = preserving_retreats(p, army, g['miner'], possible)
    if not retreats or any(tuple(r['first']) == selected for r in retreats):
        return report
    witness, nodes, capped = trap_witness(p, army, selected, g['flag'], max_nodes)
    report.update(nodes=nodes, capped=capped)
    if witness:
        # Stable legal-move order is the only tie break; no added score weights.
        report.update(changed=True, move=retreats[0]['first'], retreat=retreats[0],
                      trap=witness, resource_gate=g)
    return report


def from_row(row):
    p = Position()
    for sq, value in enumerate(bytes.fromhex(row['public_board_hex'])):
        if value < 254:
            p.cells[sq] = [(value >> 4) & 1, value & 15, bool(value & 64), bool(value & 32)]
    shuttle = bytes.fromhex(row['shuttle'])
    p.shuttle = {a: tuple(None if shuttle[2*i+a] == 255 else shuttle[2*i+a]
                         for i in range(3)) for a in (0, 1)}
    return p


def audit():
    path = Path(__file__).with_name('gate-incidence.json')
    data = json.loads(path.read_text())
    rows = []
    timings = []
    counters = Counter()
    for row in data['rows']:
        p = from_row(row)
        start = time.perf_counter_ns()
        result = filter_move(p, row['army'], row['lost'], row['actual_move'])
        timings.append((time.perf_counter_ns() - start) / 1e6)
        counters['gated_roots'] += 1
        if row['actual_mover_is_miner']:
            counters['actual_miner_moves'] += 1
            if p.cells[row['actual_move'][1]] is None:
                counters['actual_quiet_miner_moves'] += 1
        counters['changed'] += result['changed']
        counters['proof_nodes'] += result['nodes']
        if result.get('bailout'):
            counters['own_flag_bailouts'] += 1
        if result.get('capped'):
            counters['cap_bailouts'] += 1
        if result['changed'] or row['actual_mover_is_miner']:
            rows.append(dict(source=row['source'], game=row['game'], ply=row['ply'], **result))
    return dict(kind='old-public-last-miner-trap-filter-prototype', strength_evidence=False,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        gate_input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sources=data['sources'],
        corpus=data['counters'], counters=dict(counters), rows=rows,
        timing_ms=dict(mean=sum(timings)/len(timings), maximum=max(timings),
                       total=sum(timings), sample='87 already gated roots; wall time on this host only'),
        scope='Counterfactual public certificate audit only; no tournament or claim of strength.')


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
