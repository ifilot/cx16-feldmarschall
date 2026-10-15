"""Calibrate, freeze and evaluate the three-arm Classic root-selection test."""
import argparse
from collections import Counter, defaultdict
import contextlib
import copy
import hashlib
import json
from pathlib import Path
import random

from ai_registry import ROOT, build_policy, catalog, get_policy, register
from information_strategy_cycle import analyze_match, bootstrap, digest, validate_metadata
from root_policy import RootPolicy, SCHEMA, log_softmax
from teacher_bot import TeacherBot
from test_information_parent_parity import public_events
from tournament import run
from tournament_store import Tournament, replay

OUT = ROOT/'docs/ai-restrained-search-2026-10-15'


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def config_path(mode):
    return ROOT/'ai/models'/('native-root-'+mode+'-v1.json')


def collect(out, plan):
    destination=out/'development-roots.json'
    assert not destination.exists(),'development roots already frozen'
    source=out/'development.fmtour'
    with Tournament(source) as tournament:
        assert tournament.metadata()['status']=='complete'
        longest={}
        for row in tournament.games():
            if row['result']=='error':continue
            if row['family'] not in longest or row['plies']>longest[row['family']]['plies']:
                longest[row['family']]=row
        games=[tournament.game(longest[f]['id']) for f in plan['families']]
    executable,_=build_policy(plan['baseline'])
    bot=TeacherBot(executable.parent/'observer',executable.parent/'teacher',samples=8,depth=4,
                   blend='correction',strategic=True,context=True)
    rng=random.Random(plan['development']['root_seed'])
    roots=[]
    try:
        for game in games:
            states,_=replay(game)
            events=public_events(game,states)
            for side in (0,1):
                available=list(range(side,min(len(events),plan['development']['maximum_root_ply']),2))
                quota=plan['development']['roots_per_side_per_family']
                assert len(available)>=quota,(game['family'],len(available))
                selected=set(rng.sample(available,quota))
                seed=game['seed']*2+side+1
                bot.rng.seed(seed)
                for command in ('new '+('red','blue')[side],'rules 0','difficulty normal',
                                'seed '+str(seed),'setup '+game[('red_setup','blue_setup')[side]]):
                    bot.observer.send(command)
                for ply,event in enumerate(events[:max(selected)+1]):
                    if ply % 2 == side:
                        if ply in selected:
                            bot.choose()
                            roots.append(dict(game=game['id'],family=game['family'],army=side,ply=ply,
                                              report=bot.last_report))
                        else:bot.observer.ask('go','move')
                        bot.observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
                    bot.observer.send(event)
    finally:bot.close()
    result=dict(roots=roots,source_tournament_sha256=digest(source),
                samples=8,depth=4,input='Own setup and public moves/battles only; fixed legal prefixes, not strength games.',
                root_seed=plan['development']['root_seed'],families=dict(Counter(r['family'] for r in roots)))
    write(destination,result)
    print('Collected',len(roots),'public roots',flush=True)


def root_values(row):
    values=row['report']['values']
    return ({tuple(v['move']):v['parent_score'] for v in values},
            {tuple(v['move']):v['correction'] for v in values})


def calibrate(out, plan):
    paths=[config_path(mode) for mode in ('probability-control','kl-restrained')]
    assert not any(p.exists() for p in paths),'settings already frozen; create a new policy version'
    source=out/'development-roots.json'
    roots=json.loads(source.read_text())['roots']
    eligible=[r for r in roots if max(v['parent_score'] for v in r['report']['values'])<30000]
    settings=plan['calibration']
    temperatures={}
    for temperature in settings['temperature_grid']:
        masses=[]
        for row in eligible:
            scores,_=root_values(row)
            moves=sorted(scores);best=max(scores.values())
            logs=log_softmax([(scores[m]-best)/temperature for m in moves])
            import math
            masses.append(sum(math.exp(lp) for m,lp in zip(moves,logs) if scores[m]==best))
        temperatures[str(temperature)]=sum(masses)/len(masses)
    acceptable=[t for t in settings['temperature_grid'] if temperatures[str(t)]>=settings['native_top_tier_mass_target']]
    temperature=max(acceptable) if acceptable else min(settings['temperature_grid'])
    dummy=dict(schema=SCHEMA,mode='probability-control',temperature=temperature,kl_budget=1.)
    control=RootPolicy(dummy)
    control_kl=[control.distribution(*root_values(row))['kl'] for row in eligible]
    target=settings['mean_kl_fraction_target']*sum(control_kl)/len(control_kl)
    lower,upper=0.,max(control_kl)
    for _ in range(64):
        middle=(lower+upper)/2
        if sum(min(k,middle) for k in control_kl)/len(control_kl)>target:upper=middle
        else:lower=middle
    budget=max(settings['minimum_kl_budget'],min(settings['maximum_kl_budget'],(lower+upper)/2))
    for mode,path in zip(('probability-control','kl-restrained'),paths):
        write(path,dict(schema=SCHEMA,mode=mode,temperature=temperature,kl_budget=budget,
                        calibration_roots_sha256=digest(source),
                        calibration='Temperature from native score-tier probabilities; KL budget halves mean control change, subject to prespecified bounds. No win labels or validation data.'))
    write(out/'calibration.json',dict(roots=len(roots),nonwinning_roots=len(eligible),
                                    temperature_top_tier_mass=temperatures,selected_temperature=temperature,
                                    control_mean_kl=sum(control_kl)/len(control_kl),target_mean_kl=target,
                                    selected_kl_budget=budget,settings_sha256={p.name:digest(p) for p in paths}))
    mechanism(out,plan)


