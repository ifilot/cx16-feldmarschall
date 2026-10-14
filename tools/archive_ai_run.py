"""Preserve a completed AI run and its keep/reject decision in the repository."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from feldmarschall import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--decision', choices=('keep', 'reject', 'diagnostic'), required=True)
    parser.add_argument('--reason', required=True)
    parser.add_argument('--name', help='archive name, without extension')
    args = parser.parse_args()
    report = json.loads((args.run / 'summary.json').read_text())
    name = args.name or args.run.name
    if Path(name).name != name:
        parser.error('--name must be a filename')
    destination = ROOT / 'docs/ai-runs' / (name + '.zip')
    entry = {
        'name': name, 'decision': args.decision, 'reason': args.reason,
        'source_sha256': report['provenance']['source_sha256'],
        'phase': report['provenance'].get('phase', 'historical'),
        'strategy': report['provenance'].get('strategy', 'historical'),
        'suite': report['provenance'].get('suite', 'classic'),
        'difficulty': report['provenance'].get('difficulty'),
        'comparisons': {key: value['overall'] for key, value in report['comparisons'].items()},
        'source_snapshot_available': (args.run / 'sources.zip').exists(),
        'evaluator_snapshot_available': (args.run / 'sources.zip').exists() or (args.run / 'candidate.c').exists(),
        'executable_snapshots_available': (args.run / 'engines').exists(),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for filename in ('provenance.json', 'games.jsonl', 'summary.json', 'sources.zip', 'endgames.json', 'candidate.c',
                         'portfolio.json', 'trials.json', 'deployment-block-analysis.json', 'analysis-sources.zip',
                         'deployment-integrity.json', 'policy.json', 'frozen-policy.json',
                         'selection-integrity.json', 'model-binding.json', 'model-sources.zip'):
            path = args.run / filename
            if path.exists():
                archive.write(path, filename)
        archive.writestr('experiment.json', json.dumps(entry, indent=2) + '\n')
        if (args.run / 'engines').exists():
            for path in sorted((args.run / 'engines').rglob('*')):
                if path.is_file():
                    archive.write(path, str(path.relative_to(args.run)))
    entry['archive'] = 'ai-runs/' + destination.name
    entry['archive_sha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
    ledger = ROOT / 'docs/ai-experiments.json'
    entries = json.loads(ledger.read_text()) if ledger.exists() else []
    entries.append(entry)
    ledger.write_text(json.dumps(entries, indent=2) + '\n')
    print(destination)


if __name__ == '__main__':
    main()
