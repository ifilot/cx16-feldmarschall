"""Descriptive public-combat activation of inner-guard assignment, completed studies.

Reads own initial ranks, public piece ownership and ranks disclosed by actual
battles. No policy is run or updated. Counts cannot establish strength or the
counterfactual outcome of assigning a different guard.
"""
from collections import Counter
import hashlib,json
from pathlib import Path

from feldmarschall import GLYPHS,setup_squares
from tournament_store import Tournament,replay

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/ai-honest-campaign-2026-10-16/research/inner-guard'


def audit(path,policy):
    records=[];counts=Counter();armies=Counter()
    with Tournament(path) as tour:
        metadata=tour.metadata()
        assert metadata['status']=='complete' and metadata['rules']=='classic'
        assert metadata['setup_mode']=='policy-owned-rotated-v1'
        for row in tour.games():
            game=tour.game(row['id']);army=int(game['blue']==policy)
            assert game[('red','blue')[army]]==policy
            squares=setup_squares(army)
            index=lambda origin:origin//10*10+9-origin%10 if army else origin
            origin_at={squares[index(origin)]:origin for origin in range(40)}
            own_setup=game[('red_setup','blue_setup')[army]]
            own_initial_ranks={origin:GLYPHS.index(own_setup[index(origin)]) for origin in range(40)}
            gates={squares[index(origin)]:origin for origin in (20,31)}
            states,_=replay(game);armies[str(army)]+=1
            for ply,(source,target) in enumerate(game['moves']):
                before,after=states[ply],states[ply+1]
                actor,defender=before[source],before[target]
                own_move=actor[0]==army
                actor_origin=origin_at.get(source) if own_move else None
                if own_move:assert actor[1]==own_initial_ranks[actor_origin]
                is_capture=defender is not None
                enemy_rank=(defender[1] if own_move else actor[1]) if is_capture else None
                if own_move and is_capture and actor_origin==21 and enemy_rank==7:
                    survivor=after[target]
                    kept=survivor is not None and survivor[0]==army
                    counts['original_guard_attacks_disclosed_miner']+=1
                    counts['guard_survives_miner_capture' if kept else 'guard_exchanges_with_miner']+=1
                    record=dict(game=game['id'],family=game['family'],army=army,ply=ply,
                        own_origin=21,own_rank=actor[1],enemy_rank_disclosed_in_this_battle=7,
                        target_gate=gates.get(target),guard_survives=kept,kind='original-guard-versus-miner')
                    records.append(record)
                if own_move and is_capture and enemy_rank==7 and target in gates and ply:
                    previous_source,previous_target=game['moves'][ply-1]
                    prior=states[ply-1]
                    breached=(previous_target==target and prior[previous_source][0]!=army and
                              prior[target] is not None and prior[target][0]==army and prior[target][1]==10)
                    if breached:
                        survivor=after[target];kept=survivor is not None and survivor[0]==army
                        counts['immediate_inner_bomb_breach_recaptures']+=1
                        counts['immediate_breach_recapture_retains_piece' if kept else 'immediate_breach_recapture_exchanges']+=1
                        records.append(dict(game=game['id'],family=game['family'],army=army,ply=ply,
                            gate=gates[target],own_origin=actor_origin,own_rank=actor[1],
                            own_guard_origin21=actor_origin==21,guard_survives=kept,
                            kind='immediate-inner-bomb-breach-recapture'))
                # Maintain only OWN public identity. Battle survivor ownership
                # is public, even when no enemy rank was known before combat.
                if own_move:
                    token=origin_at.pop(source)
                    if after[target] is not None and after[target][0]==army:origin_at[target]=token
                elif target in origin_at and (after[target] is None or after[target][0]!=army):origin_at.pop(target)
            counts['games']+=1
            counts['error_prefixes']+=game['result']=='error'
    guard_events=[r for r in records if r['kind']=='original-guard-versus-miner']
    breach_events=[r for r in records if r['kind']=='immediate-inner-bomb-breach-recapture']
    counts['games_with_original_guard_miner_combat']=len({r['game'] for r in guard_events})
    counts['original_guard_miner_combats_at_inner_gate']=sum(r['target_gate'] is not None for r in guard_events)
    counts['games_with_immediate_breach_recapture']=len({r['game'] for r in breach_events})
    counts['immediate_breach_recaptures_by_original_guard']=sum(r['own_guard_origin21'] for r in breach_events)
    return dict(policy=policy,tournament=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        counts=dict(counts),games_by_army=dict(armies),events=records)


def main():
    results=[]
    for cycle in (110,111):
        directory=next((ROOT/'docs/ai-honest-campaign-2026-10-16').glob('cycle-'+str(cycle)+'*'))
        plan=json.loads((directory/'plan.json').read_text())
        for policy in plan['policies']:results.append(dict(cycle=cycle,**audit(directory/(policy+'.fmtour'),policy)))
    doc=dict(scope='Post-hoc descriptive activation on completed C110/C111 only; no parameter selection, new games or strength inference',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results=results,
        limitations=['Own armies differ intentionally between policies; these are not identical-root causal activation comparisons.',
            'Combat ranks are consumed only when an actual battle discloses them; no concealed pre-battle rank is used.',
            'An origin21 guard may leave the post. These counts follow its identity rather than assuming it remained stationary.',
            'Immediate breach recaptures may be performed by other defenders; survival is observed only, without counterfactual conversion claims.',
            'Saved engine-error prefixes are included and identified; absent future events are not inferred.'])
    (OUT/'natural-recaptures-C110-C111.json').write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='events'} for r in results]))


if __name__=='__main__':main()