def mechanism(out,plan):
    roots=json.loads((out/'development-roots.json').read_text())['roots']
    policies={mode:RootPolicy.load(config_path(mode)) for mode in ('probability-control','kl-restrained')}
    records=[]
    for row in roots:
        scores,corrections=root_values(row)
        if max(scores.values())>=30000:continue
        results={mode:policy.distribution(scores,corrections) for mode,policy in policies.items()}
        control,candidate=results.values()
        assert control['prior_probabilities']==candidate['prior_probabilities']
        assert candidate['control_kl']==control['kl']
        assert candidate['kl']<=policies['kl-restrained'].budget+1e-10
        assert candidate['kl']<=control['kl']+1e-10
        parent=tuple(row['report']['parent'])
        for result in results.values():
            result['native_move_override_probability']=1-result['probabilities'][result['moves'].index(parent)]
        records.append(dict(game=row['game'],family=row['family'],army=row['army'],ply=row['ply'],
                            rollout_values_sha256=hashlib.sha256(json.dumps(row['report']['values'],sort_keys=True).encode()).hexdigest(),
                            policies=results))
    summaries={}
    for mode in policies:
        summaries[mode]={key:sum(r['policies'][mode][key] for r in records)/len(records)
                         for key in ('kl','entropy','native_top_tier_mass','native_move_override_probability','expected_corrected_score')}
        summaries[mode]['constraint_active_fraction']=sum(r['policies'][mode]['constrained'] for r in records)/len(records)
    write(out/'mechanism.json',dict(roots=len(records),summaries=summaries,records=records,
                                   same_rollout_values=True,strength_evidence=False))


def register_policies(out,plan):
    before=out/'registry-before.json'
    assert not before.exists(),'registration already started; never replace an existing ID'
    write(before,dict(policies=catalog()))
    for key,mode in (('control','probability-control'),('candidate','kl-restrained')):
        settings=config_path(mode)
        spec=copy.deepcopy(get_policy(plan['baseline']))
        for field in ('archive','source_sha256'):spec.pop(field)
        spec.update(id=plan[key],name=('Probability Control' if key=='control' else 'KL Restrained Search')+' Teacher v1 / Normal',
                    description=plan['hypothesis']+' '+mode,status='experimental',
                    model='Unchanged Context Teacher v1 guarded student and eight-world masked sampler; frozen native-score root-selection settings.',
                    information_model='Own army and public history only; no diagnostic truth, learned beliefs or information bonuses.',
                    root_policy=str(settings.relative_to(ROOT)),root_policy_sha256=digest(settings),
                    asset_files=[str(settings.relative_to(ROOT))])
        spec['driver_args']+=['--root-policy',settings.name]
        write(out/(key+'-spec.json'),spec)
        register(spec)
    identities=(plan['baseline'],plan['control'],plan['candidate'],plan['opponent'])
    write(out/'frozen-policies.json',{p:get_policy(p) for p in identities})


def matches(plan):
    config=plan['validation']
    for key in ('baseline','control','candidate'):
        yield dict(name='dos--'+plan[key],group='dos',policy=plan[key],opponent=plan['opponent'],
                   seed=config['dos_seed'],rounds=config['dos_rounds'])
    for first,second in (('control','baseline'),('candidate','baseline'),('candidate','control')):
        yield dict(name='head--'+plan[first]+'--'+plan[second],group='head',policy=plan[first],opponent=plan[second],
                   seed=config['head_seed'],rounds=config['head_rounds'])


