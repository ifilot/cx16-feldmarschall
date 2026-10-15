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
import shutil

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


def receives_opponent_setup(policy):
    """Only original DOS or the explicitly labelled information ablation."""
    return policy.get('driver') == 'msdos1990' or (
        policy.get('driver') == 'teacher' and
        policy.get('information_model') in ('diagnostic-full-enemy-ranks', 'diagnostic-flag-spy', 'diagnostic-flag') and
        '--diagnostic-truth' in policy.get('driver_args', []))


def register(spec):
    """Freeze all build inputs; publish a new ID only after its archive exists."""
    identity = spec['id']
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-v[0-9]+(?:-(?:easy|normal|hard))?', identity):
        raise ValueError('ID must be descriptive and versioned, e.g. missions-v2-normal')
    if any(p['id'] == identity for p in catalog()):
        raise ValueError(f'ID already exists: {identity}; create a new version')
    if spec.get('difficulty', 'normal') not in ('easy', 'normal', 'hard'):
        raise ValueError('Invalid difficulty')
    if spec.get('driver') == 'native-beliefs':
        required = {'AI_BELIEF_PRIORS', 'AI_DIAGNOSTICS', 'AI_MEMORY'}
        if not required.issubset(spec.get('defines', [])):
            raise ValueError('Native belief driver requires public-board, memory and prior protocol compile flags')
    files = set()
    for directory in ('src/core', 'src/native', 'tests/baselines'):
        files.update(p for p in (ROOT / directory).iterdir() if p.suffix in ('.c', '.h'))
    files.update(p for p in (ROOT / 'tools').glob('*.py'))
    files.update(ROOT / p for p in spec['sources'])
    files.update(ROOT / p for p in spec.get('teacher_sources', []))
    files.update(ROOT / p for p in spec.get('asset_files', []))
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
    # A catalog entry must be rebuildable before it becomes selectable. Failed
    # source snapshots may remain as evidence, but never publish a broken ID.
    build_policy(identity, policy=policy)
    document = json.loads(CATALOG.read_text())
    document['policies'].append(policy)
    CATALOG.write_text(json.dumps(document, indent=2) + '\n')
    return policy


