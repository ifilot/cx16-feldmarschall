"""Historical public-root diagnostic for fixed versus capture-extended horizons.

No campaign validation games or concealed labels select roots or parameters.
All three variants see identical public prefixes and sampled-world RNG streams.
The depth-eight reference is another heuristic search, not a best-move oracle.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile

from ai_registry import ROOT, build_policy, get_policy
from campaign_depth import depth_for_actions
from teacher_bot import TeacherBot
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(roots, candidate='quiescent4'):
    result = dict(roots=len(roots), families=dict(Counter(r['family'] for r in roots)), comparisons={})
    for left, right in (('fixed4', candidate), ('fixed4', 'fixed8'), (candidate, 'fixed8')):
        changed = 0
        delta, shifts, nodes = [], [], []
        for root in roots:
            a, b = root['reports'][left], root['reports'][right]
            changed += a['selected'] != b['selected']
            values = {tuple(v['move']): v['value'] for v in b['values']}
            # Apparent loss according to the second search only, not truth.
            delta.append(values[tuple(b['selected'])] - values[tuple(a['selected'])])
            av = {tuple(v['move']): v['correction'] for v in a['values']}
            shifts.extend(abs(v['correction']-av[tuple(v['move'])]) for v in b['values'])
            nodes.append(b['nodes'] / a['nodes'] if a['nodes'] else 1)
        result['comparisons'][left+'--'+right] = dict(
            changed_decisions=changed, disagreement_rate=changed/len(roots),
            mean_second_search_score_shortfall=sum(delta)/len(delta),
            mean_absolute_action_correction_shift=sum(shifts)/len(shifts),
            mean_node_ratio=sum(nodes)/len(nodes))
    result['mean_nodes'] = {mode: sum(r['reports'][mode]['nodes'] for r in roots)/len(roots)
                            for mode in ('fixed4', candidate, 'fixed8')}
    if roots and 'wall_seconds' in roots[0]:
        result['total_wall_seconds']={mode:sum(r['wall_seconds'][mode] for r in roots)
                                      for mode in ('fixed4',candidate,'fixed8')}
        result['candidate_wall_ratio']=result['total_wall_seconds'][candidate]/result['total_wall_seconds']['fixed4']
    return result


def adaptive_mechanism(source):
    """Reuse the actually evaluated horizons on identical historical roots."""
    document=json.loads(source.read_text())
    records=[]
    for row in document['roots']:
        reports=row['reports']
        count=len(reports['fixed4']['values'])
        depth=depth_for_actions(4,count)
        adaptive=reports['fixed8' if depth==8 else 'fixed4']
        base=reports['fixed4']
        values={tuple(v['move']):v['value'] for v in reports['fixed8']['values']}
        records.append(dict(game=row['game'],army=row['army'],family=row['family'],ply=row['ply'],
            public_legal_action_count=count,selected_depth=depth,selected=adaptive['selected'],
            nodes=adaptive['nodes'],baseline_nodes=base['nodes'],
            changed_from_fixed4=adaptive['selected']!=base['selected'],
            agrees_with_fixed8=adaptive['selected']==reports['fixed8']['selected'],
            agrees_with_quiescent4=adaptive['selected']==reports['quiescent4']['selected'],
            fixed8_heuristic_shortfall=values[tuple(reports['fixed8']['selected'])]-values[tuple(adaptive['selected'])]))
    summary=dict(roots=len(records),extended_roots=sum(r['selected_depth']==8 for r in records),
        changed_decisions=sum(r['changed_from_fixed4'] for r in records),
        agrees_with_fixed8=sum(r['agrees_with_fixed8'] for r in records),
        agrees_with_quiescent4=sum(r['agrees_with_quiescent4'] for r in records),
        mean_nodes=sum(r['nodes'] for r in records)/len(records),
        total_node_ratio=sum(r['nodes'] for r in records)/sum(r['baseline_nodes'] for r in records),
        mean_fixed8_heuristic_shortfall=sum(r['fixed8_heuristic_shortfall'] for r in records)/len(records))
    return dict(source_sha256=digest(source),summary=summary,records=records)


def run(source, root_path, destination, decisions=140, capable_routes=False, informed_opponent=False):
    destination.mkdir(parents=True, exist_ok=True)
    if capable_routes and informed_opponent:
        raise ValueError('mechanism comparison isolates one hypothesis at a time')
    candidate='informed4' if informed_opponent else 'capable4' if capable_routes else 'quiescent4'
    prefix='informed-opponent' if informed_opponent else 'capable-routes' if capable_routes else 'quiescence'
    output = destination/(prefix+'-mechanism.json')
    if output.exists():
        raise ValueError('preserve completed research output; choose a new destination')
    historical = json.loads(root_path.read_text())
    if historical['source_tournament_sha256'] != digest(source):
        raise ValueError('historical roots and source tournament hashes differ')
    # Interleave through the already frozen historical development cohort.
    stride = max(1, len(historical['roots']) // decisions)
    selected_roots = historical['roots'][::stride][:decisions]
    if len(selected_roots) != decisions:
        raise ValueError('insufficient historical development roots')
    selections = {}
    for row in selected_roots:
        selections.setdefault((row['game'], row['army']), set()).add(row['ply'])
    baseline = get_policy('teacher-context-v1-normal')
    executable, receipt = build_policy(baseline['id'])
    roots = []
    with tempfile.TemporaryDirectory(prefix='feld-horizon-mechanism-') as temporary:
        temporary = Path(temporary)
        with zipfile.ZipFile(ROOT/baseline['archive']) as archive:
            archive.extractall(temporary/'source')
        # Freeze all native core semantics to the old baseline. Only the owned
        # compile-guarded rollout source comes from the current research tree.
        (temporary/'source/src/native/teacher_rollout.c').write_bytes(
            (ROOT/'src/native/teacher_rollout.c').read_bytes())
        programs = {}
        define='AI_ROLLOUT_INFORMED_OPPONENT' if informed_opponent else 'AI_ROLLOUT_CAPABLE_ROUTES' if capable_routes else 'AI_ROLLOUT_QUIESCENCE'
        for name, extra in (('base', []), ('candidate', [define])):
            program = temporary/name
            command = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Isrc/core', '-o', str(program)]
            command += ['-D'+define for define in baseline['teacher_defines']+extra]
            command += baseline['teacher_sources']
            subprocess.run(command, cwd=temporary/'source', check=True, capture_output=True)
            programs[name] = program
        runtime_hashes = {name: digest(program) for name, program in programs.items()}
        bots = {mode: TeacherBot(executable.parent/'observer', programs[program], samples=8,
                                depth=depth, blend='correction', strategic=True, context=True)
                for mode, program, depth in (('fixed4', 'base', 4), (candidate, 'candidate', 4),
                                            ('fixed8', 'base', 8))}
        try:
            with Tournament(source) as tournament:
                for game_id, army in sorted(selections):
                    game = tournament.game(game_id)
                    states, _ = replay(game)
                    events = public_events(game, states)
                    targets = selections[(game_id, army)]
                    seed = game['seed']*2+army+1
                    for bot in bots.values():
                        bot.rng.seed(seed)
                        for command in ('new '+('red','blue')[army], 'rules 0', 'difficulty normal',
                                        'seed '+str(seed), 'setup '+game[('red_setup','blue_setup')[army]]):
                            bot.observer.send(command)
                    for ply, event in enumerate(events[:max(targets)+1]):
                        if ply % 2 == army:
                            if ply in targets:
                                public = [bot.observer.ask('public','public') for bot in bots.values()]
                                strategic = [bot.observer.ask('strategy','strategy') for bot in bots.values()]
                                assert len(set(public)) == len(set(strategic)) == 1
                                reports = {}
                                wall_seconds={}
                                streams = []
                                order=list(bots)
                                rotation=len(roots)%len(order)
                                for mode in order[rotation:]+order[:rotation]:
                                    bot=bots[mode]
                                    started=time.perf_counter()
                                    bot.choose()
                                    wall_seconds[mode]=time.perf_counter()-started
                                    reports[mode] = bot.last_report
                                    streams.append(repr(bot.rng.getstate()))
                                assert len(set(streams)) == 1, 'world RNG consumption changed'
                                roots.append(dict(game=game_id, army=army, family=game['family'],
                                                  ply=ply, public_sha256=hashlib.sha256(public[0].encode()).hexdigest(),
                                                  reports=reports,wall_seconds=wall_seconds))
                                print('Historical horizon root',len(roots),'/',decisions,flush=True)
                            else:
                                for bot in bots.values():
                                    bot.observer.ask('go','move')
                            for bot in bots.values():
                                bot.observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
                        for bot in bots.values():
                            bot.observer.send(event)
        finally:
            for bot in bots.values():
                bot.close()
    test_pattern='test_campaign_informed_opponent.py' if informed_opponent else 'test_campaign_routes.py' if capable_routes else 'test_campaign_quiescence.py'
    tests = subprocess.run(['python3','-m','unittest','discover','-s','tools','-p',
                            test_pattern,'-v'], cwd=ROOT, capture_output=True,
                           text=True, check=True)
    (destination/(prefix+'-native-tests.log')).write_text(tests.stdout+tests.stderr)
    result = dict(kind='historical-public-horizon-mechanism', strength_evidence=False,
                  input='Own setup and public history only; hypothetical armies sampled identically.',
                  source=str(source.relative_to(ROOT)), source_sha256=digest(source),
                  historical_roots_sha256=digest(root_path), native_runtime_sha256=runtime_hashes,
                  current_rollout_sha256=digest(ROOT/'src/native/teacher_rollout.c'),
                  baseline_receipt=receipt, samples=8, extension_policy_decision_cap=0 if capable_routes or informed_opponent else 4,
                  native_privacy_and_capture_tests_passed=True,
                  candidate=candidate,summary=summarize(roots,candidate), roots=roots)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary'],indent=2),flush=True)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour')
    parser.add_argument('--roots',type=Path,default=ROOT/'docs/ai-restrained-search-2026-10-15/development-roots.json')
    parser.add_argument('--out',type=Path,default=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon')
    parser.add_argument('--decisions',type=int,default=140)
    parser.add_argument('--capable-routes',action='store_true')
    parser.add_argument('--informed-opponent',action='store_true')
    parser.add_argument('--adaptive-existing',type=Path,
                        help='derive adaptive root choices from an existing three-horizon diagnostic')
    args=parser.parse_args()
    if args.adaptive_existing:
        print(json.dumps(adaptive_mechanism(args.adaptive_existing),indent=2))
    else:
        run(args.source,args.roots,args.out,args.decisions,args.capable_routes,args.informed_opponent)
