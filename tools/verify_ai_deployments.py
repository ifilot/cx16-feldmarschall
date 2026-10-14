"""Check recorded setup experiments actually isolate placements and swap them with engines."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from feldmarschall import valid_setup
from optimize_ai_deployments import identity


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args();run=args.run
    provenance=json.loads((run/'provenance.json').read_text())
    trials=json.loads((run/'trials.json').read_text())
    games=[json.loads(line) for line in (run/'games.jsonl').read_text().splitlines()]
    pairs=defaultdict(list)
    for game in games:
        side=int(game['candidate_blue']);foe=1-side;trial=trials[game['case']]
        assert (game['red'],game['blue'])[side]=='current'
        assert (game['red'],game['blue'])[foe]==trial['opponent']
        assert game['deployments'][side]==game['candidate_setup']
        assert game['deployments'][foe]==trial['opponent_setup']
        assert all(valid_setup(layout) for layout in game['deployments'])
        assert game['seed']==trial['seed'] and game['group']==trial['family']
        assert len(game['moves'])==game['plies']
        if game['setup_id'].startswith('setup-'):assert identity(game['candidate_setup'])==game['setup_id']
        pairs[(game['setup_id'],game['case'])].append(game)
    for pair in pairs.values():
        assert len(pair)==2 and {game['candidate_blue'] for game in pair}=={False,True}
        assert pair[0]['candidate_setup']==pair[1]['candidate_setup']
    for name,expected in provenance['engine_sha256'].items():
        assert hashlib.sha256((run/'engines'/name).read_bytes()).hexdigest()==expected
    for name,expected in provenance['support_sha256'].items():
        assert hashlib.sha256((run/name).read_bytes()).hexdigest()==expected
    assert provenance['fixed_policy']=='coordinated missions; student disabled'
    report={'games':len(games),'side_pairs':len(pairs),'legal_inventories_and_engine_following_setups':True,
            'move_policy':'frozen coordinated '+provenance['difficulty'],'program_hashes_valid':True}
    (run/'deployment-integrity.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
