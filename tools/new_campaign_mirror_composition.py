"""Audit actual setup tickets and exact original/mirror mixture composition.

Complete frozen cohorts only. A mixture game must reproduce its selected fixed
arm's whole initial state and saved move/outcome/error prefix. No new games.
"""
import argparse
from collections import Counter,defaultdict
import hashlib,json,re,zipfile,zlib
from pathlib import Path

from tournament_store import Tournament,mirror_setup


def next_rng(state):
    state^=(state<<7)&65535;state^=state>>9;state^=(state<<8)&65535
    return state


def ticket(seed):
    state=seed&65535 or 1;state=next_rng(state)
    while state>65530:state=next_rng(state)
    return (state-1)%10


def load(path):
    with Tournament(path) as tour:
        metadata=tour.metadata()
        assert metadata['status']=='complete' and metadata['setup_mode']=='policy-owned-rotated-v1'
        assert metadata['rules']=='classic'
        row=tour.db.execute('select data from artifacts where sha256=?',(metadata['setup_records_sha256'],)).fetchone()
        data=zlib.decompress(row['data']);assert hashlib.sha256(data).hexdigest()==metadata['setup_records_sha256']
        records={row['pair_id']:row for row in json.loads(data)['records']}
        games={row['id']:tour.game(row['id']) for row in tour.games()}
        assert len(games)==metadata['planned_games']
    return metadata,records,games


def audit(directory):
    plan=json.loads((directory/'plan.json').read_text());frozen=json.loads((directory/'frozen-policies.json').read_text())
    root=directory.parents[2];baseline=plan['baseline']
    mirror='student-fortress-mirror-template-v1-normal';mixture='student-fortress-mirror-mixture-template-v1-normal'
    with zipfile.ZipFile(root/frozen[baseline]['archive']) as archive:
        text=archive.read('src/core/ai_deploy.c').decode()
    raw=next(r for r in re.findall(r'\{([\d,]+)\}',text)if len(r.split(','))==40)
    base=''.join('123456789SBF'[int(r)]for r in raw.split(','));reflected=mirror_setup(base)
    loaded={p:load(directory/(p+'.fmtour'))for p in (baseline,mirror,mixture)}
    counts=Counter();families=defaultdict(Counter);records=[]
    _,mr,mg=loaded[mixture]
    assert set(mg)==set(loaded[baseline][2])==set(loaded[mirror][2])
    for pair_id,mix_record in sorted(mr.items()):
        original=loaded[baseline][1][pair_id];mirrored=loaded[mirror][1][pair_id]
        for key in ('setup_seed','move_seed','family','opponent_setup'):
            assert mix_record[key]==original[key]==mirrored[key],(pair_id,key)
        assert original['owner_setup']==base and mirrored['owner_setup']==reflected
        choice='mirror' if ticket(mix_record['setup_seed'])>=5 else 'original'
        expected=reflected if choice=='mirror' else base
        assert mix_record['owner_setup']==expected
        counts[choice+'_pairs']+=1;families[mix_record['family']][choice+'_pairs']+=1
    for identity,game in sorted(mg.items()):
        rec=mr[game['pair_id']];choice='mirror' if ticket(rec['setup_seed'])>=5 else 'original'
        fixed_id=mirror if choice=='mirror'else baseline;fixed=loaded[fixed_id][2][identity]
        side='red' if game['red']==mixture else 'blue';opposite='blue'if side=='red'else'red'
        assert fixed[side]==fixed_id and fixed[opposite]==game[opposite]==plan['opponent']
        for key in ('id','pair_id','family','seed','red_setup','blue_setup','moves','result','reason','plies'):
            assert game[key]==fixed[key],(identity,choice,key)
        expected=rec['owner_setup'] if side=='red'else mirror_setup(rec['owner_setup'])
        assert game[side+'_setup']==expected
        counts['exact_selected_arm_games']+=1;counts['exact_selected_arm_error_prefixes']+=game['result']=='error'
        families[game['family']]['exact_selected_arm_games']+=1
        records.append(dict(game=identity,pair=game['pair_id'],side=side,orientation=choice,
            selected_fixed_policy=fixed_id,plies=game['plies'],error_prefix=game['result']=='error',
            exact_initial_state_moves_outcome_and_reason=True))
    return dict(passed=True,scope='Preregistered deployment-ticket and exact saved-trajectory composition, not a new strength estimate',
        counts=dict(counts),families={f:dict(v)for f,v in families.items()},records=records,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        sources={p:hashlib.sha256((directory/(p+'.fmtour')).read_bytes()).hexdigest()for p in loaded},
        limitations='Own-only reflection changes matchups as well as orientation. Mixture selection uses existing setup tickets, so its finite-cohort score need not equal the mean of the two fixed-arm scores.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    args=parser.parse_args();doc=audit(args.directory.resolve())
    (args.directory/'composition-audit.json').write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps({k:v for k,v in doc.items()if k!='records'}))


if __name__=='__main__':main()