def strength(out,plan,run_games):
    frozen=json.loads((out/'frozen-policies.json').read_text())
    assert all(get_policy(p)==spec for p,spec in frozen.items())
    before=json.loads((out/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)]==before
    output=out/'validation';output.mkdir(exist_ok=True)
    reports,pairs,signature={},{},None
    for match in matches(plan):
        path=output/(match['name']+'.fmtour')
        if not path.exists():
            assert run_games,'required tournament missing'
            print('Running',match['name'],flush=True)
            with path.with_suffix('.log').open('x') as log,contextlib.redirect_stdout(log):
                summary=run(match['policy'],match['opponent'],path,rounds=match['rounds'],seed=match['seed'],
                            jobs=plan['jobs'],families=plan['families'],max_plies=plan['max_plies'],backend=plan['backend'])
                print(json.dumps(summary),flush=True)
        validate_metadata(path,match,plan,frozen)
        report,complete,current=analyze_match(path,match,plan,frozen)
        reports[match['name']]=report
        if match['group']=='dos':
            if signature is None:signature=current
            assert signature==current,'DOS armies or seeds differ'
            pairs[match['policy']]=complete
        write(output/(match['name']+'.report.json'),report)
        print('Verified',match['name'],report['summary']['standings'][match['policy']],flush=True)
    comparisons={}
    for first,second in (('candidate','control'),('candidate','baseline'),('control','baseline')):
        new,old=pairs[plan[first]],pairs[plan[second]]
        common=sorted(new.keys() & old.keys())
        name=first+'_minus_'+second
        comparison=bootstrap([(new[k][0],dict(score=new[k][1]['score']-old[k][1]['score'])) for k in common])
        head_name='head--'+plan[first]+'--'+plan[second]
        head=reports[head_name]['complete_pair_statistics']['metrics']['score']
        comparison['head_score']=head
        comparison['dos_gain_supported']=comparison['metrics']['score']['interval_95'][0]>0
        comparison['head_gain_supported']=head['interval_95'][0]>.5
        comparison['both_supported']=comparison['dos_gain_supported'] and comparison['head_gain_supported']
        comparisons[name]=comparison
    report=dict(matches=reports,comparisons=comparisons,frozen_policies=frozen,
                previous_policies_unchanged=len(before),
                mechanism_supported=comparisons['candidate_minus_control']['both_supported'],
                practical_gain_supported=comparisons['candidate_minus_baseline']['both_supported'])
    report['strength_gate_passed']=report['mechanism_supported'] and report['practical_gain_supported']
    write(out/'strength-report.json',report)
    return report


def decision(out,plan):
    report=json.loads((out/'strength-report.json').read_text())
    summaries={key:report['matches']['dos--'+plan[key]]['summary']['standings'][plan[key]]
               for key in ('baseline','control','candidate')}
    comparisons={}
    for name,comparison in report['comparisons'].items():
        effect=comparison['metrics']['score']
        comparisons[name]=dict(dos_gain_percentage_points=100*effect['mean'],
                               dos_interval_95=[100*v for v in effect['interval_95']],
                               complete_pairs=comparison['complete_pairs'],
                               head_score=comparison['head_score'],both_supported=comparison['both_supported'])
    result=dict(hypothesis=plan['hypothesis'],policies={k:plan[k] for k in ('baseline','control','candidate')},
                dos=summaries,comparisons=comparisons,
                development=json.loads((out/'calibration.json').read_text()),
                development_root_games=len({r['game'] for r in json.loads((out/'development-roots.json').read_text())['roots']}),
                mechanism=json.loads((out/'mechanism.json').read_text())['summaries'],
                mechanism_supported=report['mechanism_supported'],practical_gain_supported=report['practical_gain_supported'],
                strength_gate_passed=report['strength_gate_passed'],
                validation_attempts=sum(r['summary']['games'] for r in report['matches'].values()),
                unscored_errors=sum(r['summary']['errors'] for r in report['matches'].values()),
                decision=('Strength gate passed; preserve candidate for separate deployment work.' if report['strength_gate_passed'] else
                          'Preserve both policies as experimental evidence; the prespecified strength gate did not pass.'),
                production='Unchanged student-guard-v1-normal',
                limitations='DOS retains original hidden-rank access. This is a score-derived native prior, not a reproduction of Ataraxos networks. Development distribution diagnostics do not prove strength or identify why an opponent wins.')
    write(out/'result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('collect','calibrate','register','run','analyze','decide'))
    parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args();out=args.out.resolve()
    plan=json.loads((out/'plan.json').read_text())
    if args.action=='collect':collect(out,plan)
    elif args.action=='calibrate':calibrate(out,plan)
    elif args.action=='register':register_policies(out,plan)
    elif args.action in ('run','analyze'):strength(out,plan,args.action=='run')
    else:decision(out,plan)


if __name__=='__main__':main()
