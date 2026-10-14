"""Search diverse legal deployments while freezing every move policy and opponent."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import zipfile

from arena import deployments, play
from benchmark_ai import statistics
from feldmarschall import ROOT, STRESS_SETUPS, presets, random_setup, valid_setup

FAMILIES=(*STRESS_SETUPS,'presets','broad-mixed')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(setup):return 'setup-'+hashlib.sha256(setup.encode()).hexdigest()[:12]
def separation(a,b):return sum(x!=y for x,y in zip(a,b))


def mutate(setup,rng):
    cells=list(setup)
    for _ in range(rng.randint(2,6)):
        a,b=rng.sample(range(40),2);cells[a],cells[b]=cells[b],cells[a]
    return ''.join(cells)


def diverse(ranked, count, minimum=8):
    chosen=[]
    for setup,score in ranked:
        if all(separation(setup,other)>=minimum for other in chosen):chosen.append(setup)
        if len(chosen)==count:return chosen
    raise ValueError('not enough distinct strong setups for the requested portfolio')


def freeze(out,difficulty,phase,seed):
    engines={
        'current':str(ROOT/'build/feldmarschall-ai-coordinated')+' --difficulty '+difficulty,
        'v020':str(ROOT/'build/feldmarschall-ai-v020'),
        'planned':str(ROOT/'build/feldmarschall-ai-planned'),
        'adaptive':str(ROOT/'build/feldmarschall-ai-adaptive-progress')+' --difficulty '+difficulty,
        'easy':str(ROOT/'build/feldmarschall-engine')+' --difficulty easy',
        'greedy':shlex.join([sys.executable,str(ROOT/'tools/bots.py'),'greedy'])}
    out.mkdir(parents=True,exist_ok=False);(out/'engines').mkdir()
    source=ROOT/'tools/optimize_ai_deployments.py'
    provenance={'phase':phase,'strategy':'deployment-genetic-search' if phase=='development' else 'deployment-heldout-validation',
        'suite':'broad-deployment','difficulty':difficulty,'seed':seed,'command':sys.argv,
        'candidate_source':str(source),'source_sha256':sha(source),'fixed_policy':'coordinated missions; student disabled',
        'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'pairing':'Candidate and opponent setups follow their engines when both sides are swapped. Both games share the move seed.',
        'engine_sha256':{},'support_sha256':{},'engine_commands':engines,'run_engine_commands':{}}
    for name,command in engines.items():
        executable,*arguments=shlex.split(command);target=out/'engines'/name;shutil.copy2(executable,target)
        for index,value in enumerate(arguments):
            path=Path(value)
            if path.suffix=='.py' and path.is_file():
                support=out/'engines/support'/name;support.mkdir(parents=True,exist_ok=True)
                for dependency in path.parent.glob('*.py'):
                    copy=support/dependency.name;shutil.copy2(dependency,copy)
                    provenance['support_sha256'][str(copy.relative_to(out))]=sha(copy)
                arguments[index]=str((support/path.name).resolve())
        provenance['engine_sha256'][name]=sha(target)
        provenance['run_engine_commands'][name]=shlex.join([str(target.resolve()),*arguments])
    with zipfile.ZipFile(out/'sources.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        for directory in ('src','tests','tools'):
            for path in (ROOT/directory).rglob('*'):
                if path.suffix in ('.c','.h','.s','.cfg','.py','.md'):archive.write(path,str(path.relative_to(ROOT)))
        for name in ('Makefile','src/Makefile'):archive.write(ROOT/name,name)
    provenance['source_archive_sha256']=sha(out/'sources.zip')
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    return provenance


def trials(seed,rounds,opponents):
    rng=random.Random(seed);cases=[]
    for family in FAMILIES:
        for round_index in range(rounds):
            layout=deployments(family,rng)
            own_control=random_setup(rng)
            for opponent in opponents:
                cases.append({'family':family,'round':round_index,'opponent':opponent,
                              'opponent_setup':layout,'random_control':own_control,
                              'seed':rng.randrange(1,60000)})
    return cases


def evaluate(layouts,cases,provenance,pool,output,generation):
    jobs=[];metadata=[];commands=provenance['run_engine_commands']
    for name,layout in layouts.items():
        for case_index,case in enumerate(cases):
            own=case['random_control'] if layout is None else layout
            if not valid_setup(own) or not valid_setup(case['opponent_setup']):raise ValueError('illegal setup')
            opponent=case['opponent'];foe=case['opponent_setup']
            for blue in (False,True):
                names=(opponent,'current') if blue else ('current',opponent)
                setups=(foe,own) if blue else (own,foe)
                jobs.append((names,tuple(commands[side] for side in names),setups,case['seed'],1000,True))
                metadata.append({'group':case['family'],'round':case['round'],'deployments':list(setups),
                    'comparison':name+'-vs-league','setup_id':name,'opponent':opponent,'case':case_index,
                    'generation':generation,'candidate_setup':own,'candidate_blue':blue})
    games=[]
    for index,game in enumerate(pool.map(play,jobs)):
        game.update(metadata[index]);games.append(game);output.write(json.dumps(game)+'\n')
        if game['reason'].startswith('illegal'):raise ValueError(game)
        if (index+1)%250==0:print(f'generation {generation}: {index+1}/{len(jobs)} games',flush=True)
    output.flush()
    return games


def score(games):
    return sum(1 if game['winner']=='current' else .5 if game['winner'] is None else 0 for game in games)/len(games)


def comparisons(games):
    grouped=defaultdict(list)
    for game in games:grouped[game['comparison']].append(game)
    return {name:{'overall':statistics(selected),'opponents':{
        opponent:statistics([game for game in selected if game['opponent']==opponent])
        for opponent in sorted({game['opponent'] for game in selected})}}
        for name,selected in grouped.items()}


def delta(games,candidate,control):
    points=defaultdict(list)
    blocks={}
    for game in games:
        if game['setup_id'] not in (candidate,control):continue
        points[(game['setup_id'],game['case'])].append(1 if game['winner']=='current' else .5 if game['winner'] is None else 0)
        blocks[game['case']]=(game['group'],game['round'])
    indices=sorted(case for name,case in points if name==candidate)
    differences=[sum(points[(candidate,case)])/2-sum(points[(control,case)])/2 for case in indices]
    assert all(len(points[(name,case)])==2 for case in indices for name in (candidate,control))
    clustered=defaultdict(list)
    for case,difference in zip(indices,differences):clustered[blocks[case]].append(difference)
    families=defaultdict(list)
    for (family,round_index),values in clustered.items():families[family].append(sum(values)/len(values))
    rng=random.Random(8675309)
    # All opponent policies evaluated on a given layout belong to one block.
    # Resample within family so its predefined portfolio weight stays fixed.
    samples=sorted(sum(sum(rng.choices(values,k=len(values)))/len(values) for values in families.values())/
                   len(families) for _ in range(10000))
    return {'paired_cases':len(differences),'score_difference':sum(differences)/len(differences),
            'deployment_blocks':len(clustered),'confidence_method':'stratified bootstrap of complete layout/round blocks, all opponents and sides bundled',
            'paired_bootstrap_95':[samples[249],samples[9749]]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--validate',type=Path,help='completed search directory whose portfolio is fixed before validation')
    parser.add_argument('--difficulty',choices=('normal','hard'),default='normal')
    parser.add_argument('--population',type=int,default=16)
    parser.add_argument('--generations',type=int,default=4)
    parser.add_argument('--rounds',type=int,default=1)
    parser.add_argument('--jobs',type=int,default=4)
    parser.add_argument('--seed',type=int,default=41261014)
    args=parser.parse_args()
    if min(args.generations,args.rounds,args.jobs)<1 or args.population<16:parser.error('positive counts and population >=16 required')
    provenance=freeze(args.out,args.difficulty,'validation' if args.validate else 'development',args.seed)
    cases=trials(args.seed,args.rounds,[name for name in provenance['run_engine_commands'] if name!='current'])
    (args.out/'trials.json').write_text(json.dumps(cases,indent=2)+'\n')
    all_games=[];cache={};genealogy=[];rng=random.Random(args.seed+12345)
    with (args.out/'games.jsonl').open('w') as output,ProcessPoolExecutor(args.jobs) as pool:
        if args.validate:
            portfolio=json.loads((args.validate/'portfolio.json').read_text())
            layouts={identity(setup):setup for setup in portfolio['selected']}
            layouts['preset-control']=portfolio['preset_control'];layouts['random-control']=None
            all_games=evaluate(layouts,cases,provenance,pool,output,'heldout')
            report={'provenance':provenance,'comparisons':comparisons(all_games),
                'setup_deltas':{name:{control:delta(all_games,name,control) for control in ('preset-control','random-control')}
                                for name in layouts if name not in ('preset-control','random-control')},
                'portfolio_sha256':sha(args.validate/'portfolio.json')}
            (args.out/'portfolio.json').write_text(json.dumps(portfolio,indent=2)+'\n')
        else:
            originals=[setup for _,setup in presets()]
            population=originals+[deployments(family,rng) for family in STRESS_SETUPS]
            while len(population)<args.population:population.append(deployments(rng.choice(FAMILIES),rng))
            for generation in range(args.generations):
                new={identity(setup):setup for setup in population if setup not in cache}
                games=evaluate(new,cases,provenance,pool,output,generation);all_games.extend(games)
                for name,setup in new.items():cache[setup]=score([game for game in games if game['setup_id']==name])
                ranked=sorted(cache.items(),key=lambda item:(-item[1],item[0]))
                parents=diverse(ranked,4,4);genealogy.append({'generation':generation,'new_layouts':len(new),
                    'leaders':[{'setup':setup,'score':cache[setup]} for setup in parents]})
                print(f'generation {generation}: {len(cache)} unique layouts, best score {ranked[0][1]:.1%}',flush=True)
                population=parents[:]
                while len(population)<args.population:
                    child=mutate(rng.choice(parents),rng)
                    if child not in cache and child not in population:population.append(child)
            ranked=sorted(((setup,value) for setup,value in cache.items() if setup not in originals),key=lambda item:(-item[1],item[0]))
            selected=diverse(ranked,3,8)
            control=max(originals,key=lambda setup:cache[setup])
            portfolio={'selected':selected,'selected_development_scores':[cache[setup] for setup in selected],
                'preset_control':control,'preset_control_score':cache[control],'minimum_pairwise_hamming':8,
                'difficulty':args.difficulty,'seed':args.seed,'searched_layouts':len(cache),
                'genealogy':genealogy,'rankings':[{'setup':setup,'score':value} for setup,value in sorted(cache.items(),key=lambda item:-item[1])]}
            (args.out/'portfolio.json').write_text(json.dumps(portfolio,indent=2)+'\n')
            report={'provenance':provenance,'comparisons':comparisons(all_games),'portfolio':portfolio}
    (args.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.validate:print(json.dumps(report['setup_deltas'],indent=2))
    else:print(json.dumps({key:portfolio[key] for key in ('selected','selected_development_scores','preset_control_score','searched_layouts')},indent=2))


if __name__=='__main__':main()
