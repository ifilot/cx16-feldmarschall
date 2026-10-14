"""Verify diagnostic snapshots against complete public game replays."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import zipfile

from build_ai_diagnostics import permitted_view
from feldmarschall import Position, GLYPHS, square_name


def verify_record(record):
    position, lost, history = Position(), [[0]*12, [0]*12], []
    for army in (0, 1):
        position.place(army, record['replay']['deployments'][army])
    for ply, (src, dst) in enumerate(record['replay']['moves_before']):
        assert (src, dst) in position.moves(ply % 2)
        target = position.cells[dst]
        squares = f'{square_name(src)} {square_name(dst)}'
        if target is None:
            history.append('moved ' + squares)
            position.move(src, dst)
        else:
            a, d = position.cells[src][1], target[1]
            history.append(f'battle {squares} {GLYPHS[a]} {GLYPHS[d]}')
            _, fallen = position.fight(src, dst, a, d)
            for owner, rank, _, _ in fallen:
                lost[owner][rank] += 1
    army = record['input']['army']
    assert army == len(history) % 2
    assert history == record['public_history']
    assert permitted_view(position, army, lost) == record['input']
    assert position.cells == record['referee_board']
    assert [list(move) for move in position.moves(army)] == record['legal_moves']
    assert tuple(record['chosen_move']) in position.moves(army)
    # Concealed identities are exclusively referee data. Their permutation may
    # affect oracle labels, but must not change model-visible inputs.
    altered = copy.deepcopy(position)
    concealed = [sq for sq, cell in enumerate(altered.cells) if cell and cell[0] != army and not cell[3]]
    ranks = [altered.cells[sq][1] for sq in concealed]
    random.Random(1234).shuffle(ranks)
    for sq, rank in zip(concealed, ranks):
        altered.cells[sq][1] = rank
    assert permitted_view(altered, army, lost) == record['input']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path, help='corpus directory or retained ZIP')
    args = parser.parse_args()
    if args.corpus.suffix == '.zip':
        with zipfile.ZipFile(args.corpus) as archive:
            assert archive.testzip() is None
            manifest = json.loads(archive.read('manifest.json'))
            data = archive.read('positions.jsonl')
            for name, expected in manifest['source_sha256'].items():
                assert hashlib.sha256(archive.read('sources/'+name)).hexdigest() == expected
        external = args.corpus.parent/'manifest.json'
        if external.exists():
            metadata = json.loads(external.read_text())
            if metadata.get('archive') == args.corpus.name:
                assert hashlib.sha256(args.corpus.read_bytes()).hexdigest() == metadata['archive_sha256']
    else:
        manifest = json.loads((args.corpus/'manifest.json').read_text())
        data = (args.corpus/'positions.jsonl').read_bytes()
    assert hashlib.sha256(data).hexdigest() == manifest['positions_sha256']
    records = [json.loads(line) for line in data.splitlines()]
    assert len(records) == manifest['positions']
    assert len({record['id'] for record in records}) == len(records)
    for record in records:
        verify_record(record)
    print(f'{len(records)} diagnostic snapshots: legal replay, public history, masked input and concealed-rank permutation checks pass')


if __name__ == '__main__':
    main()
