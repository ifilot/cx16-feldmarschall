"""Variant strength referee using actual C rules and audited permitted engine views."""
from collections import Counter

from feldmarschall import Engine, parse_square, square_name, GLYPHS
from variant_rules import VariantPosition


def play_variant(job):
    names,commands,setups,seed,max_plies,record_moves,rules,library=job
    truth=VariantPosition(rules,library);engines=[];moves=[];events=[];counts=Counter()
    winner=None;reason='';side=0;plies=0;view_checks=0
    try:
        for army in (0,1):
            engine=Engine(commands[army],names[army]);engines.append(engine)
            engine.send(f'seed {seed*2+army+1}');engine.send('rules '+str(rules))
            engine.send('new '+('red','blue')[army]);engine.send('setup '+setups[army])
            truth.place(army,setups[army])
        while True:
            for army,engine in enumerate(engines):
                actual=engine.ask('view','view');expected=truth.view(army)
                view_checks+=1
                if actual!=expected:raise ValueError(f'permitted-view mismatch at {plies}, army {army}: {actual} != {expected}')
            legal=truth.moves(side)
            if not legal:
                if truth.moves(1-side):winner,reason=1-side,'no moves'
                else:reason='neither can move'
                break
            if plies>=max_plies:reason='ply limit';break
            answer=engines[side].ask('go','move').split()
            try:move=tuple(map(parse_square,answer))
            except ValueError:move=None
            if move not in legal:winner,reason=1-side,'illegal move '+' '.join(answer);break
            src,dst=move;event,ending=truth.apply(src,dst)
            for engine in engines:engine.send(event)
            ply_events=[event];counts[event.split()[0]]+=1
            if event.startswith('combat') and event.split()[4]=='?':counts['hidden_defender']+=1
            moves.append([src,dst]);plies+=1
            if ending:winner,reason=side,ending
            else:
                rescued=truth.auto_rescue(dst)
                if rescued:
                    trigger,destination,rank,visible=rescued
                    own_event=f'reinforce {square_name(trigger)} {square_name(destination)} {GLYPHS[rank]} {int(visible)}'
                    other_event=f'reinforce {square_name(trigger)} {square_name(destination)} {GLYPHS[rank] if visible else "?"} {int(visible)}'
                    for army,engine in enumerate(engines):engine.send(own_event if army==side else other_event)
                    ply_events.append({'owner':side,'own':own_event,'opponent':other_event});counts['rescue']+=1
            events.append(ply_events)
            if ending:
                for army,engine in enumerate(engines):
                    assert engine.ask('view','view')==truth.view(army)
                    view_checks+=1
                break
            side=1-side
    finally:
        for engine in engines:engine.close()
    result={'red':names[0],'blue':names[1],'winner':None if winner is None else names[winner],
            'result':{None:'draw',0:'red',1:'blue'}[winner],'reason':reason,'plies':plies,'seed':seed,
            'rules':rules,'observations_audited':True,'view_checks':view_checks,'event_counts':dict(counts)}
    if record_moves:result.update(moves=moves,events=events)
    return result
