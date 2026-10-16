"""Independent terminal C119 accounting and paired interval; never runs games."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from direct_sql_review import review as review_sql
from mirror_direct_review import BASELINE, MIXTURE, bootstrap, load


def review(directory):
    directory=Path(directory)
    # This gate checks a complete, exact manifest and terminal metadata before
    # any game rows are inspected by this final-study-specific reviewer.
    accounting=review_sql(directory)
    plan=json.loads((directory/'plan.json').read_text())
    assert plan['cycle']==119 and plan['policies']==[BASELINE,MIXTURE]
    assert plan['seed']==3119001 and plan['rounds']==512
    assert plan['families']==['original-dos'] and plan['max_plies']==1000
    assert plan['setup_mode']=='policy-owned-rotated-v1'
    assert plan['selection_protocol_sha256']=='3c2a468fb6413cde05943e6989f0b065c39e058c21cb875bc6b90ef389ee6850'
    games={p:load(directory/(p+'.fmtour'),p) for p in plan['policies']}
    assert set(games[BASELINE])==set(games[MIXTURE])
    pairs=defaultdict(list)
    for identity,a in games[MIXTURE].items():
        b=games[BASELINE][identity]
        assert a['pair_id']==b['pair_id']
        pairs[a['pair_id']].append((a,b))
    blocks=[]
    for _,rows in sorted(pairs.items()):
        assert len(rows)==2
        if any(a['points'] is None or b['points'] is None for a,b in rows):continue
        blocks.append((rows[0][0]['family'],sum(a['points']-b['points'] for a,b in rows)/2))
    interval=bootstrap(blocks)
    result=json.loads((directory/'result.json').read_text())
    stored=result['comparisons'][MIXTURE+' minus '+BASELINE]
    for key in ('mean','interval_95','interval_98_3333'):
        assert interval[key]==stored['metrics']['score'][key],key
    assert interval['complete_pairs']==stored['complete_pairs']
    assert interval['pairs_by_family']==stored['pairs_by_family']
    return dict(passed=True,cycle=119,independent_sql=accounting,
        independent_paired_bootstrap=interval,
        scope='Fresh DOS-specific validation only. Complete terminal accounting and independently regenerated paired interval; no new matches, pooling, tuning, selected-fixed-arm trajectory claim, production RNG robustness or hardware inference.',
        auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        bootstrap_auditor_sha256=hashlib.sha256(Path(__file__).with_name('mirror_direct_review.py').read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();receipt=review(args.directory)
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
