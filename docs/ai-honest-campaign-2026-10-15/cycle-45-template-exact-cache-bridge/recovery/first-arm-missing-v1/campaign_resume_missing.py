"""Append only missing games from a frozen policy-owned OpenMP tournament.

No runtime is built, setup generated, seed redrawn, or existing game replaced.
The caller must establish that the previous single writer is terminal first.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex
import sqlite3
import tempfile
import time
import zlib

from ai_registry import receives_opponent_setup
from tournament import openmp_results
from tournament_store import Tournament, mirror_setup
from feldmarschall import valid_setup


def digest(data):
    return hashlib.sha256(data).hexdigest()


def schedule(metadata, document):
    """Reconstruct physical armies and stable one-based IDs from frozen records."""
    if metadata['backend'] != 'openmp' or metadata['rules'] != 'classic':
        raise ValueError('Classic OpenMP evidence required')
    mode = metadata.get('setup_mode')
    if mode not in ('policy-owned', 'policy-owned-rotated-v1'):
        raise ValueError('Frozen policy-owned setup records required')
    first, second = [r['policy']['id'] for r in metadata['participants']]
    if receives_opponent_setup(metadata['participants'][0]['policy']):
        raise ValueError('First policy must not receive opponent setup')
    if document.get('schema') != 'classic-policy-owned-setups-v1' or document.get('owner') != first or document.get('opponent') != second:
        raise ValueError('Setup record ownership mismatch')
    records = document['records']
    expected_pairs = metadata['rounds'] * len(metadata['families'])
    if len(records) != expected_pairs or metadata['planned_games'] != 2*expected_pairs:
        raise ValueError('Incomplete frozen setup schedule')
    jobs = []
    for index, record in enumerate(records):
        pair_id = index+1
        family = metadata['families'][index//metadata['rounds']]
        if record['pair_id'] != pair_id or record['family'] != family:
            raise ValueError('Setup record index/family mismatch')
        own, other = record['owner_setup'], record['opponent_setup']
        seed = record['move_seed']
        if not valid_setup(own) or not valid_setup(other) or type(seed) is not int or not 1 <= seed < 60000:
            raise ValueError('Invalid frozen army or seed')
        if record['setup_seed'] != (seed*109+0x5e7a)%65535+1:
            raise ValueError('Setup seed binding mismatch')
        for offset, names in enumerate(((first,second),(second,first))):
            setups = (own,other) if offset==0 else (other,own)
            if offset and mode=='policy-owned-rotated-v1':
                setups = tuple(mirror_setup(army) for army in setups)
            jobs.append(dict(id=2*index+offset+1,pair_id=pair_id,family=family,
                             names=names,setups=setups,seed=seed))
    return jobs


def raw_games(db):
    return {row[0]:tuple(row) for row in db.execute('SELECT * FROM games ORDER BY id')}


def raw_hash(rows):
    return digest(json.dumps([[v.hex() if isinstance(v,bytes) else v for v in row]
                              for _,row in sorted(rows.items())],separators=(',',':')).encode())


def resume(path, recovery):
    path, recovery = Path(path).resolve(), Path(recovery).resolve()
    recovery.mkdir(parents=True,exist_ok=False)
    started_utc = datetime.now(timezone.utc).isoformat()
    with Tournament(path) as read:
        metadata = read.metadata()
        if metadata['status']=='complete':
            raise ValueError('Tournament already complete')
        original = raw_games(read.db)
        before_hash = digest(path.read_bytes())
        snapshot = recovery/'original-partial.snapshot'
        with sqlite3.connect(snapshot) as backup:
            read.db.backup(backup)
        def artifact(expected):
            row = read.db.execute('SELECT data FROM artifacts WHERE sha256=?',(expected,)).fetchone()
            if row is None:
                raise ValueError('Missing frozen artifact')
            data = zlib.decompress(row[0])
            if digest(data)!=expected:
                raise ValueError('Corrupt frozen artifact')
            return data
        document = json.loads(artifact(metadata['setup_records_sha256']))
        jobs = schedule(metadata,document)
        for game_id,row in original.items():
            if not 1 <= game_id <= len(jobs):
                raise ValueError('Existing game outside frozen schedule')
            expected = jobs[game_id-1]
            # schema: id,pair_id,family,red,blue,seed,red_setup,blue_setup,...
            if row[:8] != (game_id,expected['pair_id'],expected['family'],*expected['names'],expected['seed'],*expected['setups']):
                raise ValueError('Existing game disagrees with frozen schedule')
        missing = [job for job in jobs if job['id'] not in original]
        if not missing:
            raise ValueError('No missing games')
        receipt = dict(started_utc=started_utc,tournament=str(path),original_games=len(original),
            original_game_ids=sorted(original),original_raw_games_sha256=raw_hash(original),
            original_partial_sha256=before_hash,snapshot_sha256=digest(snapshot.read_bytes()),
            missing_game_ids=[j['id'] for j in missing],planned_games=len(jobs),games_rerun=0,
            original_metadata=metadata,previous_writer_required_terminal=True,
            setup_records_sha256=metadata['setup_records_sha256'],runtime_files={})
        with tempfile.TemporaryDirectory(prefix='fmtour-recovery-') as temporary:
            working = Path(temporary)
            argv, privileged = {}, {}
            for participant in metadata['participants']:
                policy = participant['policy']
                identity = policy['id']
                folder = working/identity
                folder.mkdir()
                for name, expected in participant['runtime_sha256'].items():
                    relative = PurePosixPath(name)
                    if relative.is_absolute() or '..' in relative.parts:
                        raise ValueError('Unsafe runtime artifact path')
                    target = folder/name
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(artifact(expected))
                    receipt['runtime_files'][identity+'/'+name]=expected
                engine = folder/'engine'
                if digest(engine.read_bytes()) != participant['executable_sha256']:
                    raise ValueError('Engine identity mismatch')
                engine.chmod(0o755)
                argv[identity]=[str(engine),'--difficulty',policy['difficulty']]
                privileged[identity]=receives_opponent_setup(policy)
            worker=working/'frozen-worker'
            worker.write_bytes(artifact(metadata['worker_sha256']))
            worker.chmod(0o755)
            if digest(worker.read_bytes()) != metadata['worker_build']['executable_sha256']:
                raise ValueError('Worker receipt mismatch')
            source=artifact(metadata['worker_source_sha256'])
            if digest(source)!=metadata['worker_build']['source_archive_sha256']:
                raise ValueError('Worker source receipt mismatch')
            receipt['worker_sha256']=metadata['worker_sha256']
            receipt['worker_source_sha256']=metadata['worker_source_sha256']
            (recovery/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
            queue=[(j['names'],tuple(shlex.join(argv[n]) for n in j['names']),j['setups'],
                    j['seed'],metadata['max_plies'],True) for j in missing]
            # Explicit read/write reopen only after all schedule/artifact checks.
            with Tournament(path) as tournament:
                tournament.db.close()
                tournament.db=sqlite3.connect(path)
                tournament.db.row_factory=sqlite3.Row
                if raw_games(tournament.db)!=original:
                    raise ValueError('Another writer changed the partial tournament')
                execution_started=time.perf_counter()
                seen=set()
                try:
                    for index,game in openmp_results(queue,worker,working,metadata['requested_workers'],argv,
                            privileged,metadata.get('reuse_engine_processes',False)):
                        if index is None:
                            tournament.set_metadata({'recovery_parallel_execution':game})
                            continue
                        if type(index) is not int or index in seen or not 0<=index<len(missing):
                            raise ValueError('Invalid recovery worker index')
                        seen.add(index)
                        job=missing[index]
                        if (game['red'],game['blue'])!=job['names'] or game['seed']!=job['seed']:
                            raise ValueError('Recovery result identity mismatch')
                        tournament.add_game(game,job['pair_id'],job['family'],job['setups'],game_id=job['id'])
                        print(json.dumps(dict(completed=len(seen),missing_total=len(missing),game_id=job['id'])),flush=True)
                    if len(seen)!=len(missing):
                        raise ValueError('Incomplete recovery worker output')
                    final=raw_games(tournament.db)
                    if any(final[key]!=row for key,row in original.items()) or set(final)!=set(range(1,len(jobs)+1)):
                        raise ValueError('Original games changed or final IDs incomplete')
                    elapsed=time.perf_counter()-execution_started
                    receipt.update(completed=True,finished_utc=datetime.now(timezone.utc).isoformat(),
                        appended_games=len(seen),recovery_execution_seconds=elapsed,original_games_unchanged=True,
                        final_raw_games_sha256=raw_hash(final),execution_seconds_scope='Recovery of missing games only; original interrupted duration unavailable. Not full-arm execution time.')
                    tournament.set_metadata(dict(status='complete',finished_utc=receipt['finished_utc'],
                        execution_seconds=elapsed,execution_seconds_scope=receipt['execution_seconds_scope'],
                        recovery=dict(original_game_ids=sorted(original),appended_games=len(seen),games_rerun=0,
                                      receipt=str((recovery/'receipt.json').relative_to(path.parent)))))
                finally:
                    receipt['saved_game_count_after_attempt']=tournament.db.execute('SELECT COUNT(*) FROM games').fetchone()[0]
                    (recovery/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tournament',type=Path)
    parser.add_argument('--recovery',type=Path,required=True)
    args=parser.parse_args()
    resume(args.tournament,args.recovery)
