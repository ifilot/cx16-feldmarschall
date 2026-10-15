"""Compile the native mechanism test both ways and prove default byte parity."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

from ai_registry import ROOT, build_policy, get_policy


def run():
    identity = 'student-guard-v1-normal'
    policy = get_policy(identity)
    frozen, receipt = build_policy(identity)
    common = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Wno-format-overflow',
              '-Isrc/core'] + ['-I' + s for s in policy.get('include_dirs', [])]
    defines = ['-D' + s for s in policy['defines']]
    links = [s for s in policy['sources'] if s not in ('src/native/engine.c', 'src/core/ai.c')]
    runs = []
    commands = []
    with tempfile.TemporaryDirectory(prefix='public-flag-threat-tests-') as temp:
        for enabled in (False, True):
            executable = Path(temp) / ('guard' if enabled else 'default')
            command = [*common, *defines, *(['-DAI_PUBLIC_FLAG_THREATS'] if enabled else []),
                       'tests/ai_public_flag_threats_test.c', *links, '-o', str(executable)]
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
            result = subprocess.run([str(executable)], cwd=ROOT, check=True, capture_output=True, text=True)
            runs.append(json.loads(result.stdout))
            commands.append(shlex.join(command))
        current = Path(temp) / 'current-default'
        command = [*common, '-DFELDMARSCHALL_AI_ID="' + identity + '"', *defines,
                   '-o', str(current), *policy['sources']]
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        default_sha = hashlib.sha256(current.read_bytes()).hexdigest()
        frozen_sha = hashlib.sha256(frozen.read_bytes()).hexdigest()
        assert default_sha == frozen_sha, (default_sha, frozen_sha)
        commands.append(shlex.join(command))
    assert runs[0]['defended'] == 0 and runs[1]['defended'] == 32
    return dict(passed=True, kind='isolated-native-public-flag-threat-mechanism',
                runs=runs, commands=commands, frozen_policy=identity,
                frozen_source_sha256=policy['source_sha256'], frozen_native_receipt=receipt,
                default_byte_identical=True, current_default_sha256=default_sha,
                frozen_default_sha256=frozen_sha,
                current_source_sha256=hashlib.sha256((ROOT/'src/core/ai.c').read_bytes()).hexdigest(),
                test_source_sha256=hashlib.sha256((ROOT/'tests/ai_public_flag_threats_test.c').read_bytes()).hexdigest(),
                strength_evidence=False)


class PublicFlagThreatTests(unittest.TestCase):
    def test_native_public_deduction_and_default_parity(self):
        self.assertTrue(run()['passed'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    text = json.dumps(run(), indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end='')
