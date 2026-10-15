"""Verify analysis-only recovery without playing or editing a tournament."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[1].parent
sys.path.insert(0, str(ROOT/'tools'))
from campaign_cycle import audit
from tournament_store import Tournament


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    recovery = json.loads((DIRECTORY/'analysis-recovery.json').read_text())
    assert recovery['games_rerun'] == 0
    hashes = recovery['tournament_sha256']
    assert len(hashes) == 3
    for name, expected in hashes.items():
        assert digest(DIRECTORY/name) == expected, name
    result = json.loads((DIRECTORY/'result.json').read_text())
    assert result['attempts'] == result['verified_games'] == 6300
    previous = ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-05-joint-setup-beliefs'
    current_frozen = json.loads((DIRECTORY/'frozen-policies.json').read_text())
    previous_frozen = json.loads((previous/'frozen-policies.json').read_text())
    assert all(previous_frozen[k] == v for k, v in current_frozen.items())
    assignments, seeds = [], []
    for folder in (previous, DIRECTORY):
        with Tournament(folder/'teacher-context-v1-normal.fmtour') as tournament:
            assignments.append({tuple(row) for row in tournament.db.execute(
                'SELECT family,seed,red_setup,blue_setup FROM games')})
            seeds.append({row[0] for row in tournament.db.execute('SELECT seed FROM games')})
    assert not assignments[0] & assignments[1]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        audit(DIRECTORY)
    (DIRECTORY/'campaign-cycle-audit.log').write_text(output.getvalue()+'campaign_cycle.audit passed\n')
    for name, expected in hashes.items():
        assert digest(DIRECTORY/name) == expected, name
    log = Path('/tmp/campaign-cycle12-analysis-recovery.log')
    if log.exists():
        (DIRECTORY/'analysis-recovery.log').write_bytes(log.read_bytes())
    proof = dict(passed=True, games_rerun=0,
        recovery_declaration_sha256=digest(DIRECTORY/'analysis-recovery.json'),
        initial_failure_log_sha256=digest(DIRECTORY/'analysis-first-attempt.log'),
        tournament_sha256_before_recovery=hashes,
        tournament_sha256_after_recovery={name:digest(DIRECTORY/name) for name in hashes},
        attempts=result['attempts'], python_native_verified=result['verified_games'],
        errors_preserved_unscored=result['errors'], frozen_specs_exactly_equal_to_cycle5=True,
        full_assignment_overlap_with_cycle5=len(assignments[0]&assignments[1]),
        incidental_raw_move_seed_overlap=len(seeds[0]&seeds[1]),
        seed_note='Raw bounded move-seed collisions do not repeat armies; full assignments have zero overlap.',
        campaign_cycle_audit=json.loads((DIRECTORY/'audit.json').read_text()),
        result_sha256=digest(DIRECTORY/'result.json'),
        audit_source_sha256=digest(ROOT/'tools/campaign_cycle.py'),
        verification_script_sha256=digest(Path(__file__)))
    (DIRECTORY/'analysis-recovery-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))


if __name__ == '__main__':
    main()
