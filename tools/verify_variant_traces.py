"""Replay every retained move and permitted notification against frozen C rules."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path

from feldmarschall import GLYPHS, square_name
from variant_rules import VariantPosition


def replay(job):
    game,library,max_plies=job
    truth=VariantPosition(game['rules'],library)
    for army in (0,1):truth.place(army,game['deployments'][army])
    counts=Counter();coverage=Counter();ending=None
    assert len(game['moves'])==len(game['events'])==game['plies']
    for ply,(move,events) in enumerate(zip(game['moves'],game['events'])):
        assert ending is None
        side=ply%2;src,dst=move
        assert (src,dst) in truth.moves(side),(game['rules'],ply,move)
        attacker=truth.cells[src]&15;defender=truth.cells[dst]&15 if truth.cells[dst]<254 else None
        event,ending=truth.apply(src,dst);expected=[event]
        if attacker==10:coverage['bomb_moves']+=1
        if attacker==11:coverage['flag_moves']+=1
        if ending=='flag arrival':coverage['flag_arrival_wins']+=1
        if defender==10 and event.endswith(' X'):coverage['bomb_blasts']+=1
        if attacker==defender and event.endswith(' A'):coverage['attacker_wins_ties']+=1
        if game['rules']&2 and attacker==8 and defender is not None:coverage['silent_scout_disclosures']+=1
        if event.endswith(' D') and truth.lib.rules_can_rescue(dst):coverage['failed_attack_rescue_suppressed']+=1
        counts[event.split()[0]]+=1
        if event.startswith('combat') and event.split()[4]=='?':counts['hidden_defender']+=1
        if not ending:
            rescue=truth.auto_rescue(dst)
            if rescue:
                trigger,destination,rank,visible=rescue
                own=f'reinforce {square_name(trigger)} {square_name(destination)} {GLYPHS[rank]} {int(visible)}'
                opponent=f'reinforce {square_name(trigger)} {square_name(destination)} {GLYPHS[rank] if visible else "?"} {int(visible)}'
                expected.append({'owner':side,'own':own,'opponent':opponent});counts['rescue']+=1
                coverage['public_rescues' if visible else 'private_rescues']+=1
        assert events==expected,(game['rules'],ply,events,expected)
    if ending:reason=ending;winner=(game['plies']-1)%2
    else:
        side=game['plies']%2
        if not truth.moves(side):
            if truth.moves(1-side):reason,winner='no moves',1-side
            else:reason,winner='neither can move',None
        else:
            assert game['plies']>=max_plies
            reason,winner='ply limit',None
    assert game['reason']==reason
    assert game['result']=={None:'draw',0:'red',1:'blue'}[winner]
    assert game['winner']==(None if winner is None else game[('red','blue')[winner]])
    assert game['event_counts']==dict(counts)
    assert game.get('view_checks',2*(game['plies']+1))==2*(game['plies']+1)
    return game['plies'],dict(counts),dict(coverage)


def verify(root,jobs=4):
    plan=json.loads((root/'plan.json').read_text())
    logic=plan.get('logic_sha256',{})
    if 'tools/variant_rules.py' in logic:
        assert hashlib.sha256(Path(__file__).with_name('variant_rules.py').read_bytes()).hexdigest()==logic['tools/variant_rules.py']
    games=plies=0;counts=Counter();coverage=Counter()
    with ProcessPoolExecutor(jobs) as pool:
        for rules in plan['rules']:
            for level in ('normal','hard'):
                run=root/f'rules-{rules:02d}-{level}';library=run/'engines/support/referee/rules.so'
                assert hashlib.sha256(library.read_bytes()).hexdigest()==plan['program_sha256']['librules-variant.so']
                records=[json.loads(line) for line in (run/'games.jsonl').read_text().splitlines()]
                for length,events,special in pool.map(replay,((g,str(library.resolve()),1000) for g in records),chunksize=8):
                    games+=1;plies+=length;counts.update(events);coverage.update(special)
                print(f'Replayed rules {rules}, {level}: {len(records)} games',flush=True)
    return {'games_replayed':games,'plies_replayed':plies,'event_counts':dict(counts),'variant_coverage':dict(coverage),
            'scope':'Every move legal, public/private rescue notifications and battle disclosure exact, final outcome/reason and event counts reproduced against retained C library.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    parser.add_argument('--jobs',type=int,default=4);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=verify(args.root,args.jobs)
    with args.out.open('x') as output:output.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
