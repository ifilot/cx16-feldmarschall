"""Immutable, source-backed Classic AI catalog. No third-party dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import zipfile

from feldmarschall import ROOT

CATALOG = ROOT / 'ai/registry.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def catalog():
    return json.loads(CATALOG.read_text())['policies']


def get_policy(identity):
    for policy in catalog():
        if policy['id'] == identity:
            return policy
    raise ValueError(f'Unknown AI: {identity}')


def register(spec):
    """Freeze all build inputs; publish a new ID only after its archive exists."""
    identity = spec['id']
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-v[0-9]+(?:-(?:easy|normal|hard))?', identity):
        raise ValueError('ID must be descriptive and versioned, e.g. missions-v2-normal')
    if any(p['id'] == identity for p in catalog()):
        raise ValueError(f'ID already exists: {identity}; create a new version')
    if spec.get('difficulty', 'normal') not in ('easy', 'normal', 'hard'):
        raise ValueError('Invalid difficulty')
    files = set()
    for directory in ('src/core', 'src/native', 'tests/baselines'):
        files.update(p for p in (ROOT / directory).iterdir() if p.suffix in ('.c', '.h'))
    files.update(p for p in (ROOT / 'tools').glob('*.py'))
    files.update(ROOT / p for p in spec['sources'])
    files.update(ROOT / p for p in spec.get('teacher_sources', []))
    for directory in spec.get('include_dirs', []):
        files.update((ROOT / directory).glob('*.h'))
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files):
            relative = path.resolve().relative_to(ROOT.resolve())
            info = zipfile.ZipInfo(relative.as_posix(), (2026, 10, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    data = buffer.getvalue()
    sha = digest(data)
    destination = ROOT / 'ai/sources' / (sha + '.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        destination.write_bytes(data)
    policy = dict(spec, archive=str(destination.relative_to(ROOT)), source_sha256=sha)
    document = json.loads(CATALOG.read_text())
    document['policies'].append(policy)
    CATALOG.write_text(json.dumps(document, indent=2) + '\n')
    return policy


def build_policy(identity):
    policy = get_policy(identity)
    archive = ROOT / policy['archive']
    if digest(archive.read_bytes()) != policy['source_sha256']:
        raise ValueError(f'Source archive failed integrity check: {identity}')
    recipe_sha = digest(json.dumps(policy, sort_keys=True).encode())
    directory = ROOT / 'build/ai-catalog' / identity
    executable = directory / ('engine.exe' if os.name == 'nt' else 'engine')
    receipt = directory / 'build.json'
    if executable.exists() and receipt.exists():
        previous = json.loads(receipt.read_text())
        if (previous['recipe_sha256'] == recipe_sha and
                all((directory / path).is_file() and digest((directory / path).read_bytes()) == sha
                    for path, sha in previous['runtime_sha256'].items())):
            return executable, previous
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sources-', dir=directory) as temp:
        source = Path(temp)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.namelist():
                target = (source / member).resolve()
                if not target.is_relative_to(source.resolve()):
                    raise ValueError('Unsafe source archive path')
            bundle.extractall(source)
        command = [*shlex.split(os.environ.get('HOSTCC', 'gcc')), '-O2', '-std=c99',
                   '-Wno-unknown-pragmas', '-Wno-format-overflow',
                   f'-DFELDMARSCHALL_AI_ID="{identity}"', '-Isrc/core']
        command += ['-I' + path for path in policy.get('include_dirs', [])]
        command += ['-D' + define for define in policy.get('defines', [])]
        command += ['-o', str(executable), *policy['sources']]
        subprocess.run(command, cwd=source, check=True)
        runtime = [executable.name]
        if policy.get('driver') == 'teacher':
            observer = directory / 'observer'
            executable.replace(observer)
            teacher = directory / 'teacher'
            teacher_command = [*shlex.split(os.environ.get('HOSTCC', 'gcc')), '-O2', '-std=c99',
                               '-Wno-unknown-pragmas', '-Isrc/core', '-o', str(teacher)]
            teacher_command += ['-D' + d for d in policy['teacher_defines']]
            teacher_command += policy['teacher_sources']
            subprocess.run(teacher_command, cwd=source, check=True)
            runtime = ['engine', 'observer', 'teacher']
            for name in ('teacher_bot.py', 'train_ai_student.py', 'feldmarschall.py'):
                shutil_path = directory / name
                shutil_path.write_bytes((source / 'tools' / name).read_bytes())
                runtime.append(name)
            # The adapter locates its siblings relative to this preserved launcher.
            executable.write_text('#!/usr/bin/env python3\nimport os, pathlib, sys\n'
                'p = pathlib.Path(__file__).resolve().parent\n'
                f'if sys.argv[1:] == ["--identity"]:\n    print({identity!r})\n    raise SystemExit\n'
                'os.execv(sys.executable, [sys.executable, str(p / "teacher_bot.py"), '
                '"--observer", str(p / "observer"), "--teacher", str(p / "teacher"), '
                f'*{policy["driver_args"]!r}, *sys.argv[1:]])\n')
            executable.chmod(0o755)
    metadata = dict(policy=policy, recipe_sha256=recipe_sha,
                    executable_sha256=digest(executable.read_bytes()),
                    runtime_sha256={path: digest((directory / path).read_bytes()) for path in runtime},
                    compiler=subprocess.check_output([*shlex.split(os.environ.get('HOSTCC', 'gcc')),
                                                       '--version'], text=True).splitlines()[0])
    receipt.write_text(json.dumps(metadata, indent=2) + '\n')
    return executable, metadata


def restore_tournament(path):
    """Recover catalog entries and rebuildable sources from a portable tournament."""
    import zlib
    from tournament_store import Tournament
    additions = []
    document = json.loads(CATALOG.read_text())
    existing = {p['id']: p for p in document['policies']}
    with Tournament(path) as tournament:
        for participant in tournament.metadata()['participants']:
            policy = participant['policy']
            if policy['id'] in existing and existing[policy['id']] != policy:
                raise ValueError(f'ID conflict: {policy["id"]}; existing identity cannot be replaced')
            expected = 'ai/sources/' + policy['source_sha256'] + '.zip'
            if policy['archive'] != expected:
                raise ValueError('Unexpected source archive path')
            row = tournament.db.execute('SELECT data FROM artifacts WHERE sha256=?', (policy['source_sha256'],)).fetchone()
            if row is None:
                raise ValueError('Missing AI source archive')
            data = zlib.decompress(row['data'])
            if digest(data) != policy['source_sha256']:
                raise ValueError('AI source archive hash mismatch')
            additions.append((policy, data))
    for policy, data in additions:
        destination = ROOT / policy['archive']
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError('Conflicting source archive')
        if not destination.exists():
            destination.write_bytes(data)
        if policy['id'] not in existing:
            document['policies'].append(policy)
    CATALOG.write_text(json.dumps(document, indent=2) + '\n')
    return [p['id'] for p, _ in additions]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('list')
    actions.add_parser('build').add_argument('ids', nargs='+')
    actions.add_parser('register').add_argument('spec', type=Path)
    actions.add_parser('restore').add_argument('tournament', type=Path)
    args = parser.parse_args()
    if args.action == 'list':
        for policy in catalog():
            print(f'{policy["id"]:38s} {policy["name"]} [{policy["status"]}]')
    elif args.action == 'build':
        for identity in args.ids:
            print(build_policy(identity)[0])
    elif args.action == 'register':
        print(json.dumps(register(json.loads(args.spec.read_text())), indent=2))
    else:
        print('\n'.join(restore_tournament(args.tournament)))


if __name__ == '__main__':
    main()
