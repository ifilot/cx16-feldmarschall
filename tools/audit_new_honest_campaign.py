"""Verify the two-hour campaign, retained evidence and immutable setup corpus.

This checks saved receipts, not a second execution of every replay. Completion
also requires the declared deadline, settled cohorts and committed cycle files.
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import audit_honest_campaign as retained
from ai_registry import ROOT

BASE = ROOT / 'docs/ai-honest-campaign-2026-10-16'
CORPUS = 'tests/datasets/classic-generalization-v1'
CORPUS_COMMIT = '9937c31'


def research_evidence(directory):
    """Interpreter caches are local byproducts, not portable research evidence."""
    return [p for p in directory.rglob('*') if p.is_file()
            and p != directory / 'manifest.json'
            and '__pycache__' not in p.relative_to(directory).parts and p.suffix != '.pyc']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def audit(complete=False):
    retained.BASE = BASE
    result = retained.audit()
    timing = json.loads((BASE / 'timing.json').read_text())
    start = datetime.fromisoformat(timing['start_utc'])
    deadline = datetime.fromisoformat(timing['deadline_utc'])
    now = datetime.now(timezone.utc)
    assert (deadline - start).total_seconds() == timing['duration_seconds'] == 7200
    corpus_files = git('ls-tree', '-r', '--name-only', CORPUS_COMMIT, '--', CORPUS).decode().splitlines()
    assert corpus_files
    for name in corpus_files:
        assert (ROOT / name).read_bytes() == git('show', f'{CORPUS_COMMIT}:{name}'), name
    current_files = {str(p.relative_to(ROOT)) for p in (ROOT / CORPUS).rglob('*') if p.is_file()}
    assert current_files == set(corpus_files), 'Frozen corpus file set changed'
    commits = {}
    introducing_commits = []
    for cycle in result['completed_cycles']:
        directory = BASE / cycle['directory']
        files = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()
                 and p.name != 'manifest.json'}
        manifest = json.loads((directory / 'manifest.json').read_text())
        assert files == set(manifest.get('files', manifest)), directory
        relative = str(directory.relative_to(ROOT))
        changed = git('status', '--porcelain', '--untracked-files=all', '--', relative).decode()
        commit = git('log', '-1', '--format=%H', '--', relative).decode().strip()
        introduced = git('log', '--diff-filter=A', '--format=%H', '--', relative + '/result.json').decode().splitlines()
        commits[relative] = dict(latest_commit=commit, working_files_committed=not changed,
                                 result_introducing_commits=introduced)
        if complete:
            assert commit and not changed and len(introduced) == 1, relative
            introducing_commits += introduced
    research = BASE / 'research'
    research_manifest = research / 'manifest.json'
    research_files_verified = None
    if research_manifest.exists():
        files = {str(p.relative_to(research)) for p in research_evidence(research)}
        manifest = json.loads(research_manifest.read_text())
        assert files == set(manifest.get('files', manifest)), 'Research manifest coverage'
        research_files_verified = retained.verify_manifest(research)
    if complete:
        assert now >= deadline, 'The user-authorized two-hour interval has not elapsed'
        assert not result['pending_or_running'], 'A frozen cohort is not fully audited'
        assert len(set(introducing_commits)) == len(introducing_commits), 'Cycles share an introducing commit'
        assert research_files_verified is not None, 'Research evidence needs its final manifest'
        paths = [str(research.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT))]
        for name in ('README.md', 'OVERVIEW.md', 'timing.json', 'REPORT.md'):
            path = BASE / name
            assert path.is_file(), name
            paths.append(str(path.relative_to(ROOT)))
        assert not git('status', '--porcelain', '--untracked-files=all', '--', *paths), 'Uncommitted campaign research or metadata'
    result.update(
        timing=dict(**timing, observed_utc=now.isoformat(), deadline_reached=now >= deadline),
        frozen_corpus_files_verified=len(corpus_files),
        frozen_corpus_reference_commit=CORPUS_COMMIT,
        research_manifest_files_verified=research_files_verified,
        cycle_commits=commits,
        goal_completion_claim=complete,
        completion_scope='Two hours; all frozen cohorts settled; cycle evidence committed' if complete else
                         'Interim retained-evidence audit; no completion claim')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--complete', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    document = audit(args.complete)
    rendered = json.dumps(document, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered)
