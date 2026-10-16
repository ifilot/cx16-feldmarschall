"""Read-only cross-check of completed campaign artifacts and frozen policies.

This verifies retained audit/replay receipts against current saved files. It does
not rerun games or re-prove the replay/strategy implementations, and it does not
claim the timed campaign is finished while cohorts remain running or queued.
"""
import argparse
import hashlib
import json
from pathlib import Path

from ai_registry import ROOT, get_policy
from tournament_store import Tournament

BASE = ROOT / 'docs/ai-honest-campaign-2026-10-15'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(directory):
    document = json.loads((directory / 'manifest.json').read_text())
    files = document.get('files', document)
    for name, record in files.items():
        relative = Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts, name
        path = directory / relative
        sha = record['sha256'] if isinstance(record, dict) else record
        assert digest(path) == sha, str(path)
        if isinstance(record, dict) and 'bytes' in record:
            assert path.stat().st_size == record['bytes'], str(path)
    return len(files)


def audit():
    completed, pending, rejected = [], [], []
    archives = {}
    for directory in sorted(BASE.glob('cycle-*')):
        if not directory.is_dir():
            continue
        result_path = directory / 'result.json'
        if not result_path.exists():
            preflight = directory / 'preflight-result.json'
            if preflight.exists():
                result = json.loads(preflight.read_text())
                assert result['attempts'] == 0
                assert not list(directory.glob('*.fmtour')), directory.name
                if (directory / 'manifest.json').exists():
                    verify_manifest(directory)
                rejected.append(dict(directory=directory.name, status=result['status'], attempts=0))
            elif (directory / 'plan.json').exists():
                saved = []
                for path in sorted(directory.glob('*.fmtour')):
                    with Tournament(path) as tournament:
                        saved.append(dict(file=path.name, status=tournament.metadata()['status'], games=len(tournament.games())))
                pending.append(dict(directory=directory.name, saved=saved))
            continue
        result = json.loads(result_path.read_text())
        receipt = json.loads((directory / 'audit.json').read_text())
        assert receipt['passed']
        assert result['attempts'] == result['verified_games'] == receipt['attempts']
        assert result['errors'] == receipt['errors_preserved_unscored']
        hashes = verify_manifest(directory)
        frozen = json.loads((directory / 'frozen-policies.json').read_text())
        for identity, spec in frozen.items():
            assert get_policy(identity) == spec, identity
            if 'archive' in spec:
                archives[spec['archive']] = spec['source_sha256']
        attempts = errors = reports = 0
        for path in sorted(directory.glob('*.report.json')):
            report = json.loads(path.read_text())
            saved = path.with_suffix('').with_suffix('.fmtour')
            assert digest(saved) == report['tournament_sha256'], str(saved)
            count = report['summary']['games']
            verification = report['verification']
            assert verification['artifacts_verified']
            assert count == verification['python_replayed'] == verification['native_replayed_all_states']
            with Tournament(saved) as tournament:
                assert tournament.metadata()['status'] == 'complete'
                assert len(tournament.games()) == count
            capture = path.with_suffix('').with_suffix('.png')
            assert capture.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), str(capture)
            attempts += count
            errors += report['summary']['errors']
            reports += 1
        assert attempts == result['attempts'] and errors == result['errors'], directory.name
        completed.append(dict(cycle=result['cycle'], directory=directory.name, attempts=attempts,
                              errors=errors, reports_and_qt_captures=reports, manifest_files=hashes,
                              terminal_audit_sha256=digest(directory / 'audit.json')))
    for name, sha in archives.items():
        assert digest(ROOT / name) == sha, name
    return dict(scope='Completed-cycle artifact and retained replay-receipt verification; no new games or replay re-execution. Pending cohorts are reported separately.',
                passed=True, completed_cycles=completed, completed_attempts=sum(c['attempts'] for c in completed),
                errors_preserved_unscored=sum(c['errors'] for c in completed),
                immutable_policy_archives_verified=len(archives), pending_or_running=pending,
                rejected_before_matches=rejected, goal_completion_claim=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
