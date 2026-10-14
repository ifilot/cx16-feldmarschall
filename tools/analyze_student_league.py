"""Compare matched student and mission league blocks without treating opponents as independent blocks."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random


def load(run):
    provenance = json.loads((run/'provenance.json').read_text())
    assert provenance['phase'] == 'validation' and provenance['suite'] == 'broad'
    for name, digest in provenance['engine_sha256'].items():
        assert hashlib.sha256((run/'engines'/name).read_bytes()).hexdigest() == digest
    for name, digest in provenance.get('support_sha256', {}).items():
        assert hashlib.sha256((run/name).read_bytes()).hexdigest() == digest
    assert hashlib.sha256((run/'sources.zip').read_bytes()).hexdigest() == provenance['source_archive_sha256']
    games = [json.loads(line) for line in (run/'games.jsonl').read_text().splitlines()]
    assert len(games) == 70 * provenance['rounds_per_group']
    assert all(len(g['moves']) == g['plies'] and not g['reason'].startswith('illegal') for g in games)
    return provenance, games


def score(game): return .5 if game['winner'] is None else float(game['winner'] == 'current')


def analyze(candidate, control):
    cp, cg = load(candidate); bp, bg = load(control)
    assert cp['groups'] == bp['groups'] and cp['difficulty'] == bp['difficulty']
    assert {k:v for k,v in cp['engine_sha256'].items() if k != 'current'} == {k:v for k,v in bp['engine_sha256'].items() if k != 'current'}
    key = lambda g: (g['group'],g['round'],g['comparison'],g['red'],g['blue'])
    a, b = {key(g):g for g in cg}, {key(g):g for g in bg}
    assert len(a) == len(cg) and a.keys() == b.keys()
    blocks, opponents = defaultdict(list), defaultdict(list)
    for k, game in a.items():
        other = b[k]
        assert game['seed'] == other['seed'] and game['deployments'] == other['deployments']
        blocks[(game['group'],game['round'])].append(score(game)-score(other))
        opponents[game['comparison']].append((score(game),score(other)))
    families = defaultdict(list)
    for (family, _), values in blocks.items():
        assert len(values) == 10
        families[family].append(sum(values)/len(values))
    rng = random.Random(8675309)
    means = sorted(sum(rng.choice(values) for values in families.values() for _ in values)/len(blocks)
                   for _ in range(10000))
    return {'scope':'Classic Normal, five frozen opponents and seven equally weighted families; descriptive validation after freezing the student',
            'games_per_policy':len(cg), 'matched_blocks':len(blocks),
            'candidate_program_sha256':cp['engine_sha256']['current'],
            'control_program_sha256':bp['engine_sha256']['current'],
            'candidate_score':sum(map(score,cg))/len(cg), 'control_score':sum(map(score,bg))/len(bg),
            'difference':sum(sum(v) for v in blocks.values())/len(cg),
            'block_bootstrap_95':[means[250],means[9749]],
            'confidence_method':'10000 bootstrap samples of complete opponent-and-side blocks within each family; seed 8675309',
            'opponents':{k:{'candidate':sum(a for a,b in values)/len(values),
                            'control':sum(b for a,b in values)/len(values)} for k,values in opponents.items()},
            'candidate_capped':sum(g['reason']=='ply limit' for g in cg),
            'control_capped':sum(g['reason']=='ply limit' for g in bg)}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--control',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=analyze(args.candidate,args.control)
    with args.out.open('x') as output:output.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
