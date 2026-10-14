"""Verify the experiment ledger against retained sources, programs and games."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

from feldmarschall import ROOT


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(entry, base):
    path = base / entry['archive']
    require(digest(path.read_bytes()) == entry['archive_sha256'], f'{path}: archive hash')
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, f'{path}: archive CRC')
        provenance = json.loads(archive.read('provenance.json'))
        require(provenance['source_sha256'] == entry['source_sha256'], f'{path}: evaluator identity')
        names = set(archive.namelist())
        evaluator = archive.read('candidate.c') if 'candidate.c' in names else None
        if 'sources.zip' in names:
            source_bytes = archive.read('sources.zip')
            require(digest(source_bytes) == provenance['source_archive_sha256'], f'{path}: source archive hash')
            with zipfile.ZipFile(io.BytesIO(source_bytes)) as sources:
                require(sources.testzip() is None, f'{path}: source CRC')
                if evaluator is None:
                    source = provenance.get('candidate_source', 'src/core/ai.c')
                    # Preserve portability when the original checkout was elsewhere.
                    matches = [name for name in sources.namelist()
                               if source == name or source.endswith('/' + name)]
                    if not matches and 'candidate/' + Path(source).name in sources.namelist():
                        matches = ['candidate/' + Path(source).name]
                    require(len(matches) == 1, f'{path}: ambiguous/missing evaluator {source}')
                    evaluator = sources.read(matches[0])
        require(evaluator is not None and digest(evaluator) == entry['source_sha256'], f'{path}: evaluator hash')
        executable_snapshots = any(name.startswith('engines/') for name in names)
        if executable_snapshots:
            for name, expected in provenance['engine_sha256'].items():
                require(digest(archive.read('engines/' + name)) == expected, f'{path}: executable {name}')
        for name, expected in provenance.get('support_sha256', {}).items():
            require(digest(archive.read(name)) == expected, f'{path}: supporting script {name}')
        games = [json.loads(line) for line in archive.read('games.jsonl').splitlines() if line.strip()]
        expected_games = sum(result['games'] for result in entry['comparisons'].values())
        require(len(games) == expected_games, f'{path}: game count {len(games)} != {expected_games}')
        for game in games:
            if 'moves' in game:
                require(len(game['moves']) == game['plies'], f'{path}: incomplete trace')
        return len(games)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, default=ROOT / 'docs/ai-experiments.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'docs/ai-runs/archive-integrity.json')
    args = parser.parse_args()
    entries = json.loads(args.ledger.read_text())
    games = sum(verify(entry, args.ledger.parent) for entry in entries)
    report = {'archives_checked': len(entries), 'games_in_ledger': games,
              'crc_and_archive_hashes_valid': True, 'evaluator_hashes_valid': True,
              'retained_executable_hashes_valid': True, 'supporting_script_hashes_valid': True,
              'game_counts_and_trace_lengths_valid': True}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
