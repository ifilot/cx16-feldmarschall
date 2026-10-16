"""Independent stored-row accounting; no games, replay, or evidence mutations."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import zlib


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def review(directory):
    directory=Path(directory);plan=json.loads((directory/'plan.json').read_text())
    result=json.loads((directory/'result.json').read_text());audit=json.loads((directory/'audit.json').read_text())
    frozen=json.loads((directory/'frozen-policies.json').read_text())
    registration=json.loads((directory/'registration.json').read_text())
    assert sha(directory/'plan.json')==registration['plan_sha256']
    manifest=json.loads((directory/'manifest.json').read_text())
    actual_files={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name!='manifest.json'}
    assert set(manifest)==actual_files,'Manifest must cover the complete cycle directory'
    for name,value in manifest.items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert sha(directory/name)==value,name
    games={};counts={};artifact_counts={}
    for identity in plan['policies']:
        path=directory/(identity+'.fmtour')
        connection=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
        connection.row_factory=sqlite3.Row
        try:
            metadata={row['key']:json.loads(row['value']) for row in connection.execute('SELECT * FROM metadata')}
            assert metadata['status']=='complete' and metadata['rules']=='classic'
            assert metadata['seed']==plan['seed'] and metadata['rounds']==plan['rounds']
            assert metadata['families']==plan['families'] and metadata['max_plies']==plan['max_plies']
            assert metadata['setup_mode']==plan.get('setup_mode','referee')
            assert [p['policy'] for p in metadata['participants']]==[frozen[identity],frozen[plan['opponent']]]
            artifacts={}
            for row in connection.execute('SELECT sha256,data FROM artifacts'):
                raw=zlib.decompress(row['data']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
                artifacts[row['sha256']]=raw
            for participant in metadata['participants']:
                assert participant['policy']['source_sha256'] in artifacts
                assert all(value in artifacts for value in participant['runtime_sha256'].values())
            artifact_counts[identity]=len(artifacts)
            rows=[dict(row) for row in connection.execute('SELECT id,pair_id,family,red,blue,seed,red_setup,blue_setup,result,reason FROM games ORDER BY id')]
        finally:connection.close()
        assert len(rows)==metadata['planned_games']==2*plan['rounds']*len(plan['families'])
        if plan.get('dataset'):
            pin=metadata['setup_dataset'];role=pin.get('role','referee-v1')
            assert role==plan['dataset'].get('role','referee-v1')
            assert pin['manifest_sha256']==registration['dataset_manifest_sha256']
            bundle_manifest=json.loads(artifacts[pin['manifest_sha256']])
            split=pin['split'];assert split==plan['dataset']['split']
            assert pin['offset']==plan['dataset'].get('offset',0)
            specification=bundle_manifest['splits'][split]
            assert specification['families']==metadata['families']
            corpus=json.loads(artifacts[pin['files'][split+'.json']])['records']
            count=specification['pairs_per_family'];offset=pin['offset'];rounds=metadata['rounds']
            selected=[r for f in range(len(specification['families']))
                      for r in corpus[f*count+offset:f*count+offset+rounds]]
            assert pin['record_ids']==[r['id']for r in selected]
            random_stream=random.Random(metadata['seed'])
            seeds=[random_stream.randrange(1,60000)for _ in selected]
            reflect=lambda setup:''.join(setup[i:i+10][::-1] for i in range(0,40,10))
            if role=='opponent-only-v1':
                assert metadata['setup_mode']=='policy-owned-rotated-v1'
                assert pin['selection_source_sha256'] in artifacts
                own_records=json.loads(artifacts[metadata['setup_records_sha256']])['records']
                assert len(own_records)==len(selected)
                assert all(record['opponent_setup']==selected[record['pair_id']-1]['army_b'] for record in own_records)
            else:assert role=='referee-v1' and metadata['setup_mode']=='referee'
            for row in rows:
                assert row['pair_id']==(row['id']+1)//2
                record=selected[row['pair_id']-1]
                assert row['family']==record['family'] and row['seed']==seeds[row['pair_id']-1]
                expected_names=[identity,plan['opponent']] if row['id']%2 else [plan['opponent'],identity]
                assert [row['red'],row['blue']]==expected_names
                if role=='referee-v1':
                    assert (row['red_setup'],row['blue_setup'])==(record['army_a'],record['army_b'])
                else:
                    expected=record['army_b'] if row['red']==identity else reflect(record['army_b'])
                    assert (row['blue_setup'] if row['red']==identity else row['red_setup'])==expected
        tally=Counter()
        for row in rows:
            assert (row['red']==identity)!=(row['blue']==identity)
            side='red' if row['red']==identity else 'blue'
            if row['result']=='error':point=None;tally['errors']+=1
            elif row['result']=='draw':point=.5;tally['draws']+=1
            elif row['result'] in ('red','blue'):
                point=float(row['result']==side);tally['wins' if point else 'losses']+=1
            else:raise ValueError('Unknown stored result')
            row['candidate_score']=point;row['candidate_side']=side
        by_pair=defaultdict(list)
        for row in rows:by_pair[row['pair_id']].append(row)
        reflected=lambda setup:''.join(setup[i:i+10][::-1] for i in range(0,40,10))
        for pair in by_pair.values():
            assert len(pair)==2 and {g['candidate_side'] for g in pair}=={'red','blue'}
            x,y=pair
            assert x['family']==y['family'] and x['seed']==y['seed']
            mode=metadata['setup_mode']
            if mode=='referee':
                assert x['red_setup']==y['red_setup'] and x['blue_setup']==y['blue_setup']
            else:
                transform=reflected if mode=='policy-owned-rotated-v1' else lambda s:s
                assert x['red_setup']==transform(y['blue_setup']) and x['blue_setup']==transform(y['red_setup'])
        actual={k:tally[k] for k in ('wins','draws','losses','errors')}
        assert actual=={k:result['standings'][identity][k] for k in actual}
        scored=tally['wins']+tally['draws']+tally['losses']
        actual['score']=(tally['wins']+.5*tally['draws'])/scored if scored else None
        assert actual['score']==result['standings'][identity]['score']
        report=json.loads(path.with_suffix('.report.json').read_text())
        assert report['tournament_sha256']==sha(path)
        assert report['verification']['python_replayed']==report['verification']['native_replayed_all_states']==len(rows)
        assert path.with_suffix('.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        counts[identity]=actual;games[identity]=rows
    contrasts={}
    for candidate,baseline in plan['contrasts']:
        a,b=games[candidate],games[baseline];assert len(a)==len(b)
        pairs=defaultdict(list);different_own_armies=0
        for x,y in zip(a,b):
            for key in ('id','pair_id','family','seed'):assert x[key]==y[key],key
            assert (x['red']==candidate)==(y['red']==baseline)
            own='red' if x['red']==candidate else 'blue';enemy='blue' if own=='red' else 'red'
            assert x[enemy]==y[enemy]==plan['opponent']
            assert x[enemy+'_setup']==y[enemy+'_setup'],'Opponent army must match across arms'
            if plan.get('setup_mode','referee')=='referee':
                assert x[own+'_setup']==y[own+'_setup'],'Own referee army must match across arms'
            else:different_own_armies+=x[own+'_setup']!=y[own+'_setup']
            pairs[x['pair_id']].append((x['candidate_score'],y['candidate_score']))
        direction=Counter();complete=[];bounds=[]
        for rows in pairs.values():
            assert len(rows)==2
            lo=sum((0 if x is None else x)-(1 if y is None else y) for x,y in rows)/2
            hi=sum((1 if x is None else x)-(0 if y is None else y) for x,y in rows)/2
            bounds.append((lo,hi))
            if any(x is None or y is None for x,y in rows):direction['error_pairs']+=1;continue
            difference=sum(x-y for x,y in rows)/2;complete.append(difference)
            direction['positive' if difference>0 else 'negative' if difference<0 else 'tied']+=1
        name=candidate+' minus '+baseline
        mean=sum(complete)/len(complete) if complete else None
        stored=result['comparisons'][name]
        assert mean==stored['metrics']['score']['mean'] and len(complete)==stored['complete_pairs']
        interval=[sum(row[n] for row in bounds)/len(bounds) for n in (0,1)]
        assert interval==result['error_sensitivity'][name]['paired_cohort_effect_bounds']
        contrasts[name]=dict(planned_pairs=len(pairs),complete_pairs=len(complete),paired_effect=mean,
                            directions=dict(direction),finite_missing_score_bounds=interval,
                            games_with_intentionally_different_own_armies=different_own_armies)
    attempts=sum(len(rows) for rows in games.values());errors=sum(r['errors'] for r in counts.values())
    assert attempts==result['attempts']==result['verified_games']==audit['attempts']
    assert errors==result['errors']==audit['errors_preserved_unscored']
    return dict(passed=True,cycle=plan['cycle'],scope='Independent read-only SQLite row accounting and artifact hashes; checks retained full-replay receipts but does not rerun replay.',
                manifest_files=len(manifest),attempts=attempts,errors_preserved_unscored=errors,
                artifacts_verified=artifact_counts,standings=counts,contrasts=contrasts,
                corpus_schedule_independently_checked=bool(plan.get('dataset')),
                source_manifest_sha256=sha(directory/'manifest.json'),auditor_sha256=sha(__file__))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=review(args.directory);data=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(data)
    else:print(data,end='')
