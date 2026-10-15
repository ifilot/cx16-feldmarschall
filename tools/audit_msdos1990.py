"""Verify the original-code opponent and its retained complete/failed evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import zipfile

from ai_registry import ROOT,get_policy
from tournament_store import Tournament,verify

BASE=ROOT/'docs/msdos-1990-framework-2026-10-15'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canonical(game):
    return {k:game[k] for k in ('id','seed','pair_id','family','red_setup','blue_setup','moves','result','reason','plies')}

def comparable_summary(actual,expected):
    # Older schema-1 reports precede explicit scored_games/errors keys.
    return all(actual[k]==v for k,v in expected.items())

def audit():
    source_manifest=json.loads((BASE/'framework-source.json').read_text())
    assert sha(BASE/'framework-source.zip')==source_manifest['sha256']
    with zipfile.ZipFile(BASE/'framework-source.zip') as source_zip:
        for name,expected in source_manifest['files'].items():
            assert hashlib.sha256(source_zip.read(name)).hexdigest()==expected
            assert sha(ROOT/name)==expected,name
    manifest=json.loads((ROOT/'ai/msdos1990/manifest.json').read_text())
    for name,info in manifest['images'].items():
        assert sha(ROOT/'ai/msdos1990'/name)==info['sha256']
    policies=[]
    for identity in ('msdos-1990-v1-normal','msdos-1990-v2-normal'):
        policy=get_policy(identity);assert policy['driver']=='msdos1990' and policy['requires_opponent_setup']
        assert policy['emulator_version']=='2.1.4' and policy['driver_args']==['--level','3']
        assert sha(ROOT/policy['archive'])==policy['source_sha256']
        with zipfile.ZipFile(ROOT/policy['archive']) as bundle:
            for name in policy['asset_files']:assert bundle.read(name)==(ROOT/name).read_bytes()
            if identity.endswith('v2-normal'):assert bundle.read('tools/msdos1990.py')==(ROOT/'tools/msdos1990.py').read_bytes()
        policies.append(policy)
    archive_info=json.loads((BASE/'benchmark-archive.json').read_text())
    archive=BASE/archive_info['archive'];assert sha(archive)==archive_info['sha256']
    first=None;total_games=total_plies=0;seen=set();retained=[]
    with tempfile.TemporaryDirectory(prefix='msdos-audit-') as folder,tarfile.open(archive,'r:xz') as bundle:
        for member in bundle:
            assert member.isfile() and member.name in archive_info['files']
            seen.add(member.name);path=Path(folder)/'run.fmtour'
            with path.open('wb') as output:shutil.copyfileobj(bundle.extractfile(member),output)
            assert sha(path)==archive_info['files'][member.name]
            summary=verify(path)
            with Tournament(path) as tournament:
                games=[tournament.game(g['id']) for g in tournament.games()]
                meta=tournament.metadata()
            total_games+=len(games);total_plies+=sum(g['plies'] for g in games)
            if member.name=='failed-stress-v2.fmtour':
                assert meta['status']=='failed' and 'Match 107' in meta['error'] and len(games)==107
            else:
                stage,label=member.name.split('/');label=label.removesuffix('.fmtour')
                report=json.loads((BASE/stage/'report.json').read_text());measurement=report['measurements'][label]
                assert measurement['sha256']==sha(path) and measurement['games']==14
                assert measurement['execution_seconds']==meta['execution_seconds']
                assert comparable_summary(summary,measurement['summary'])
                rows=[canonical(g) for g in games]
                if first is None:first=rows
                else:assert first==rows,(stage,label)
                assert report['all_complete_traces_identical']
            retained.append(dict(path=member.name,games=len(games),plies=sum(g['plies'] for g in games),status=meta['status']))
    assert seen==set(archive_info['files']) and len(seen)==9
    primary=BASE/'reference.fmtour';summary=verify(primary)
    report=json.loads((BASE/'stress-report.json').read_text())
    assert sha(primary)==report['sha256'] and summary==report['summary']
    assert summary['games']==140 and summary['scored_games']==138 and summary['errors']==2
    with Tournament(primary) as tournament:
        metadata=tournament.metadata();games=[tournament.game(g['id']) for g in tournament.games()]
        assert metadata['schema']==2 and metadata['reuse_engine_processes']
        assert metadata['execution_seconds']==report['execution_seconds']
        assert metadata['seed']==1912001 and metadata['rounds']==10
        assert metadata['parallel_execution']['threads']==4
        assert sum(g['plies'] for g in games)==report['plies']==22691
        errors=[g for g in games if g['result']=='error']
        assert [(g['id'],g['plies']) for g in errors]==[(107,177),(112,123)]
        for g in errors:assert 'Unexpected original interrupt 3f' in g['reason']
        assert sum(v['wins']+v['losses']+v['draws'] for v in summary['standings'].values())==276
        for participant in metadata['participants']:
            p=participant['policy'];assert p==get_policy(p['id'])
    total_games+=len(games);total_plies+=report['plies']
    proof=json.loads((BASE/'checks/reference-error.json').read_text())
    assert sha(BASE/'checks/reference-error.zip')==proof['archive_sha256']
    with zipfile.ZipFile(BASE/'checks/reference-error.zip') as z:
        assert z.read('original-exit-body.bin').hex()==proof['original_exit_body_hex']
        repro=json.loads(z.read('repro107.json'));assert repro['ply']==176 and len(repro['history'])==177
    for log,count in [('core-tests.log',5),('error-isolation-tests.log',3),('tournament-tests.log',9),('desktop-tests.log',7)]:
        text=(BASE/'checks'/log).read_text();assert f'Ran {count} tests' in text and '\nOK' in text and 'FAILED (' not in text
    production=(BASE/'checks/production.log').read_text()
    assert '15163 hidden-permutation decisions' in production and '3836 Silent Defense' in production
    for name in ('review-match.png','review-error.png'):assert (BASE/name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    # Production's frozen learned policy remains exactly the production source.
    production_policy=get_policy('student-guard-v1-normal')
    with zipfile.ZipFile(ROOT/production_policy['archive']) as z:
        assert z.read('src/core/ai_student_model_production.h')==(ROOT/'src/core/ai_student_model_production.h').read_bytes()
    result=dict(status='COMPLETE',policies=policies,original_inputs=manifest,
        preserved_tournaments=retained,verified_execution_records=total_games,verified_legal_plies=total_plies,
        benchmark_distinct_games=14,benchmark_repeated_executions=8,
        fresh_reference_attempts=140,fresh_reference_scored=138,fresh_reference_unscored=2,
        throughput=dict(plies_per_second=report['execution_plies_per_second'],execution_seconds=report['execution_seconds'],end_to_end_seconds=report['seconds']),
        original_ai_instructions_unpatched=True,production_model_unchanged=True,framework_source=source_manifest,
        limitations=['Original-AI coprocessor with a host Classic referee, not full original DOS UI equivalence.','Original hidden-rank access preserved.','Two original-call fatal-exit paths reached under the bridge; unscored and not attributed conclusively to an interactive-game bug.','Hardware/workload-specific performance; repeated benchmark games are not independent strength observations.'],
        evidence_sha256={str(p.relative_to(BASE)):sha(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in ('audit.json','audit.log')},
        audit_source_sha256=sha(Path(__file__)))
    (BASE/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence_sha256','policies','original_inputs','preserved_tournaments')},indent=2))

if __name__=='__main__':audit()
