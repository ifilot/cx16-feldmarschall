"""Fit and assess one joint setup-style model on historical development only."""
import sys
import math, json
from pathlib import Path
from collections import defaultdict
from feldmarschall import ROOT
from tournament_store import Tournament, replay
from belief_experiment import rows
from information_strategy_cycle import bootstrap, digest
from campaign_joint_beliefs import SCHEMA
from calibrated_beliefs import BeliefModel

def nb(f):
    r, c = divmod(f, 10)
    return {rr * 10 + cc for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)) if 0 <= rr < 4 and 0 <= cc < 10}

def zsum(a, n, k, t):
    return sum((math.comb(a, j) * math.comb(n - a, k - j) * math.exp(t * j) for j in range(max(0, k - (n - a)), min(a, k) + 1))) if 0 <= k <= n else 0

def local(sq, army):
    return (3 - sq // 10 if army else sq // 10 - 6) * 10 + sq % 10

def fit(data):
    weights = [0.5, 0.5]
    phi = [[0.25] * 4 for _ in range(2)]
    theta = [-1.0, 2.0]
    for step in range(40):
        responsibilities = []
        for s in data:
            f = s.index('F')
            k = sum((s[n] == 'B' for n in nb(f)))
            d = len(nb(f))
            vals = [weights[z] * phi[z][f // 10] / 10 * math.exp(theta[z] * k) / zsum(d, 39, 6, theta[z]) for z in range(2)]
            responsibilities.append([v / sum(vals) for v in vals])
        weights = [(1 + sum((r[z] for r in responsibilities))) / (len(data) + 2) for z in range(2)]
        for z in range(2):
            counts = [1.0] * 4
            for s, r in zip(data, responsibilities):
                counts[s.index('F') // 10] += r[z]
            phi[z] = [v / sum(counts) for v in counts]
            grid = [-4 + i * 0.25 if z == 0 else i * 0.25 for i in range(17)]

            def objective(t):
                return sum((r[z] * (t * sum((s[n] == 'B' for n in nb(s.index('F')))) - math.log(zsum(len(nb(s.index('F'))), 39, 6, t))) for s, r in zip(data, responsibilities))) - 0.5 * t * t
            theta[z] = max(grid, key=objective)
    return dict(weights=weights, phi=phi, theta=theta)

def bomb_reveals(g):
    states, _ = replay(g)
    ids = {sq: (c[0], sq) for sq, c in enumerate(states[0]) if c}
    out = []
    for ply, (src, dst) in enumerate(g['moves']):
        a, d = (ids[src], ids.get(dst))
        if d:
            for sq, key in [(src, a), (dst, d)]:
                if states[ply][sq][1] == 10:
                    out.append((ply + 1, key))
        ids.pop(src)
        if states[ply + 1][dst] is None:
            ids.pop(dst, None)
        elif states[ply + 1][dst][0] == a[0]:
            ids[dst] = a
    return out

def predict(row, model, reveals, independent):
    enemy = 1 - row['army']
    u = {local(h[2], enemy) for h in row['histories'].values() if h[-1] & 1 << 10}
    fset = {local(h[2], enemy) for h in row['histories'].values() if h[-1] & 1 << 11}
    fixed = {local(origin, enemy) for ply, (owner, origin) in reveals if owner == enemy and ply <= row['ply']}
    k = 6 - len(fixed)
    probs = {}
    for f in fset:
        probs[f] = 0
        available = u - {f}
        neighbors = nb(f)
        for z in range(2):
            t = model['theta'][z]
            probs[f] += model['weights'][z] * model['phi'][z][f // 10] / 10 * math.exp(t * len(fixed & neighbors)) * zsum(len(available & neighbors), len(available), k, t) / zsum(len(neighbors), 39, 6, t)
    norm = sum(probs.values())
    return {f: p / norm for f, p in probs.items()}

def main():
    p = ROOT / 'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    views = list(rows(p))
    parts = {r['pair']: r['partition'] for r in views}
    train = []
    cal = []
    setups = defaultdict(list)
    revealed = {}
    with Tournament(p.with_name('development.fmtour')) as t:
        seen = set()
        for row in t.games():
            g = t.game(row['id'])
            revealed[g['id']] = bomb_reveals(g)
            for side in ('red', 'blue'):
                if (g['pair_id'], side) in seen:
                    continue
                seen.add((g['pair_id'], side))
                s = g[side + '_setup']
                (train if parts[g['pair_id']] == 'train' else cal).append(s)
                setups[parts[g['pair_id']], g['family']].append(s)
    model = fit(train)
    counts = [1.0] * 4
    for s in train:
        counts[s.index('F') // 10] += 1
    simple = dict(weights=[1.0, 0.0], phi=[[n / sum(counts) for n in counts]] * 2, theta=[0.0, 0.0])
    selected = []
    grouped = defaultdict(list)
    for row in views:
        if row['partition'] == 'calibration':
            grouped[row['game'], row['army']].append(row)
    for vs in grouped.values():
        vs.sort(key=lambda r: r['ply'])
        selected.extend((vs[i] for i in sorted({len(vs) // 3, 2 * len(vs) // 3})))
    bygame = defaultdict(list)
    earlylate = defaultdict(list)
    metadata = {}
    learned_model = BeliefModel.load(ROOT / 'ai/models/public-history-beliefs-v1.json')
    learned_games = defaultdict(list)
    for r in selected:
        flags = [sq for sq, rank in r['labels'].items() if rank == 11]
        if not flags:
            continue
        f = local(r['histories'][flags[0]][2], 1 - r['army'])
        a = predict(r, simple, revealed[r['game']], False)
        b = predict(r, model, revealed[r['game']], False)
        vals = (-math.log(a[f]), -math.log(b[f]), max(a, key=a.get) == f, max(b, key=b.get) == f)
        bygame[r['game']].append(vals)
        metadata[r['game']] = (r['pair'], r['family'])
        fractional = learned_model.marginals(list(bytes.fromhex(r['board'])), list(bytes.fromhex(r['lost'])), r['histories'], r['army'])
        mass = sum((v[11] for v in fractional.values()))
        old = fractional[flags[0]][11] / mass
        learned_games[r['game']].append((-math.log(old), -math.log(b[f]), max(fractional, key=lambda sq: fractional[sq][11]) == flags[0], max(b, key=b.get) == f))
        earlylate['has_public_bomb' if any((ply <= r['ply'] and owner == 1 - r['army'] for ply, (owner, origin) in revealed[r['game']])) else 'no_public_bomb'].append(vals)
    pairs = defaultdict(list)
    for game, vs in bygame.items():
        pair, family = metadata[game]
        pairs[pair, family].append([sum((v[i] for v in vs)) / len(vs) for i in range(4)])
    blocks = [(family, dict(logloss_delta=sum((v[1] - v[0] for v in vs)) / len(vs), accuracy_delta=sum((v[3] - v[2] for v in vs)) / len(vs))) for (pair, family), vs in pairs.items()]
    report = dict(model=model, simple=simple, train_armies=len(train), calibration_armies=len(cal), snapshots=len(selected), games=len(bygame), paired=bootstrap(blocks), by_bomb_evidence={k: dict(n=len(vs), independent_logloss=sum((v[0] for v in vs)) / len(vs), joint_logloss=sum((v[1] for v in vs)) / len(vs), independent_accuracy=sum((v[2] for v in vs)) / len(vs), joint_accuracy=sum((v[3] for v in vs)) / len(vs)) for k, vs in earlylate.items()})
    learned_pairs = defaultdict(list)
    for game, vs in learned_games.items():
        learned_pairs[metadata[game]].append([sum((v[i] for v in vs)) / len(vs) for i in range(4)])
    learned_blocks = [(family, dict(logloss_delta=sum((v[1] - v[0] for v in vs)) / len(vs), accuracy_delta=sum((v[3] - v[2] for v in vs)) / len(vs))) for (pair, family), vs in learned_pairs.items()]
    report['versus_frozen_independent_learned_model'] = dict(paired=bootstrap(learned_blocks), model_sha256=digest(ROOT / 'ai/models/public-history-beliefs-v1.json'), limitation='Existing learned probabilities are deterministic count-balanced fractional approximations, not its actual eight-world runtime estimates. New joint Flag probabilities are exact for its simplified model.')
    report['setup_correlations'] = {partition: {family: dict(armies=len(vs), mean_flag_neighbor_bombs=sum((sum((s[n] == 'B' for n in nb(s.index('F')))) for s in vs)) / len(vs), bomb_fraction_at_flag_neighbors=sum((sum((s[n] == 'B' for n in nb(s.index('F')))) for s in vs)) / sum((len(nb(s.index('F'))) for s in vs))) for (part, family), vs in setups.items() if part == partition} for partition in ('train', 'calibration')}
    model_document = dict(model, schema=SCHEMA, training=dict(corpus_sha256=digest(p), tournament_sha256=digest(p.with_name('development.fmtour')), recipe_sha256=digest(Path(__file__)), training_armies=len(train), calibration_armies=len(cal), split='First14 complete pairs per family train, last6 calibrate, matching frozen prior study.', deduplication='One initial army per pair and color; swapped games never duplicate setup training.', recipe='40 fixed EM iterations; initial weights0.5, row priors0.25, theta[-1,2]. Add-one style and Flag-row counts. Theta grids[-4,0] and[0,4] step0.25; quadratic log penalty0.5*theta^2. No calibration fitting.', feature='Initial Flag row and orthogonal Flag-Bomb adjacency only; no family labels, outcomes or move labels used.', limitations='Mixture is a simplified setup distribution, not an opponent action model. Mobile ranks exchangeable except original public behavior factors.'), research=dict(primary_source='https://project.dke.maastrichtuniversity.nl/games/files/bsc/OMStratego.pdf', connection='Section2.2 motivates protected Flags, decoys and exposed Flags; this exact mixture/subset model is our hypothesis, not the paper algorithm.'))
    model_path = ROOT / 'ai/models/joint-flag-bomb-beliefs-v1.json'
    model_path.write_text(json.dumps(model_document, indent=2) + '\n')
    report.update(scope='Historical development only; calibration evaluates one fixed fit without tuning. Never reads campaign or fresh validation cohorts.', model_sha256=digest(model_path), analysis_sha256=digest(Path(__file__)), corpus_sha256=digest(p), tournament_sha256=digest(p.with_name('development.fmtour')))
    out = ROOT / 'docs/ai-honest-campaign-2026-10-15/research/joint-setup-development.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
if __name__ == '__main__':
    main()
