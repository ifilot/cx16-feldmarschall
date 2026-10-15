"""Reproduce every policy-owned army from the runtime embedded in a .fmtour.

No registry builds or working-tree policy files are used. Only the first
participant's frozen runtime is extracted. Each setup process receives the
recorded, strictly whitelisted setup-selection protocol and no opponent army.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import zlib

from feldmarschall import valid_setup
from tournament_store import Tournament, verify


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact_payloads(tournament):
    artifacts = {}
    for row in tournament.db.execute('SELECT sha256,name,data FROM artifacts'):
        data = zlib.decompress(row['data'])
        if sha(data) != row['sha256']:
            raise ValueError('Artifact hash mismatch: '+str(row['name']))
        artifacts[row['sha256']] = dict(name=row['name'], data=data)
    return artifacts


def runtime_path(directory, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or not relative.parts:
        raise ValueError('Unsafe runtime artifact path: '+name)
    target = directory.joinpath(*relative.parts)
    if not target.resolve().is_relative_to(directory.resolve()):
        raise ValueError('Unsafe runtime artifact path: '+name)
    return target


def audit(path, repeats=2, timeout=15):
    """Audit all setup records; fail exact comparisons on repeatable streams.

    Repeated setup choices must always match the recorded army. For stdout and
    stderr, exact stored-transcript comparison is mandatory when the replayed
    stream repeats. Variable streams are reported explicitly as unaudited for
    exact transcript reproduction; their setup lines still must match.
    """
    path = Path(path)
    if repeats < 2 or timeout <= 0:
        raise ValueError('At least two repeats and a positive timeout required')
    summary = verify(path)
    with Tournament(path) as tournament:
        metadata = tournament.metadata()
        if metadata.get('setup_mode') != 'policy-owned':
            raise ValueError('Expected policy-owned setup mode')
        if metadata['status'] != 'complete':
            raise ValueError('Setup audit requires a complete tournament')
        artifacts = artifact_payloads(tournament)
    participant = metadata['participants'][0]
    policy = participant['policy']
    owner = policy['id']
    if metadata.get('setup_owner') != owner:
        raise ValueError('First policy must own the setup selection')
    if policy.get('driver') == 'msdos1990' or '--diagnostic-truth' in policy.get('driver_args', []):
        raise ValueError('Setup owner must not receive hidden opponent information')
    source_hash = policy['source_sha256']
    if source_hash not in artifacts:
        raise ValueError('Missing frozen setup policy source')
    source_records = metadata.get('setup_source_sha256')
    required_sources = {'tournament.py', 'arena.py', 'feldmarschall.py'}
    if not isinstance(source_records, dict) or not required_sources <= set(source_records):
        raise ValueError('Missing setup selection source hashes')
    for name, digest in source_records.items():
        if digest not in artifacts:
            raise ValueError('Missing setup selection source artifact: '+name)
    document_hash = metadata['setup_records_sha256']
    document = json.loads(artifacts[document_hash]['data'])
    rows = []
    with tempfile.TemporaryDirectory(prefix='policy-setup-replay-', dir='/tmp') as temp:
        directory = Path(temp)/'owner'
        directory.mkdir()
        for name, digest in participant['runtime_sha256'].items():
            if digest not in artifacts:
                raise ValueError('Missing frozen runtime: '+name)
            target = runtime_path(directory, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(artifacts[digest]['data'])
            target.chmod(0o755)
        engine_name = ('engine' if 'engine' in participant['runtime_sha256'] else
                       'engine.exe' if 'engine.exe' in participant['runtime_sha256'] else None)
        if engine_name is None:
            raise ValueError('Frozen setup runtime has no engine entrypoint')
        arguments = [str(directory/engine_name), '--difficulty', policy['difficulty']]
        for record in document['records']:
            expected = ['feldmarschall', 'new red', 'rules 0', 'difficulty '+policy['difficulty'],
                        'seed '+str(record['setup_seed']), 'setup', 'quit']
            if record.get('protocol') != expected:
                raise ValueError('Setup selection protocol is missing or contains extra input')
            if any(not isinstance(record.get(stream), str) for stream in ('stdout', 'stderr')):
                raise ValueError('Missing exact setup-selection transcripts')
            runs = []
            for _ in range(repeats):
                completed = subprocess.run(arguments, input='\n'.join(expected)+'\n',
                                           capture_output=True, text=True, check=True,
                                           cwd=directory, timeout=timeout)
                setups = [line[6:].strip() for line in completed.stdout.splitlines()
                          if line.startswith('setup ')]
                if (setups != [record['owner_setup']] or not valid_setup(record['owner_setup'])
                        or any(line.startswith('error') for line in completed.stdout.splitlines())):
                    raise ValueError('Frozen policy setup replay mismatch in pair '+str(record['pair_id']))
                runs.append(dict(stdout=completed.stdout, stderr=completed.stderr))
            streams = {}
            for stream in ('stdout', 'stderr'):
                repeatable = all(run[stream] == runs[0][stream] for run in runs)
                equal = runs[0][stream] == record[stream] if repeatable else None
                if repeatable and not equal:
                    raise ValueError('Repeatable '+stream+' differs from recorded setup transcript in pair '
                                     +str(record['pair_id']))
                streams[stream] = dict(repeatable=repeatable, exact_recorded_match=equal,
                                       recorded_sha256=sha(record[stream].encode()),
                                       replay_sha256=[sha(run[stream].encode()) for run in runs])
            rows.append(dict(pair_id=record['pair_id'], family=record['family'],
                             setup_seed=record['setup_seed'], owner_setup=record['owner_setup'],
                             setup_matches=True, protocol_sha256=sha(('\n'.join(expected)+'\n').encode()),
                             streams=streams))
    return dict(passed=True, kind='frozen-policy-owned-setup-replay-audit',
                tournament=str(path), tournament_sha256=sha(path.read_bytes()),
                owner=owner, records=len(rows), expected_records=metadata['planned_games']//2,
                records_audited=rows, repetitions=repeats, verified_games=summary['games'],
                policy_source_sha256=source_hash, runtime_sha256=participant['runtime_sha256'],
                setup_source_sha256=source_records, setup_records_sha256=document_hash,
                all_setup_sources_present=True, no_opponent_input=True,
                all_streams_repeatable=all(r['streams'][s]['repeatable'] for r in rows for s in ('stdout', 'stderr')),
                audit_source_sha256=sha(Path(__file__).read_bytes()),
                limitation='Repeatability is observed over the specified repeats; variable streams do not receive an exact transcript claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tournament', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--repeats', type=int, default=2)
    args = parser.parse_args()
    result = json.dumps(audit(args.tournament, repeats=args.repeats), indent=2)+'\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result)
    else:
        print(result, end='')
