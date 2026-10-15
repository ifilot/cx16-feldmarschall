"""Describe actual scouting and conditional follow-ups in the retained games."""
from collections import Counter
import json

from build_ai_diagnostics import permitted_view
from feldmarschall import Position, SCOUT, battle
from linked_scouting_cycle import BASE, plan
from review_linked_scouting import opportunities
from tournament_store import Tournament


def analyze():
    config=plan();actors={config['candidate'],config['baseline']}
    stats={actor:Counter() for actor in actors};examples=[];example_counts=Counter();divergences=[];followups=[]
    for path in sorted((BASE/'tournaments').rglob('*.fmtour')):
        with Tournament(path) as tournament:
            assert tournament.metadata()['status']=='complete'
            for row in tournament.games():
                game=tournament.game(row['id']);position=Position();lost=[[0]*12,[0]*12];pending={}
                for army in (0,1):position.place(army,game['red_setup' if army==0 else 'blue_setup'])
                for actor in (game['red'],game['blue']):
                    if actor in actors:stats[actor]['games']+=1
                for ply,(src,dst) in enumerate(game['moves']):
                    army=ply%2;identity=game['red' if army==0 else 'blue']
                    moving,target=position.cells[src],position.cells[dst]
                    if army in pending:
                        previous=pending.pop(army);counter=stats[identity]
                        beneficiaries=previous['beneficiaries']
                        target_present=position.cells[previous['target']] is previous['target_piece']
                        legal=position.moves(army)
                        available=target_present and any((a,previous['target']) in legal and
                                  position.cells[a] is piece for a,piece in beneficiaries)
                        counter['valued_probe_followup_still_legal']+=available
                        taken=available and any(src==a and dst==previous['target'] for a,_ in beneficiaries)
                        favorable=available and any((a,previous['target']) in legal and position.cells[a] is piece and
                            battle(piece[1],previous['target_piece'][1])=='attacker' for a,piece in beneficiaries)
                        counter['valued_probe_followup_taken']+=taken
                        counter['favorable_followups_available']+=favorable
                        counter['favorable_followups_taken']+=favorable and taken
                        counter['unfavorable_followups_available']+=available and not favorable
                        counter['unfavorable_followups_declined']+=available and not favorable and not taken
                        counter['valued_probe_defender_left_target']+=not target_present
                        counter['valued_probe_all_beneficiaries_lost']+=not any(position.cells[a] is piece for a,piece in beneficiaries)
                        previous['record'].update(next_own_ply=ply,actual_next_move=[src,dst],
                            defender_still_at_target=target_present,followup_still_legal=available,
                            favorable_followup=favorable,followup_taken=taken)
                    if identity in actors and moving[1]==SCOUT and target is not None:
                        counter=stats[identity];counter['scout_attacks']+=1
                        if target[3]:
                            counter['disclosed_losing_scout_attacks']+=battle(SCOUT,target[1])=='defender'
                        else:
                            counter['concealed_scout_attacks']+=1
                            info=permitted_view(position,army,lost)
                            ops=[o for o in opportunities(dict(input=info,legal_moves=position.moves(army))) if o['target']==dst]
                            counter['concealed_scout_attacks_with_valued_followup']+=bool(ops)
                            if ops and battle(SCOUT,target[1])=='defender':
                                counter['valued_probe_scout_losses']+=1
                                record=dict(tournament=str(path.relative_to(BASE)),game=game['id'],ply=ply,
                                    identity=identity,move=[src,dst],opportunities=ops,disclosed_rank_after_probe=target[1])
                                followups.append(record)
                                pending[army]=dict(target=dst,target_piece=target,
                                    beneficiaries=[(o['beneficiary'],position.cells[o['beneficiary']]) for o in ops],record=record)
                                if example_counts[identity]<12:
                                    example_counts[identity]+=1
                                    examples.append(dict(tournament=str(path.relative_to(BASE)),game=game['id'],ply=ply,
                                        identity=identity,move=[src,dst],opportunities=ops))
                    if target is None:position.move(src,dst)
                    else:
                        _,fallen=position.fight(src,dst,moving[1],target[1])
                        for side,rank,_,_ in fallen:lost[side][rank]+=1
                for army,previous in pending.items():
                    identity=game['red' if army==0 else 'blue']
                    stats[identity]['valued_probe_game_ended_before_next_turn']+=1
                    previous['record']['game_ended_before_next_turn']=True
    for stage in ('development','validation'):
        folder=BASE/f'tournaments/{stage}-league'
        for path in sorted(folder.glob('*.fmtour')):
            other=BASE/f'tournaments/{stage}-control'/path.name.replace(config['candidate'],config['baseline'])
            with Tournament(path) as a,Tournament(other) as b:
                for row in a.games():
                    ga,gb=a.game(row['id']),b.game(row['id'])
                    assert ga['red_setup']==gb['red_setup'] and ga['blue_setup']==gb['blue_setup']
                    first=next((ply for ply,(ma,mb) in enumerate(zip(ga['moves'],gb['moves'])) if ma!=mb),None)
                    if first is None:
                        assert ga['moves']==gb['moves']
                        continue
                    assert ga['red' if first%2==0 else 'blue']==config['candidate']
                    position=Position()
                    for army in (0,1):position.place(army,ga['red_setup' if army==0 else 'blue_setup'])
                    for src,dst in ga['moves'][:first]:
                        moving,target=position.cells[src],position.cells[dst]
                        if target is None:position.move(src,dst)
                        else:position.fight(src,dst,moving[1],target[1])
                    assert any(position.cells[move[0]][1]==SCOUT for move in (ga['moves'][first],gb['moves'][first]))
                    divergences.append(dict(tournament=str(path.relative_to(BASE)),game=ga['id'],ply=first,
                        candidate_move=list(ga['moves'][first]),baseline_move=list(gb['moves'][first])))
    return dict(scope='Observational public-root opportunity counts, not causal estimates. Legal follow-up means at least one credited beneficiary remains at its recorded square and can attack the same surviving defender on the next own turn. Favorable means winning immediate combat only; it ignores recapture, flag defense and alternative moves. Declining does not prove a mistake.',
                actors={actor:dict(counter) for actor,counter in sorted(stats.items())},
                first_divergences=len(divergences),divergence_examples=divergences[:24],valued_probe_examples=examples,
                all_valued_probe_loss_followups=followups)


if __name__=='__main__':
    result=analyze()
    (BASE/'activity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['actors'],indent=2))
