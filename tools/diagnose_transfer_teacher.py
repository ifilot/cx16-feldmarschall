"""Resample a frozen teacher on outcome-blind, stratified retained public roots."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shlex
import time
import zipfile

from ai_registry import ROOT, build_policy
from feldmarschall import Engine, parse_square
from teacher_bot import TeacherBot
from train_teacher_student import canonical_shuttle, own_initial, shuttle_hex


def digest(data):
    return hashlib.sha256(data).hexdigest()


def restore(engine, record):
    info = record['input']; army = info['army']
    seed = int(digest(record['id'].encode())[:8], 16)
    engine.send('difficulty normal')
    engine.send('seed ' + str(seed % 65535 + 1))
    engine.send('new ' + ('red', 'blue')[army])
    engine.send('setup ' + own_initial(info, record['public_history']))
    for ply, event in enumerate(record['public_history']):
        if ply % 2 == army:
            engine.ask('go', 'move')
            engine.ask('played ' + ' '.join(event.split()[1:3]), 'playedok')
        engine.send(event)
    side, board, lost, shuttle = engine.ask('public', 'public').split()
    assert [int(side), board, lost, canonical_shuttle(shuttle)] == [
        army, info['board_hex'], info['enemy_lost_hex'], canonical_shuttle(shuttle_hex(info))]


def run_root(job):
    record, observer, teacher, production = job
    runs = []
    for batch in (0, 1):
        bot = TeacherBot(Path(observer), Path(teacher), samples=8, depth=4,
                         blend='correction', strategic=True, context=True)
        try:
            restore(bot.observer, record)
            context = bot.observer.ask('strategy', 'strategy')
            seed = int(digest(('transfer-stability:' + str(batch) + ':' + record['id']).encode())[:16], 16)
            bot.rng.seed(seed)
            started = time.perf_counter(); move = bot.choose()
            report = bot.last_report
            ordered = sorted(report['values'], key=lambda row: row['value'], reverse=True)
            runs.append(dict(batch=batch, world_seed=seed, selected=move, parent=report['parent'],
                             context_sha256=digest(bytes.fromhex(context)),
                             margin=ordered[0]['value']-ordered[1]['value'] if len(ordered)>1 else None,
                             nodes=report['nodes'], effective_samples=report['effective_samples'],
                             values=report['values'], elapsed_seconds=time.perf_counter()-started))
        finally:
            bot.close()
    engine = Engine(shlex.quote(production))
    try:
        restore(engine, record)
        move = tuple(map(parse_square, engine.ask('go', 'move').split()[:2]))
    finally:
        engine.close()
    assert runs[0]['context_sha256'] == runs[1]['context_sha256']
    assert tuple(runs[0]['parent']) == tuple(runs[1]['parent'])
    value_maps = [{tuple(v['move']): v['value'] for v in r['values']} for r in runs]
    cross_regret = [max(value_maps[b].values())-value_maps[b][tuple(runs[1-b]['selected'])] for b in (0,1)]
    return dict(id=record['id'], source=record['source'], split_group=record['split_group'],
                production_move=move, observer_production_parity=move==tuple(runs[0]['parent']),
                choice_agrees=runs[0]['selected']==runs[1]['selected'],
                teacher_changes_production=[tuple(r['selected'])!=move for r in runs],
                cross_batch_score_regret=cross_regret, runs=runs)


def select(records, count):
    buckets=defaultdict(list)
    for r in records:
        key=(r['source']['group'],r['source']['phase'],r['input']['army'])
        buckets[key].append(r)
    for values in buckets.values():
        values.sort(key=lambda r:digest(('transfer-stability-select:'+r['id']).encode()))
    keys=sorted(buckets,key=lambda k:digest(repr(k).encode()))
    chosen=[]
    while len(chosen)<count:
        changed=False
        for key in keys:
            if buckets[key] and len(chosen)<count:
                chosen.append(buckets[key].pop(0));changed=True
        if not changed:break
    return chosen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--positions',type=int,default=32)
    parser.add_argument('--jobs',type=int,default=4)
    parser.add_argument('--out',type=Path,default=ROOT/'docs/ai-transfer-2026-10-15/checks/stability.json')
    args=parser.parse_args()
    archive=ROOT/'docs/ai-cycle-2026-10-15/student-model/training-evidence.zip'
    with zipfile.ZipFile(archive) as bundle:
        raw=bundle.read('public-inputs.jsonl')
    records=[json.loads(line) for line in raw.splitlines()]
    # The retained public export omits source labels, so recover selection labels
    # from the original development corpus without exposing them to the teacher.
    from build_teacher_corpus import extract, select as corpus_select
    from tournament_store import Tournament
    source=ROOT/'docs/ai-cycle-2026-10-15/tournaments/teacher-development/teacher-context-v1-normal--student-guard-v1-normal.fmtour'
    with Tournament(source) as tournament:
        games=[]
        for row in tournament.games():
            game=tournament.game(row['id'])
            games.append(dict(game,group=game['family'],deployments=[game['red_setup'],game['blue_setup']]))
    reconstructed={r['id']:r for r in extract(games,corpus_select(games,8),digest(source.read_bytes()))}
    for r in records:
        original=reconstructed[r['id']]
        assert r['input']==original['input'] and r['public_history']==original['public_history']
        r['source']=original['source']
    chosen=select(records,args.positions)
    executable,receipt=build_policy('teacher-context-v1-normal')
    # This frozen production-equivalent diagnostic policy adds the forced-history
    # acknowledgement absent from the production executable's public protocol.
    production,production_receipt=build_policy('guard-diagnostics-v1-normal')
    jobs=[(r,str(executable.parent/'observer'),str(executable.parent/'teacher'),str(production)) for r in chosen]
    results=[]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for result in pool.map(run_root,jobs):
            results.append(result);print(f'{len(results)}/{len(chosen)} roots',flush=True)
    summary=dict(positions=len(results),agreed_choices=sum(r['choice_agrees'] for r in results),
                 observer_production_parity=sum(r['observer_production_parity'] for r in results),
                 changed_production_per_batch=[sum(r['teacher_changes_production'][b] for r in results) for b in (0,1)],
                 mean_cross_batch_score_regret=sum(sum(r['cross_batch_score_regret']) for r in results)/(2*len(results)),
                 coverage=dict(Counter(f"{r['source']['group']}:{r['source']['phase']}:{r['input']['army']}" for r in chosen)))
    report=dict(summary=summary,positions=results,teacher=receipt,production=production_receipt,
                corpus_archive_sha256=digest(archive.read_bytes()),public_inputs_sha256=digest(raw),
                source_tournament_sha256=digest(source.read_bytes()),script_sha256=digest(Path(__file__).read_bytes()),
                selection='Outcome-blind deterministic round-robin across available family/phase/army buckets; retained development corpus only.',
                scope='Two independent batches of eight consistent sampled worlds, full public history, fixed observer RNG. Production parity uses frozen Guard Diagnostics, previously checked equivalent on 3901 decisions, because original production lacks forced-history played acknowledgement. Agreement is repeatability, not correctness or game strength. Score regret is teacher internal utility, not winning probability. Reused development roots are not new validation.')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
