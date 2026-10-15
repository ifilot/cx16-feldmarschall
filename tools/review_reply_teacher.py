"""Reconstruct the eighteen Scout-loss roots and their public replies."""
import hashlib
import json

from ai_registry import ROOT
from build_ai_diagnostics import permitted_view
from feldmarschall import GLYPHS, Position, square_name
from tournament_store import Tournament

BASE=ROOT/'docs/ai-reply-teacher-2026-10-15'
SOURCE=ROOT/'docs/ai-linked-scouting-2026-10-15'


def review():
    losses=json.loads((SOURCE/'activity.json').read_text())['all_valued_probe_loss_followups']
    assert len(losses)==18
    cases=[]
    for record in losses:
        path=SOURCE/record['tournament']
        with Tournament(path) as tournament:game=tournament.game(record['game'])
        position=Position();history=[];lost=[[0]*12,[0]*12];army=record['ply']%2
        for side in (0,1):position.place(side,game['red_setup' if side==0 else 'blue_setup'])
        case=None
        for ply,(src,dst) in enumerate(game['moves']):
            moving,target=position.cells[src],position.cells[dst]
            if ply==record['ply']:
                assert [src,dst]==record['move']
                case=dict(id=hashlib.sha256(f'{path.name}:{game["id"]}:{ply}'.encode()).hexdigest()[:20],
                    input=permitted_view(position,army,lost),public_history=list(history),
                    own_initial_setup=game['red_setup' if army==0 else 'blue_setup'],
                    legal_moves=[list(m) for m in position.moves(army)],recorded_probe=[src,dst],
                    source=dict(tournament=str(path.relative_to(ROOT)),game=game['id'],ply=ply,
                                family=game['family'],seed=game['seed']),
                    observed_followup=record)
            squares=square_name(src)+' '+square_name(dst)
            if target is None:history.append('moved '+squares);position.move(src,dst)
            else:
                history.append(f'battle {squares} {GLYPHS[moving[1]]} {GLYPHS[target[1]]}')
                _,fallen=position.fight(src,dst,moving[1],target[1])
                for side,rank,_,_ in fallen:lost[side][rank]+=1
            if case is not None:
                if ply==record['ply']:case['public_probe_event']=history[-1]
                if ply==record['ply']+1:
                    case['public_opponent_reply']=history[-1]
                    break
        assert case is not None
        cases.append(case)
    return cases


if __name__=='__main__':
    cases=review()
    with (BASE/'public-cases.jsonl').open('x') as out:
        for case in cases:out.write(json.dumps(case,sort_keys=True)+'\n')
    report=dict(scope='Public replay of all eighteen previously credited Scout-loss probes. Observed outcomes are diagnostic metadata, excluded from teacher inputs and strength evaluation.',
                cases=len(cases),source_sha256=hashlib.sha256((SOURCE/'activity.json').read_bytes()).hexdigest(),
                cases_sha256=hashlib.sha256((BASE/'public-cases.jsonl').read_bytes()).hexdigest(),
                terminal_before_next_turn=sum(c['observed_followup'].get('game_ended_before_next_turn',False) for c in cases),
                followup_still_legal=sum(c['observed_followup'].get('followup_still_legal',False) for c in cases))
    (BASE/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
