"""Verify focused cases, replay provenance and oracle-independent analysis."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile

from build_ai_mission_cases import public_case, public_analysis
from feldmarschall import ROOT, BOMB, FLAG, LAKES
from test_ai_diagnostics import verify_record


def verify(directory):
    corpus = ROOT / 'docs/ai-diagnostics/positions-20261014.zip'
    with zipfile.ZipFile(corpus) as archive:
        assert archive.testzip() is None
        records = {r['id']: r for line in archive.read('positions.jsonl').splitlines() if (r := json.loads(line))}
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert hashlib.sha256(corpus.read_bytes()).hexdigest() == manifest['source_corpus_sha256']
    assert hashlib.sha256((ROOT / 'tools/build_ai_mission_cases.py').read_bytes()).hexdigest() == manifest['analysis_source_sha256']
    data = (directory / 'cases.jsonl').read_bytes()
    assert hashlib.sha256(data).hexdigest() == manifest['cases_sha256']
    cases = [json.loads(line) for line in data.splitlines()]
    assert len(cases) == manifest['cases'] == 18
    assert len({(c['source']['archive'], c['source']['game_index']) for c in cases}) == 18
    assert {c['difficulty'] for c in cases} == {'normal', 'hard'}
    for case in cases:
        record = records[case['id']]
        verify_record(record)
        assert case == public_case(record, case['category'])
        assert all(a['move'] in case['legal_moves'] for a in case['analysis']['alternatives'])
        assert not {'referee_board', 'evidence', 'labels', 'replay'}.intersection(case)
        changed = copy.deepcopy(record)
        changed['referee_board'] = None; changed['evidence'] = None; changed['labels'] = []
        changed['replay']['deployments'][1 - record['input']['army']] = 'arbitrary hidden truth'
        assert case == public_case(changed, case['category'])
    # A stationary bomb wall, no miner and the enemy flag beyond it cannot
    # become an avoidable-cycle example merely because quiet moves exist.
    cells = [255] * 100
    for sq in LAKES: cells[sq] = 254
    cells[90] = 4; cells[99] = FLAG; cells[0] = FLAG | 16 | 32
    for sq in (40, 41, 44, 45, 48, 49): cells[sq] = BOMB | 16 | 32
    info = {'army': 0, 'board_hex': bytes(cells).hex()}
    result = public_analysis(info, [], [90, 91], [[90, 91], [90, 92]])
    assert result['structural_status'] == 'blocked_by_stationary_barriers'
    assert result['permanent_flag_route_blockage']
    # The same wall belonging to us may be opened by an opposing Miner.
    for sq in (40, 41, 44, 45, 48, 49): cells[sq] = BOMB
    info['board_hex'] = bytes(cells).hex()
    assert not public_analysis(info, [], [90, 91], [[90, 91], [90, 92]])['permanent_flag_route_blockage']
    # An open gap changes the necessary topology without revealing enemy ranks.
    cells[40] = 255; info['board_hex'] = bytes(cells).hex()
    assert public_analysis(info, [], [90, 91], [[90, 91], [90, 80]])['structural_status'] == 'optimistic_route_exists'
    print('18 distinct public cases: legal replay, alternatives, oracle exclusion and stationary blockage checks pass')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    verify(parser.parse_args().directory)
