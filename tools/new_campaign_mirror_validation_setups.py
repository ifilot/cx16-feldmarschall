"""Terminal two-arm original/mirrored deployment validation audit.

This does not read any game row until BOTH tournaments have terminal metadata.
Only original-selected mixture trajectories have a corresponding fixed arm.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile
import zlib

from tournament_store import Tournament


MIXTURE = 'student-fortress-mirror-mixture-template-v1-normal'


def reflect(army):
    assert len(army) == 40
    return ''.join(army[row * 10 + 9 - col] for row in range(4) for col in range(10))


def accepted_ticket(seed):
    # Independent local implementation of the frozen 16-bit generator, with
    # explicit truncation after each shift/XOR. No mixture-helper import.
    state = int(seed) & 0xffff
    state = state or 1
    draws = 0
    while True:
        state = (state ^ (state << 7)) & 0xffff
        state = (state ^ (state >> 9)) & 0xffff
        state = (state ^ (state << 8)) & 0xffff
        draws += 1
        if state <= 65530:
            return (state - 1) % 10, draws


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(directory):
    plan = json.loads((directory / 'plan.json').read_text())
    baseline = plan['baseline']
    assert set(plan['policies']) == {baseline, MIXTURE} and len(plan['policies']) == 2
    frozen = json.loads((directory / 'frozen-policies.json').read_text())
    root = directory.parents[2]
    paths = {identity: directory / (identity + '.fmtour') for identity in (baseline, MIXTURE)}
    # This barrier precedes loading ANY setup record or game outcome.
    for path in paths.values():
        with Tournament(path) as tournament:
            metadata = tournament.metadata()
            assert metadata['status'] == 'complete', 'Both full cohorts must be terminal first'
            assert metadata['rules'] == 'classic'
            assert metadata['setup_mode'] == 'policy-owned-rotated-v1'
    archive_path = root / frozen[baseline]['archive']
    assert sha(archive_path) == frozen[baseline]['source_sha256']
    with zipfile.ZipFile(archive_path) as archive:
        source = archive.read('src/core/ai_deploy.c').decode()
    declaration = source.split('static const uint8_t layouts[3][ARMY_SIZE] = {', 1)[1]
    first_row = declaration.split('{', 1)[1].split('}', 1)[0]
    ranks = [int(value.strip()) for value in first_row.split(',')]
    assert len(ranks) == 40 and all(0 <= rank < 12 for rank in ranks)
    original = ''.join('123456789SBF'[rank] for rank in ranks)
    mirrored = reflect(original)
    assert original != mirrored and reflect(mirrored) == original
    loaded = {}
    for identity, path in paths.items():
        with Tournament(path) as tournament:
            metadata = tournament.metadata()
            artifact = tournament.db.execute('SELECT data FROM artifacts WHERE sha256=?',
                                           (metadata['setup_records_sha256'],)).fetchone()
            raw = zlib.decompress(artifact['data'])
            assert hashlib.sha256(raw).hexdigest() == metadata['setup_records_sha256']
            setup_records = json.loads(raw)['records']
            records = {row['pair_id']: row for row in setup_records}
            assert len(records) == len(setup_records) == plan['rounds'] * len(plan['families'])
            games = {row['id']: tournament.game(row['id']) for row in tournament.games()}
            assert len(games) == metadata['planned_games'] == 2 * len(records)
            loaded[identity] = records, games
    base_records, base_games = loaded[baseline]
    mix_records, mix_games = loaded[MIXTURE]
    assert set(base_records) == set(mix_records) and set(base_games) == set(mix_games)
    counts = Counter()
    receipts = []
    for pair, record in sorted(mix_records.items()):
        base_record = base_records[pair]
        for key in ('setup_seed', 'move_seed', 'family', 'opponent_setup'):
            assert base_record[key] == record[key], (pair, key)
        assert base_record['owner_setup'] == original
        ticket, draws = accepted_ticket(record['setup_seed'])
        orientation = 'original' if ticket < 5 else 'mirror'
        expected = original if orientation == 'original' else mirrored
        assert record['owner_setup'] == expected, (pair, 'mixture canonical army')
        counts[orientation + '_pairs'] += 1
        counts['pairs_requiring_rng_rejection'] += draws > 1
        pair_games = [g for g in mix_games.values() if g['pair_id'] == pair]
        assert len(pair_games) == 2
        assert {('red' if g['red'] == MIXTURE else 'blue') for g in pair_games} == {'red', 'blue'}
        for game in pair_games:
            other = base_games[game['id']]
            side = 'red' if game['red'] == MIXTURE else 'blue'
            opponent_side = 'blue' if side == 'red' else 'red'
            assert game[side] == MIXTURE and other[side] == baseline
            assert game[opponent_side] == other[opponent_side] == plan['opponent']
            for key in ('id', 'pair_id', 'family', 'seed'):
                assert game[key] == other[key], (pair, key)
            assert game['seed'] == record['move_seed'] and game['family'] == record['family']
            rotate = reflect if side == 'blue' else lambda army: army
            assert game[side + '_setup'] == rotate(expected)
            assert other[side + '_setup'] == rotate(original)
            assert game[opponent_side + '_setup'] == other[opponent_side + '_setup'] == rotate(record['opponent_setup'])
            counts['intended_actual_color_setups'] += 2
            exact = orientation == 'original'
            if exact:
                for key in ('red_setup', 'blue_setup', 'moves', 'result', 'reason', 'plies'):
                    assert game[key] == other[key], (game['id'], key)
                counts['original_subset_exact_games'] += 1
                counts['original_subset_exact_error_prefixes'] += game['result'] == 'error'
            else:
                counts['mirrored_subset_games_without_fixed_mirror_reference'] += 1
            receipts.append(dict(game=game['id'], pair=pair, side=side, setup_ticket=ticket,
                                 setup_draws=draws, orientation=orientation,
                                 intended_setups_and_opponent_seeds_matched=True,
                                 exact_baseline_trajectory_checked=exact))
    return dict(passed=True, scope='Terminal two-arm deployment and original-selected-subset trajectory audit',
                counts=dict(counts), canonical_original=original, canonical_mirror=mirrored,
                baseline_archive_sha256=sha(archive_path), source_sha256=sha(Path(__file__)),
                tournament_sha256={identity: sha(path) for identity, path in paths.items()},
                records=receipts,
                limitation='No fixed mirror arm exists in this cohort. Mirrored-selected games are checked for intended setup, common opponents/seeds/sides only; no mirrored-subset trajectory-equivalence or strength claim follows.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = audit(args.directory.resolve())
    (args.directory / 'intended-setups-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'records'}))


if __name__ == '__main__':
    main()
