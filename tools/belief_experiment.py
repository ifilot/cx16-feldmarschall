"""Reproducible public-input corpus, belief fitting and frozen Classic evaluation."""
import argparse
from collections import defaultdict
import contextlib
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import shlex
import subprocess
import tempfile

from ai_registry import ROOT, build_policy, catalog, get_policy, register
from calibrated_beliefs import BeliefModel, FEATURE_SIZES, SCHEMA, features
from feldmarschall import Engine, GLYPHS, square_name, battle
from information_strategy_cycle import analyze_match, bootstrap, digest, score
from tournament import run
from tournament_store import Tournament, replay, verify
from train_ai_student import sample_world

OUT = ROOT/'docs/ai-calibrated-beliefs-2026-10-15'


def write(path, document):
    path.write_text(json.dumps(document, indent=2)+'\n')


def rows(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            row['histories'] = {int(sq): h for sq, h in row['histories'].items()}
            row['labels'] = {int(sq): rank for sq, rank in row['labels'].items()}
            yield row


def public_corpus(tournament_path, path, baseline, split_rounds=None):
    """Labels live outside the observer; only own setup/public events sent in."""
    program, receipt = build_policy(baseline)
    with Tournament(tournament_path) as tournament:
        metadata = tournament.metadata()
        assert metadata['status'] == 'complete'
        games = [tournament.game(g['id']) for g in tournament.games() if g['result'] != 'error']
    family_pairs = defaultdict(list)
    for game in games:
        if game['pair_id'] not in family_pairs[game['family']]:
            family_pairs[game['family']].append(game['pair_id'])
    # Use metadata schedule, including errors, so a failed game never shifts
    # the split or moves its paired game to a different cohort.
    with Tournament(tournament_path) as tournament:
        all_pairs = defaultdict(set)
        for game in tournament.games(): all_pairs[game['family']].add(game['pair_id'])
    training = {p for values in all_pairs.values() for p in sorted(values)[:split_rounds]} if split_rounds else set()
    counts = defaultdict(int)
    engines = [Engine(shlex.quote(str(program.parent/'observer'))) for _ in range(2)]
    try:
        with gzip.open(path, 'xt') as stream:
            for game in games:
                states, _ = replay(game)
                for side, engine in enumerate(engines):
                    engine.send('new '+('red', 'blue')[side])
                    engine.send('rules 0')
                    engine.send('setup '+game[('red_setup', 'blue_setup')[side]])
                for ply, state in enumerate(states):
                    if ply <= 400 and ply % 20 == 0 and ply < len(game['moves']):
                        for side, engine in enumerate(engines):
                            army, board, lost, _ = engine.ask('public', 'public').split()
                            assert int(army) == side
                            cells = list(bytes.fromhex(board))
                            histories = {sq: list(map(int, engine.ask('memory '+square_name(sq), 'history').split()))
                                         for sq, cell in enumerate(cells)
                                         if cell < 254 and bool(cell & 16) != bool(side) and not cell & 32}
                            labels = {sq: state[sq][1] for sq in histories}
                            for sq, rank in labels.items():
                                assert state[sq][0] == 1-side and histories[sq][-1] & (1 << rank)
                                assert cells[sq] & 15 == 12, 'concealed truth leaked into public board'
                            partition = ('train' if game['pair_id'] in training else 'calibration') if split_rounds else 'validation'
                            row = dict(game=game['id'], pair=game['pair_id'], family=game['family'],
                                       partition=partition, ply=ply, army=side, board=board, lost=lost,
                                       histories=histories, labels=labels)
                            stream.write(json.dumps(row, separators=(',', ':'))+'\n')
                            counts[partition] += 1
                    if ply == len(game['moves']) or ply >= 400:
                        break
                    src, dst = game['moves'][ply]
                    squares = square_name(src)+' '+square_name(dst)
                    event = ('moved '+squares if state[dst] is None else
                             'battle '+squares+' '+GLYPHS[state[src][1]]+' '+GLYPHS[state[dst][1]])
                    for engine in engines: engine.send(event)
                print('Corpus game', game['id'], flush=True)
    finally:
        for engine in engines: engine.close()
    audit = dict(tournament=str(tournament_path.relative_to(ROOT)), tournament_sha256=digest(tournament_path),
                 corpus_sha256=digest(path), snapshots=dict(counts), games=len(games),
                 observer_source_sha256=receipt['policy']['source_sha256'],
                 permitted_input='Own setup and public moves/battles only. Referee labels stored separately for offline fitting/scoring.',
                 pair_partitions={family: {'train': sorted(p for p in ps if p in training),
                                          'other': sorted(p for p in ps if p not in training)}
                                  for family, ps in all_pairs.items()})
    write(path.with_suffix('.audit.json'), audit)
    return audit


def metric_summary(records):
    """Each game contributes equal weight; report piece-level metrics too."""
    grouped = defaultdict(lambda: defaultdict(list))
    locations = defaultdict(lambda: defaultdict(list))
    for row, probabilities in records:
        for sq, label in row['labels'].items():
            p = probabilities[sq]
            loss = -math.log(max(1e-12, p[label]))
            brier = sum((v-int(rank == label))**2 for rank, v in enumerate(p))
            correct = float(max(range(12), key=lambda r: p[r]) == label)
            groups = ['all', 'moved' if row['histories'][sq][5] else 'unmoved']
            if label == 11: groups.append('flag')
            if label == 9: groups.append('spy')
            for group in groups:
                grouped[group][row['game']].append((loss, brier, correct))
        # Identifying the square containing a rare unique rank is different
        # from predicting the most likely rank on that square. Average ties
        # rather than reward a board-orientation-dependent square ordering.
        for rank, group in ((11,'flag'), (9,'spy')):
            targets = [sq for sq, label in row['labels'].items() if label == rank]
            if not targets:
                continue
            assert len(targets) == 1
            target = targets[0]
            mass = {sq:p[rank] for sq,p in probabilities.items()}
            total = sum(mass.values())
            value = mass[target]
            higher = sum(v > value for v in mass.values())
            ties = sum(v == value for v in mass.values())
            top = 1/ties if higher == 0 else 0.0
            reciprocal = sum(1/i for i in range(higher+1,higher+ties+1))/ties
            locations[group][row['game']].append((top,reciprocal,-math.log(max(1e-12,value/total))))
    result = {}
    for group, games in grouped.items():
        means = [tuple(sum(x[i] for x in values)/len(values) for i in range(3)) for values in games.values()]
        result[group] = dict(games=len(games), pieces=sum(map(len, games.values())),
                             log_loss=sum(x[0] for x in means)/len(means),
                             brier=sum(x[1] for x in means)/len(means),
                             accuracy=sum(x[2] for x in means)/len(means))
        if group in locations:
            values=[tuple(sum(x[i] for x in xs)/len(xs) for i in range(3)) for xs in locations[group].values()]
            result[group]['location']=dict(top_accuracy=sum(x[0] for x in values)/len(values),
                                           mean_reciprocal_rank=sum(x[1] for x in values)/len(values),
                                           log_loss=sum(x[2] for x in values)/len(values))
    return result


def coarse_model():
    """Likelihood product represented by old approach/retreat importance weights.

    Coarse weights are not feature-separable, so override likelihoods directly.
    """
    model = BeliefModel(dict(schema=SCHEMA, feature_sizes=list(FEATURE_SIZES), temperature=0,
                       log_likelihood_ratios=[[[[0.0]*size for size in FEATURE_SIZES] for _ in range(12)] for _ in range(2)]))
    def likelihood(cells, army, sq, h):
        return [1+int(h[8] < 12 and battle(rank, h[8]) == 'attacker')+
                int(h[9] < 12 and battle(h[9], rank) == 'attacker') for rank in range(12)]
    model.likelihoods = likelihood
    return model


def fit(corpus, destination, report_path):
    data = list(rows(corpus))
    training = [row for row in data if row['partition'] == 'train']
    calibration = [row for row in data if row['partition'] == 'calibration']
    assert {r['pair'] for r in training}.isdisjoint(r['pair'] for r in calibration)
    game_views = defaultdict(int)
    for row in training: game_views[row['game']] += 1
    totals = [[0.0]*12 for _ in range(2)]
    counts = [[[[0.0]*size for size in FEATURE_SIZES] for _ in range(12)] for _ in range(2)]
    for row in training:
        cells = list(bytes.fromhex(row['board']))
        for sq, rank in row['labels'].items():
            h = row['histories'][sq]
            group, weight = int(h[5] > 0), 1/game_views[row['game']]
            totals[group][rank] += weight
            for f, v in enumerate(features(cells, row['army'], sq, h)):
                counts[group][rank][f][v] += weight
    tables = copy.deepcopy(counts)
    alpha = 10.0
    for g in range(2):
        for f, size in enumerate(FEATURE_SIZES):
            pooled = [sum(counts[g][r][f][v] for r in range(12)) for v in range(size)]
            frequencies = [(v+1)/(sum(pooled)+size) for v in pooled]
            for r in range(12):
                tables[g][r][f] = [math.log((counts[g][r][f][v]+alpha*frequencies[v])/
                                                   (totals[g][r]+alpha)/frequencies[v]) for v in range(size)]
    document = dict(schema=SCHEMA, feature_sizes=list(FEATURE_SIZES), temperature=0,
                    log_likelihood_ratios=tables, smoothing_pseudocount=alpha,
                    soft_log_likelihood_bound=2.0, training_corpus_sha256=digest(corpus),
                    training_games=sorted(game_views), calibration_games=sorted({r['game'] for r in calibration}),
                    input='Masked board and public origin/move/approach/retreat history only.',
                    prediction='Conditional feature likelihood product; no online access to labels. Rank prior supplied by exact remaining inventory.')
    evaluated = {}
    for temperature in (0.0, .125, .25, .5, .75, 1.0):
        document['temperature'] = temperature
        model = BeliefModel(document)
        records = ((row, model.marginals(list(bytes.fromhex(row['board'])), list(bytes.fromhex(row['lost'])),
                                         row['histories'], row['army'])) for row in calibration)
        evaluated[str(temperature)] = metric_summary(records)
        print('Calibration temperature', temperature, evaluated[str(temperature)]['all'], flush=True)
    best = min(evaluated, key=lambda key: (evaluated[key]['all']['log_loss'], float(key)))
    document['temperature'] = float(best)
    write(destination, document)
    coarse = coarse_model()
    baseline = metric_summary((row, coarse.marginals(list(bytes.fromhex(row['board'])), list(bytes.fromhex(row['lost'])),
                                                    row['histories'], row['army'])) for row in calibration)
    report = dict(training_games=len(game_views), calibration_games=len(document['calibration_games']),
                  train_snapshots=len(training), calibration_snapshots=len(calibration),
                  calibration=evaluated, baseline_approximate_marginals=baseline,
                  selected_temperature=float(best), model_sha256=digest(destination),
                  selection='Minimum game-weighted log loss on count-balanced fractional marginals; not exact joint assignment marginals. No strength results used.',
                  limitations='Naive conditional independence; snapshot behavior likelihoods rather than a full opponent action policy. Final sampler is self-normalized importance sampling with eight worlds.')
    write(report_path, report)
    return report


def predict(corpus, model_path, report_path, partition, seed):
    """Score actual 8-world beliefs; many-world diagnostic distinguishes sampling.

    Select two public snapshots per game, before inspecting labels. Sparse
    eight-world predictions get a 5% inventory-only mixture for finite log loss;
    this is an offline scoring convention, not a runtime rank disclosure.
    """
    model = BeliefModel.load(model_path)
    grouped = defaultdict(list)
    for row in rows(corpus):
        if row['partition'] == partition: grouped[row['game']].append(row)
    selected = []
    for views in grouped.values():
        for side in (0, 1):
            own = sorted((r for r in views if r['army'] == side), key=lambda r: r['ply'])
            if own:
                selected.extend(own[i] for i in sorted({len(own)//3, 2*len(own)//3}))
    reports = {}
    predictions = {}
    for label, samples, fitted in (('baseline_8',8,False),('learned_8',8,True),
                                    ('baseline_256',256,False),('learned_256',256,True)):
        records, effective, per_game = [], [], defaultdict(list)
        for row in selected:
            cells, lost = list(bytes.fromhex(row['board'])), list(bytes.fromhex(row['lost']))
            rng = random.Random(seed+row['game']*1009+row['ply']*2+row['army'])
            draws = (model.sample_worlds(cells,lost,row['histories'],rng,row['army'],samples) if fitted else
                     [sample_world(cells,lost,row['histories'],rng,row['army']) for _ in range(samples)])
            total = sum(w for _, w in draws)
            ess = total*total/sum(w*w for _, w in draws)
            effective.append(ess)
            per_game[row['game']].append(ess)
            slots, remaining, _ = model.prepare(cells,lost,row['histories'],row['army'])
            probs = {}
            for sq in slots:
                prior = [n if row['histories'][sq][-1] & (1 << r) else 0 for r,n in enumerate(remaining)]
                denom = sum(prior)
                probs[sq] = [.95*sum(w for world,w in draws if world[sq]&15 == rank)/total+
                             .05*prior[rank]/denom for rank in range(12)]
            records.append((row,probs))
        reports[label] = dict(metrics=metric_summary(records), mean_effective_samples=sum(effective)/len(effective),
                              minimum_effective_samples=min(effective))
        predictions[label] = records
        print('Prediction', partition, label, reports[label], flush=True)
    # Paired game-cluster log-loss differences, preserving both orientations.
    def losses(records):
        acc=defaultdict(list)
        for row, probs in records:
            acc[row['game']].extend(-math.log(max(1e-12,probs[sq][rank])) for sq,rank in row['labels'].items())
        return {g:sum(v)/len(v) for g,v in acc.items()}
    differences={}
    for samples in (8,256):
        old,new=losses(predictions['baseline_'+str(samples)]),losses(predictions['learned_'+str(samples)])
        blocks=defaultdict(list)
        family={r['game']:r['family'] for r in selected}
        pair={r['game']:r['pair'] for r in selected}
        for game in old:blocks[pair[game]].append((family[game],new[game]-old[game]))
        differences[str(samples)]=bootstrap([(values[0][0],dict(log_loss_difference=sum(v for _,v in values)/len(values)))
                                             for values in blocks.values() if len(values)==2])
    result=dict(partition=partition, model_sha256=digest(model_path), corpus_sha256=digest(corpus),
                snapshots=len(selected), games=len(grouped), sampling=reports, paired_log_loss=differences,
                scoring='Game-weighted all-concealed-piece metrics; 5% inventory prior smoothing for sparse sampled probabilities. Negative paired log-loss difference favors learned beliefs. 256 samples are offline diagnostic only; playing uses eight.')
    write(report_path,result)
    return result


def register_candidate(out, plan):
    before = out/'registry-before.json'
    if not before.exists(): write(before, dict(policies=catalog()))
    spec = copy.deepcopy(get_policy(plan['baseline']))
    for key in ('archive','source_sha256'): spec.pop(key)
    spec.update(id=plan['candidate'], name='Calibrated Public-History Belief Teacher v1 / Normal',
                description=plan['idea'], status='experimental',
                information_model='Own army and public history only; learned hidden-rank likelihoods, exact public inventory.',
                belief_model='ai/models/public-history-beliefs-v1.json',
                model='Frozen categorical belief tables plus unchanged Context Teacher v1 guarded student.',
                belief_model_sha256=digest(ROOT/'ai/models/public-history-beliefs-v1.json'),
                asset_files=['ai/models/public-history-beliefs-v1.json'])
    spec['driver_args'] += ['--belief-model','public-history-beliefs-v1.json']
    write(out/'policy-spec.json',spec)
    result=register(spec)
    write(out/'frozen-policies.json',{p:get_policy(p) for p in (plan['baseline'],plan['candidate'],plan['opponent'])})
    return result


def strength(out, plan):
    frozen=json.loads((out/'frozen-policies.json').read_text())
    assert all(get_policy(p)==v for p,v in frozen.items())
    before=json.loads((out/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)]==before
    # Reuse the established all-state Python/native replay + Qt6 audit.
    audit_plan=dict(plan, candidates={'belief':plan['candidate']})
    config=plan['validation']
    matches=[dict(name='dos--'+p,group='dos',policy=p,opponent=plan['opponent'],seed=config['dos_seed'],rounds=config['dos_rounds'])
             for p in (plan['baseline'],plan['candidate'])]
    matches.append(dict(name='head--'+plan['candidate'],group='head',policy=plan['candidate'],
                        opponent=plan['baseline'],seed=config['head_seed'],rounds=config['head_rounds']))
    output=out/'validation';output.mkdir(exist_ok=True)
    reports,pairs,signature={}, {}, None
    for match in matches:
        path=output/(match['name']+'.fmtour')
        if not path.exists():
            print('Strength running',match['name'],flush=True)
            with path.with_suffix('.log').open('x') as log,contextlib.redirect_stdout(log):
                run(match['policy'],match['opponent'],path,rounds=match['rounds'],seed=match['seed'],
                    jobs=plan['jobs'],families=plan['families'],max_plies=plan['max_plies'],backend=plan['backend'])
        report,complete,current=analyze_match(path,match,audit_plan,frozen)
        reports[match['name']]=report
        if match['group']=='dos':
            if signature is None:signature=current
            assert signature==current
            pairs[match['policy']]=complete
        write(output/(match['name']+'.report.json'),report)
        print('Strength verified',match['name'],report['summary'],flush=True)
    old,new=pairs[plan['baseline']],pairs[plan['candidate']]
    common=sorted(old.keys() & new.keys())
    matched=bootstrap([(old[key][0],dict(score=new[key][1]['score']-old[key][1]['score'])) for key in common])
    head=reports[matches[-1]['name']]['complete_pair_statistics']['metrics']['score']
    result=dict(matches=reports,matched_dos=matched,
                supported_dos_gain=matched['metrics']['score']['interval_95'][0]>0,
                supported_head_gain=head['interval_95'][0]>.5,
                previous_policies_unchanged=len(before),
                source_and_model_frozen=frozen,
                statistics='20000 family-stratified complete side-swapped paired bootstrap replicates; one candidate, 95% intervals. Errors unscored and preserved.')
    result['promote']=result['supported_dos_gain'] and result['supported_head_gain']
    write(out/'strength-report.json',result)
    return result


def decision(out, plan):
    strength=json.loads((out/'strength-report.json').read_text())
    prediction=json.loads((out/'validation-prediction.json').read_text())
    dos={p:strength['matches']['dos--'+p]['summary']['standings'][p]
         for p in (plan['baseline'],plan['candidate'])}
    head=strength['matches']['head--'+plan['candidate']]
    effect=strength['matched_dos']['metrics']['score']
    evidence={}
    for count in (8,256):
        evidence[str(count)]={name:prediction['sampling'][name+'_'+str(count)]['metrics']
                              for name in ('baseline','learned')}
    result=dict(policy=plan['candidate'],hypothesis=plan['idea'],
                implementation='Frozen, public-history categorical rank likelihoods with exact inventory and importance-corrected eight-world sampling. Unchanged four-ply masked Context Teacher continuation and root evaluation.',
                development_games=plan['development']['rounds']*14,
                validation_dos=dos,
                matched_dos_gain_percentage_points=dict(mean=100*effect['mean'],
                                                       interval_95=[100*x for x in effect['interval_95']],
                                                       complete_pairs=strength['matched_dos']['complete_pairs']),
                head_to_head=head['summary']['standings'][plan['candidate']],
                head_to_head_score_interval_95=head['complete_pair_statistics']['metrics']['score']['interval_95'],
                strength_attempts=sum(r['summary']['games'] for r in strength['matches'].values()),
                unscored_errors=sum(r['summary']['errors'] for r in strength['matches'].values()),
                prediction=evidence,prediction_paired_log_loss=prediction['paired_log_loss'],
                supported_dos_gain=strength['supported_dos_gain'],supported_head_gain=strength['supported_head_gain'],
                decision=('Desktop strength gate passed; retain immutable candidate for subsequent deployment/distillation work.' if strength['promote'] else
                          'Retain as experimental evidence; the prespecified general-strength gate did not pass.'),
                production='Unchanged student-guard-v1-normal. Registered policies and models were not modified after freeze.',
                limitations=['DOS retains original hidden-rank access; comparison is not equal-information play.',
                             'Eight-world sparse probability metrics use a common 5% inventory-prior mixture for offline scoring only.',
                             '256-world predictions are offline diagnostics, not the playing policy.',
                             'Prediction gains alone do not demonstrate useful information gathering or stronger play.'])
    write(out/'result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('corpus','fit','predict-development','register','strength','predict-validation','decide'))
    parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args();out=args.out.resolve()
    plan=json.loads((out/'plan.json').read_text())
    corpus=out/'development.jsonl.gz'
    model=ROOT/'ai/models/public-history-beliefs-v1.json'
    if args.action=='corpus':
        assert not corpus.exists()
        public_corpus(out/'development.fmtour',corpus,plan['baseline'],plan['development']['training_rounds_per_family'])
    elif args.action=='fit':
        assert not model.exists(),'immutable model already exists'
        model.parent.mkdir(exist_ok=True)
        fit(corpus,model,out/'fit-report.json')
    elif args.action=='predict-development':
        predict(corpus,model,out/'development-prediction.json','calibration',2000001)
    elif args.action=='register':register_candidate(out,plan)
    elif args.action=='strength':strength(out,plan)
    elif args.action=='decide':decision(out,plan)
    else:
        path=out/'validation.jsonl.gz'
        source=out/'validation'/('dos--'+plan['baseline']+'.fmtour')
        if not path.exists():public_corpus(source,path,plan['baseline'])
        predict(path,model,out/'validation-prediction.json','validation',plan['validation']['prediction_seed'])


if __name__=='__main__':main()
