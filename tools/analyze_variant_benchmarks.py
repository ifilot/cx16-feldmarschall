"""Verify variant trial matrices and compare matched complete league blocks."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import shlex
import zipfile

from feldmarschall import STRESS_SETUPS, valid_setup


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(run, plan, rules, level):
    provenance=json.loads((run/'provenance.json').read_text())
    report=json.loads((run/'summary.json').read_text())
    assert report['provenance']==provenance
    assert provenance['rules']==rules and provenance['difficulty']==level and provenance['phase']==plan['phase']
    assert provenance['rounds_per_group']==plan['rounds_per_family']
    assert set(provenance['groups'])=={*STRESS_SETUPS,'presets','broad-mixed'}
    assert sorted(provenance['groups'].values())==list(range(20261101+plan['seed_offset'],20261108+plan['seed_offset']))
    for name,expected in provenance['engine_sha256'].items():assert digest(run/'engines'/name)==expected
    for name,expected in provenance['support_sha256'].items():assert digest(run/name)==expected
    assert provenance['engine_sha256']['current']==plan['program_sha256']['feldmarschall-engine']
    for name,program in [('v020','feldmarschall-ai-v020'),('planned','feldmarschall-ai-planned'),('adaptive','feldmarschall-ai-adaptive-progress')]:
        assert provenance['engine_sha256'][name]==plan['program_sha256'][program]
    assert provenance['support_sha256']['engines/support/referee/rules.so']==plan['program_sha256']['librules-variant.so']
    assert digest(run/'sources.zip')==provenance['source_archive_sha256']
    with zipfile.ZipFile(run/'sources.zip') as sources:
        for name,expected in plan.get('logic_sha256',{}).items():assert hashlib.sha256(sources.read(name)).hexdigest()==expected
    for name,difficulty in [('current',level),('adaptive','normal'),('easy','easy')]:
        arguments=shlex.split(provenance['run_engine_commands'][name])
        assert arguments[arguments.index('--difficulty')+1]==difficulty
    games=[json.loads(line) for line in (run/'games.jsonl').read_text().splitlines()]
    assert len(games)==70*plan['rounds_per_family']
    pairs=defaultdict(list);blocks=defaultdict(list);opponents=defaultdict(list);families=defaultdict(list)
    for game in games:
        assert game['rules']==rules and game['observations_audited']
        assert not game['reason'].startswith('illegal') and len(game['moves'])==game['plies']==len(game['events'])
        if 'view_checks' in game:assert game['view_checks']==2*(game['plies']+1)
        assert all(valid_setup(setup) for setup in game['deployments'])
        pair=(game['group'],game['round'],game['comparison']);pairs[pair].append(game)
        point=.5 if game['winner'] is None else float(game['winner']=='current')
        blocks[pair[:2]].append(point);opponents[game['comparison']].append(point);families[game['group']].append(point)
    assert len(pairs)==35*plan['rounds_per_family']
    for pair in pairs.values():
        assert len(pair)==2 and pair[0]['red']==pair[1]['blue'] and pair[0]['blue']==pair[1]['red']
        assert pair[0]['seed']==pair[1]['seed'] and pair[0]['deployments']==pair[1]['deployments']
    assert all(len(values)==10 for values in blocks.values())
    for name,values in opponents.items():
        stored=report['comparisons'][name]['overall']
        assert stored['games']==len(values) and stored['score']==sum(values)/len(values)
    means={key:sum(values)/len(values) for key,values in blocks.items()}
    counts=Counter()
    for game in games:counts.update(game['event_counts'])
    result={'games':len(games),'score':sum(means.values())/len(means),'block_bootstrap_95':interval(means),
            'capped':sum(g['reason']=='ply limit' for g in games),'reasons':dict(Counter(g['reason'] for g in games)),
            'event_counts':dict(counts),'families':{k:sum(v)/len(v) for k,v in families.items()},
            'view_checks':sum(g.get('view_checks',2*(g['plies']+1)) for g in games),
            'private_rescues':sum(isinstance(e,dict) and e['own'].endswith(' 0') for g in games for turn in g['events'] for e in turn),
            'opponents':{k:sum(v)/len(v) for k,v in opponents.items()}}
    matrix={(g['group'],g['round'],g['comparison'],g['red'],g['blue']):(g['seed'],g['deployments']) for g in games}
    return result,means,matrix


def interval(blocks):
    families=defaultdict(list)
    for (family,_),score in blocks.items():families[family].append(score)
    rng=random.Random(8675309)
    values=sorted(sum(sum(rng.choices(v,k=len(v))) for v in families.values())/len(blocks) for _ in range(10000))
    return [values[249],values[9749]]


def analyze(root):
    plan=json.loads((root/'plan.json').read_text());results={};blocks={};reference=None
    for rules in plan['rules']:
        results[str(rules)]={}
        for level in ('normal','hard'):
            result,means,matrix=audit(root/f'rules-{rules:02d}-{level}',plan,rules,level)
            if reference is None:reference=matrix
            assert matrix==reference,'all rule and difficulty conditions must share setups and seeds'
            results[str(rules)][level]=result;blocks[(rules,level)]=means
    contrasts={}
    for rules in plan['rules']:
        diff={key:blocks[(rules,'hard')][key]-value for key,value in blocks[(rules,'normal')].items()}
        contrasts[f'{rules}:hard-minus-normal']={'difference':sum(diff.values())/len(diff),'block_bootstrap_95':interval(diff)}
        if rules and 0 in plan['rules']:
            for level in ('normal','hard'):
                diff={key:value-blocks[(0,level)][key] for key,value in blocks[(rules,level)].items()}
                contrasts[f'{rules}:{level}-minus-classic']={'difference':sum(diff.values())/len(diff),'block_bootstrap_95':interval(diff)}
    return {'schema':1,'plan_sha256':digest(root/'plan.json'),'conditions':results,'contrasts':contrasts,
            'games':sum(r['games'] for v in results.values() for r in v.values()),
            'confidence_method':'10000 bootstrap samples within each family; complete blocks bundle all five opponents and both sides; seed 8675309',
            'interpretation':'Intervals describe each predeclared comparison separately, without multiplicity correction. Variant-versus-Classic contrasts measure the retained production configurations, including Classic-only student scoring; they do not isolate a rule effect from all policy/opponent interactions.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=analyze(args.root)
    with args.out.open('x') as output:output.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'games':result['games'],'conditions':len(result['conditions'])},indent=2))