def build_policy(identity, policy=None):
    policy = get_policy(identity) if policy is None else policy
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
        if policy.get('driver') == 'msdos1990':
            runtime = build_msdos1990(source, directory, executable, policy)
            metadata = dict(policy=policy, recipe_sha256=recipe_sha,
                            executable_sha256=digest(executable.read_bytes()),
                            runtime_sha256={path: digest((directory / path).read_bytes()) for path in runtime},
                            compiler='Original 16-bit machine code; Unicorn ' + policy['emulator_version'])
            receipt.write_text(json.dumps(metadata, indent=2) + '\n')
            return executable, metadata
        command = [*shlex.split(os.environ.get('HOSTCC', 'gcc')), '-O2', '-std=c99',
                   '-Wno-unknown-pragmas', '-Wno-format-overflow',
                   f'-DFELDMARSCHALL_AI_ID="{identity}"', '-Isrc/core']
        command += ['-I' + path for path in policy.get('include_dirs', [])]
        command += ['-D' + define for define in policy.get('defines', [])]
        command += ['-o', str(executable), *policy['sources']]
        subprocess.run(command, cwd=source, check=True)
        runtime = [executable.name]
        if policy.get('driver') == 'native-beliefs':
            runtime = build_native_beliefs(source, directory, executable, policy)
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
            for flag, name in (('--world-sampling', 'campaign_sampling.py'),
                               ('--campaign-strategy', 'campaign_strategy.py'),
                               ('--paired-confidence', 'campaign_search.py'),
                               ('--adaptive-depth', 'campaign_depth.py'),
                               ('--correction-anchor', 'campaign_anchor.py'),
                               ('--belief-sweeps', 'campaign_swap_beliefs.py'),
                               ('--root-capture-mode', 'campaign_belief_values.py')):
                if flag in policy.get('driver_args', []):
                    (directory / name).write_bytes((source / 'tools' / name).read_bytes())
                    runtime.append(name)
            if '--campaign-strategy' in policy.get('driver_args', []):
                name = 'campaign_recurrence.py'
                (directory / name).write_bytes((source / 'tools' / name).read_bytes())
                runtime.append(name)
                arguments=policy['driver_args']
                if arguments[arguments.index('--campaign-strategy')+1]=='flag-interceptor':
                    name='campaign_flag_guard.py'
                    (directory/name).write_bytes((source/'tools'/name).read_bytes())
                    runtime.append(name)
            if '--information-strategy' in policy.get('driver_args', []):
                for name in ('info_common.py', 'info_lifetime.py', 'info_objectives.py', 'info_followthrough.py'):
                    (directory / name).write_bytes((source / 'tools' / name).read_bytes())
                    runtime.append(name)
            if '--belief-model' in policy.get('driver_args', []):
                name = 'calibrated_beliefs.py'
                (directory / name).write_bytes((source / 'tools' / name).read_bytes())
                runtime.append(name)
                model_path = policy['belief_model']
                if digest((source / model_path).read_bytes()) != policy['belief_model_sha256']:
                    raise ValueError('Belief model failed integrity check')
                model_name = Path(model_path).name
                (directory / model_name).write_bytes((source / model_path).read_bytes())
                runtime.append(model_name)
            if '--joint-belief-model' in policy.get('driver_args', []):
                for name in ('campaign_joint_beliefs.py', 'calibrated_beliefs.py'):
                    (directory / name).write_bytes((source / 'tools' / name).read_bytes())
                    runtime.append(name)
                model_path = policy['joint_belief_model']
                if digest((source / model_path).read_bytes()) != policy['joint_belief_model_sha256']:
                    raise ValueError('Joint setup model failed integrity check')
                joint_name = Path(model_path).name
                (directory / joint_name).write_bytes((source / model_path).read_bytes())
                runtime.append(joint_name)
            if '--root-policy' in policy.get('driver_args', []):
                name = 'root_policy.py'
                (directory / name).write_bytes((source / 'tools' / name).read_bytes())
                runtime.append(name)
                settings_path = policy['root_policy']
                if digest((source / settings_path).read_bytes()) != policy['root_policy_sha256']:
                    raise ValueError('Root policy settings failed integrity check')
                settings_name = Path(settings_path).name
                (directory / settings_name).write_bytes((source / settings_path).read_bytes())
                runtime.append(settings_name)
            driver_arguments = repr(policy['driver_args'])
            if '--belief-model' in policy.get('driver_args', []):
                # The tournament copies runtimes into a temporary directory;
                # resolve the model beside that portable launcher, not cwd.
                driver_arguments = ('[' + ', '.join('str(p / '+repr(arg)+')' if arg == model_name else repr(arg)
                                                   for arg in policy['driver_args']) + ']')
            if '--root-policy' in policy.get('driver_args', []):
                driver_arguments = ('[' + ', '.join('str(p / '+repr(arg)+')' if arg == settings_name else repr(arg)
                                                   for arg in policy['driver_args']) + ']')
            if '--joint-belief-model' in policy.get('driver_args', []):
                driver_arguments = ('[' + ', '.join('str(p / '+repr(arg)+')' if arg == joint_name else repr(arg)
                                                   for arg in policy['driver_args']) + ']')
            # The adapter locates its siblings relative to this preserved launcher.
            executable.write_text('#!/usr/bin/env python3\nimport os, pathlib, sys\n'
                'p = pathlib.Path(__file__).resolve().parent\n'
                f'if sys.argv[1:] == ["--identity"]:\n    print({identity!r})\n    raise SystemExit\n'
                'os.execv(sys.executable, [sys.executable, str(p / "teacher_bot.py"), '
                '"--observer", str(p / "observer"), "--teacher", str(p / "teacher"), '
                f'*{driver_arguments}, *sys.argv[1:]])\n')
            executable.chmod(0o755)
    metadata = dict(policy=policy, recipe_sha256=recipe_sha,
                    executable_sha256=digest(executable.read_bytes()),
                    runtime_sha256={path: digest((directory / path).read_bytes()) for path in runtime},
                    compiler=subprocess.check_output([*shlex.split(os.environ.get('HOSTCC', 'gcc')),
                                                       '--version'], text=True).splitlines()[0])
    receipt.write_text(json.dumps(metadata, indent=2) + '\n')
    return executable, metadata


