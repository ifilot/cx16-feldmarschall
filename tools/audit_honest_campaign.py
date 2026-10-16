"""Read-only cross-check of completed campaign artifacts and frozen policies.

This verifies retained audit/replay receipts against current saved files. It does
not rerun games or re-prove the replay/strategy implementations, and it does not
claim the timed campaign is finished while cohorts remain running or queued.
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from ai_registry import ROOT, get_policy, receives_opponent_setup
from information_strategy_cycle import validate_metadata
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


def summarize_executions(completed, saved_executions, reuse_declarations, completed_saved_paths):
    """Count one physical control even if its source study is still pending."""
    attempts = sum(c['attempts'] for c in completed)
    unique_attempts = sum(count for count, errors in saved_executions.values())
    unique_errors = sum(errors for count, errors in saved_executions.values())
    for reuse in reuse_declarations:
        assert reuse['destination'] in completed_saved_paths
    duplicate_appearances = sum(reuse['attempts'] for reuse in reuse_declarations
                                if reuse['source'] in completed_saved_paths)
    assert attempts - unique_attempts == duplicate_appearances
    return dict(completed_attempts=attempts, unique_saved_attempts=unique_attempts,
                reused_comparison_attempts=duplicate_appearances,
                declared_reused_control_attempts=sum(reuse['attempts'] for reuse in reuse_declarations),
                errors_preserved_unscored=sum(c['errors'] for c in completed),
                errors_field_counts_comparison_appearances=True,
                unique_saved_unscored_errors=unique_errors)


def audit():
    completed, pending, rejected = [], [], []
    archives = {}
    saved_executions = {}
    reuse_declarations = []
    completed_saved_paths = set()
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
        plan = json.loads((directory / 'plan.json').read_text())
        registration_path = directory / ('freeze.json' if result.get('independent_honest_heads') else 'registration.json')
        registration = json.loads(registration_path.read_text())
        assert registration['plan_sha256'] == digest(directory / 'plan.json')
        registered_epoch = (registration['epoch'] if 'epoch' in registration else
                            datetime.fromisoformat(registration['prepared_utc']).timestamp())
        receipt = json.loads((directory / 'audit.json').read_text())
        assert receipt['passed']
        assert result['attempts'] == result['verified_games'] == receipt['attempts']
        assert result['errors'] == receipt['errors_preserved_unscored']
        if result.get('reused_control_attempts'):
            reuse_path = directory / 'shared-control-receipt.json'
            reuse = json.loads(reuse_path.read_text())
            assert reuse['passed'] and reuse['prospective']
            assert digest(reuse_path) == result['shared_control_receipt_sha256']
            assert digest(ROOT / reuse['source']) == reuse['source_sha256']
            assert digest(ROOT / reuse['destination']) == reuse['destination_sha256'] == reuse['source_sha256']
            assert result['new_attempts'] + result['reused_control_attempts'] == result['attempts']
            reuse_declarations.append(dict(source=reuse['source'], destination=reuse['destination'],
                                           attempts=result['reused_control_attempts']))
        hashes = verify_manifest(directory)
        frozen = json.loads((directory / 'frozen-policies.json').read_text())
        for identity, spec in frozen.items():
            assert get_policy(identity) == spec, identity
            if spec.get('driver') != 'msdos1990':
                assert not receives_opponent_setup(spec), identity
                assert 'AI_DIAGNOSTIC_TRUTH' not in spec.get('defines', []), identity
                assert '--diagnostic-truth' not in spec.get('driver_args', []), identity
            if 'archive' in spec:
                archives[spec['archive']] = spec['source_sha256']
        attempts = errors = reports = 0
        for path in sorted(directory.glob('*.report.json')):
            report = json.loads(path.read_text())
            saved = path.with_suffix('').with_suffix('.fmtour')
            assert digest(saved) == report['tournament_sha256'], str(saved)
            count = report['summary']['games']
            sha = report['tournament_sha256']
            totals = (count, report['summary']['errors'])
            if sha in saved_executions:
                assert saved_executions[sha] == totals
            saved_executions[sha] = totals
            completed_saved_paths.add(str(saved.relative_to(ROOT)))
            verification = report['verification']
            assert verification['artifacts_verified']
            assert count == verification['python_replayed'] == verification['native_replayed_all_states']
            validate_metadata(saved, report['match'], plan, frozen)
            with Tournament(saved) as tournament:
                metadata = tournament.metadata()
                assert metadata['status'] == 'complete' and metadata['rules'] == 'classic'
                assert datetime.fromisoformat(metadata['created_utc']).timestamp() >= registered_epoch
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
    accounting = summarize_executions(completed, saved_executions, reuse_declarations, completed_saved_paths)
    return dict(scope='Completed-cycle artifact and retained replay-receipt verification; no new games or replay re-execution. Pending cohorts are reported separately. Completed attempts count comparison appearances; unique saved attempts count byte-identical reused control artifacts only once.',
                passed=True, completed_cycles=completed, **accounting,
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
