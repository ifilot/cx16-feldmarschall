"""Native capability assignment: public invariance, tactical parity, actual move change."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from ai_registry import ROOT, build_policy, get_policy


def audit():
    p = get_policy('student-guard-v1-normal')
    common = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Wno-format-overflow', '-Isrc/core']
    common += ['-I'+v for v in p['include_dirs']] + ['-D'+v for v in p['defines']]
    links = [v for v in p['sources'] if v not in ('src/core/ai.c', 'src/native/engine.c')]
    rows = []
    with tempfile.TemporaryDirectory(prefix='task-assignment-') as temp:
        for enabled in (False, True):
            executable = Path(temp)/str(enabled)
            subprocess.run(common+['-DAI_DIAGNOSTICS', '-DAI_TRACE']+(['-DAI_TASK_ASSIGNMENT'] if enabled else [])
                           +['tests/ai_task_assignment_test.c', *links, '-o', str(executable)],
                           cwd=ROOT, capture_output=True, text=True, check=True)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            cases = {}
            for line in result.stdout.splitlines():
                tokens = line.split()
                if tokens[0] == 'case':
                    scenario, level, rank, *outputs = map(int, tokens[1:])
                    cases[scenario, level, rank] = outputs
                elif tokens[0] == 'prefix':
                    prefix = list(map(int, tokens[1:]))
                elif tokens[0] == 'cost':
                    cost = float(tokens[1])
                elif tokens[0] == 'checks':
                    checks, failures = map(int, tokens[1:])
            assert failures == 0
            for scenario in range(7):
                for level in range(3):
                    assert all(cases[scenario, level, rank] == cases[scenario, level, 0] for rank in range(12))
            rows.append(dict(cases=cases, prefix=prefix, mean_seconds=cost, native_checks=checks))
        parity = []
        for key in rows[0]['cases']:
            scenario, level, rank = key
            assert rows[0]['cases'][key][-1] == rows[1]['cases'][key][-1], ('capture-score-parity', key)
            if scenario or level != 1:
                # Tactical roots can update goals while preserving the forcing move.
                n = 2 if scenario in (4, 5) and level == 1 else 6
                assert rows[0]['cases'][key][:n] == rows[1]['cases'][key][:n], key
                parity.append(key)
        # Preprocessor-off must reproduce the immutable production executable.
        executable = Path(temp)/'default'
        subprocess.run(common+['-DFELDMARSCHALL_AI_ID="'+p['id']+'"', *p['sources'], '-o', str(executable)], cwd=ROOT,
                       capture_output=True, text=True, check=True)
        frozen, _ = build_policy(p['id'])
        default_sha = hashlib.sha256(executable.read_bytes()).hexdigest()
        assert default_sha == hashlib.sha256(frozen.read_bytes()).hexdigest()
    return dict(passed=True, default_byte_identical=True, default_sha256=default_sha,
                hidden_nibble_invariance_cases=7*3*12, capture_score_parity_cases=7*3*12, unchanged_gated_or_ineligible_cases=len(parity),
                first_common_move=rows[0]['prefix'][:2], baseline_next_move=rows[0]['prefix'][2:4],
                assignment_next_move=rows[1]['prefix'][2:4],
                baseline_seconds=rows[0]['mean_seconds'], assignment_seconds=rows[1]['mean_seconds'],
                native_checks=[r['native_checks'] for r in rows],
                source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                               ('src/core/ai.c','tests/ai_task_assignment_test.c','tools/test_task_assignment.py')})

class NativeAssignment(unittest.TestCase):
    def test_mechanism(self):
        evidence = audit()
        path = ROOT/'docs/ai-honest-campaign-2026-10-15/research/task-assignment-native-audit.json'
        path.write_text(json.dumps(evidence, indent=2)+'\n')
        self.assertTrue(evidence['passed'])

if __name__ == '__main__':
    unittest.main()