def build_native_beliefs(source, directory, executable, policy):
    """Portable public-posterior adapter around the native move policy."""
    if 'AI_BELIEF_PRIORS' not in policy.get('defines', []):
        raise ValueError('Native belief driver requires the opt-in prior API')
    executable.replace(directory/'observer')
    runtime = ['engine','observer']
    for name in ('campaign_native_beliefs.py','campaign_belief_values.py',
                 'campaign_joint_beliefs.py','calibrated_beliefs.py','feldmarschall.py'):
        (directory/name).write_bytes((source/'tools'/name).read_bytes())
        runtime.append(name)
    model = policy['joint_belief_model']
    if digest((source/model).read_bytes()) != policy['joint_belief_model_sha256']:
        raise ValueError('Native belief model failed integrity check')
    model_name = Path(model).name
    (directory/model_name).write_bytes((source/model).read_bytes())
    runtime.append(model_name)
    arguments = '['+', '.join('str(p / '+repr(arg)+')' if arg==model_name else repr(arg)
                             for arg in policy['driver_args'])+']'
    executable.write_text('#!/usr/bin/env python3\nimport os, pathlib, sys\n'
        'p = pathlib.Path(__file__).resolve().parent\n'
        f'if sys.argv[1:] == ["--identity"]:\n    print({policy["id"]!r})\n    raise SystemExit\n'
        'os.execv(sys.executable, [sys.executable, str(p / "campaign_native_beliefs.py"), '
        '"--observer", str(p / "observer"), *'+arguments+', *sys.argv[1:]])\n')
    executable.chmod(0o755)
    return runtime


def build_msdos1990(source, directory, executable, policy):
    """Freeze the headless interpreter and original images beside its launcher."""
    import importlib.util
    import sys
    package = ROOT / 'build/msdos1990/deps/unicorn'
    if not package.is_dir():
        found = importlib.util.find_spec('unicorn')
        if found and found.origin:
            package = Path(found.origin).parent
    if not package.is_dir():
        raise ValueError('Unicorn dependency missing. Run: python3 -m pip install --target build/msdos1990/deps unicorn==' + policy['emulator_version'])
    subprocess.run([sys.executable, '-c',
                    f'import sys;sys.path.insert(0,{str(package.parent)!r});import unicorn;assert unicorn.__version__=={policy["emulator_version"]!r}'],check=True)
    runtime = []
    for name in ('msdos1990.py', 'feldmarschall.py'):
        (directory / name).write_bytes((source / 'tools' / name).read_bytes())
        runtime.append(name)
    for path in sorted(package.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or 'include' in path.parts or path.suffix in ('.a','.pyc'):
            continue
        relative = Path('unicorn') / path.relative_to(package)
        target = directory / relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
        runtime.append(relative.as_posix())
    for name in policy['asset_files']:
        relative = Path('original') / Path(name).name
        target = directory / relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((source / name).read_bytes())
        runtime.append(relative.as_posix())
    # Preserve the emulator distribution's license without bundling unused
    # static libraries or C headers into every portable tournament.
    for path in sorted(package.parent.glob('unicorn-*.dist-info/licenses/**/*')):
        if path.is_file():
            relative=Path('emulator-licenses') / path.name
            (directory / relative).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,directory / relative)
            runtime.append(relative.as_posix())
    executable.write_text('#!/usr/bin/env python3\nimport os, pathlib, sys\n'
        'p=pathlib.Path(__file__).resolve().parent\n'
        f'if sys.argv[1:]==["--identity"]:\n    print({policy["id"]!r})\n    raise SystemExit\n'
        'os.execv(sys.executable,[sys.executable,str(p/"msdos1990.py"),"--assets",str(p/"original"),'
        f'"--identity",{policy["id"]!r},*{policy["driver_args"]!r},*sys.argv[1:]])\n')
    executable.chmod(0o755)
    runtime.append(executable.name)
    return runtime


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
