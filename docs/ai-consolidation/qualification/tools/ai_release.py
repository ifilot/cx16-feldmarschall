"""Verify or import an explicitly selected, qualified portable AI release."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]
GATES = {'dos_noninferiority','honest_noninferiority','x16_turns','lifecycle',
         'reproducibility','memory','previous_levels_and_rules','packaging'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(manifest):
    assert manifest['schema'] == 'feldmarschall-ai-release-v1'
    assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-v\d+-normal', manifest['id'])
    assert manifest['status'] == 'qualified'
    assert manifest['rules'] == 'Classic' and manifest['difficulty'] == 'normal'
    assert manifest['information_model'] == 'own-army-and-public-observations'
    assert manifest['files']
    for name, checksum in manifest['files'].items():
        path = PurePosixPath(name)
        assert path.parent == PurePosixPath('src/core')
        assert re.fullmatch(r'ai[a-z_]*\.(?:c|h)', path.name), name
        assert re.fullmatch(r'[0-9a-f]{64}', checksum)
    assert manifest['build_recipe'] == 'cc65-banked-inference-v1'
    assert 'BANKED_AI' in manifest['target_defines']
    assert all(re.fullmatch(r'[A-Z][A-Z0-9_]*', flag) for flag in manifest['target_defines'])
    assert not any('DIAGNOSTIC' in flag or flag == 'AI_TEST' for flag in manifest['target_defines'])


def validate_report(data, identity):
    report = json.loads(data)
    assert report['schema'] == 'feldmarschall-ai-release-qualification-v1'
    assert report['candidate'] == identity
    assert report['passed'] is True
    assert set(report['gates']) == GATES
    assert all(value is True for value in report['gates'].values())


def verify(root=ROOT):
    manifest = json.loads((root/'ai-release/manifest.json').read_text())
    validate(manifest)
    for name, checksum in manifest['files'].items():
        assert digest((root/name).read_bytes()) == checksum, name
    qualification = (root/'ai-release/qualification.json').read_bytes()
    assert digest(qualification) == manifest['qualification_sha256']
    validate_report(qualification, manifest['id'])
    return manifest


def install(package, root=ROOT):
    manifest_bytes = (package/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    validate(manifest)
    payload = {name:(package/name).read_bytes() for name in manifest['files']}
    assert all(digest(data) == manifest['files'][name] for name,data in payload.items())
    qualification = (package/'qualification.json').read_bytes()
    assert digest(qualification) == manifest['qualification_sha256']
    validate_report(qualification, manifest['id'])
    previous = root/'ai-release/manifest.json'
    if previous.exists():
        old = json.loads(previous.read_text())
        if old['id'] == manifest['id']:
            assert old == manifest, 'An existing release ID is immutable; export a new version'
    for name,data in payload.items():
        (root/name).write_bytes(data)
    previous.parent.mkdir(exist_ok=True)
    (previous.parent/'qualification.json').write_bytes(qualification)
    previous.write_bytes(manifest_bytes)
    return verify(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify','import'))
    parser.add_argument('package', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'import':
        if args.package is None:
            parser.error('import requires a release directory')
        result = install(args.package.resolve())
    else:
        result = verify()
    print('Verified AI release '+result['id'])
