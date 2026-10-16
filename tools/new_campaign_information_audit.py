"""Public-event activation audit on a named, previously screened cohort only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from campaign_template_beliefs import TemplateMixtureBeliefs
from new_campaign_information import MissedCaptureBeliefs
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tournament',type=Path)
    parser.add_argument('--games',type=int,default=100)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--background',action='store_true')
    args=parser.parse_args()
    if 'screen' not in str(args.tournament) or 'validation' in str(args.tournament):
        raise ValueError('activation audit requires an explicitly screened, non-validation cohort')
    totals=Counter();changed=[];elapsed=0.
    with Tournament(args.tournament) as tour:
        rows=[row for row in tour.games() if row['result']!='error'][:args.games]
        for row in rows:
            game=tour.game(row['id']);states,_=replay(game)
            events=public_events(game,states)
            for army in (0,1):
                if args.background:
                    from new_campaign_information_background import MissedCaptureRankBeliefs,background_row,condition_background
                    model=MissedCaptureRankBeliefs()
                else:model=MissedCaptureBeliefs()
                model.observe(['new',('red','blue')[army]])
                model.observe(['setup',game[('red_setup','blue_setup')[army]]])
                seen=False;different=False;packet_checked=False
                for event in events:
                    started=time.perf_counter();model.observe(event.split())
                    weights,_=model.posterior();elapsed+=time.perf_counter()-started
                    baseline,_=TemplateMixtureBeliefs.posterior(model)
                    totals['public_events']+=1
                    if model.miss:
                        totals['active_events']+=1;seen=True
                    delta=max(abs(a-b) for a,b in zip(weights,baseline))
                    if args.background and model.miss:
                        counts,U,moved=model.context();origin=model.miss['origin']
                        original=background_row(counts,U,origin in moved)
                        started=time.perf_counter()
                        focal,_,_=condition_background(counts,U,origin in moved,model.likelihood)
                        elapsed+=time.perf_counter()-started
                        before=[baseline[-1]*p+sum(w for w,t in zip(baseline[:-1],model.templates) if t[origin]==rank) for rank,p in enumerate(original)]
                        after=[weights[-1]*p+sum(w for w,t in zip(weights[:-1],model.templates) if t[origin]==rank) for rank,p in enumerate(focal)]
                        delta=max(abs(after[r]-before[r]) for r in (10,11))
                        if delta>1e-12:totals['changed_flag_bomb_events']+=1
                    if delta>1e-12:
                        different=True;totals['changed_contact_marginal_events' if args.background else 'changed_posterior_events']+=1
                        if args.background and not packet_checked:
                            from feldmarschall import LAKES,setup_squares
                            from campaign_native_beliefs import quantize
                            cells=[254 if s in LAKES else 255 for s in range(100)];histories={}
                            for sq,token in model.tokens.items():
                                rank=model.known.get(token);is_moved=token in model.moved
                                cells[sq]=token[0]*16+(12 if rank is None else rank)+64*is_moved+32*(token in model.disclosed or token[0]!=army and rank is not None)
                                if token[0]!=army and rank is None:
                                    histories[sq]=[0,0,setup_squares(token[0])[token[1]],0,0,int(is_moved),1023 if is_moved else 4095]
                            base=TemplateMixtureBeliefs();base.__dict__.update(model.__dict__)
                            prior,remaining=base.rank_marginals(cells,army,model.lost,histories)
                            adjusted,rest=model.rank_marginals(cells,army,model.lost,histories)
                            assert remaining==rest
                            packet_a=quantize(prior,remaining)[3];packet_b=quantize(adjusted,remaining)[3]
                            totals['whole_q12_packet_checks']+=1
                            totals['changed_whole_q12_packets']+=packet_a!=packet_b
                            totals['packet_checks_moved_clue' if origin in moved else 'packet_checks_unmoved_clue']+=1
                            packet_checked=True
                        if len(changed)<20:changed.append(dict(game=game['id'],army=army,ply=model.plies,
                            maximum_flag_bomb_marginal_delta=delta if args.background else None,
                            maximum_weight_delta=None if args.background else delta,observation=model.miss.copy()))
                totals['side_histories']+=1;totals['histories_with_evidence']+=seen
                totals['histories_with_changed_contact_marginals' if args.background else 'histories_with_changed_posterior']+=different
    doc=dict(kind='public-screen-activation-only',tournament=str(args.tournament),
        source_sha256=hashlib.sha256(args.tournament.read_bytes()).hexdigest(),
        selection='first complete game IDs, both armies; fixed before inspection',games=len(rows),
        counts=dict(totals),examples=changed,background_conditioning=args.background,host_observe_and_posterior_seconds=elapsed,
        seconds_per_public_event=elapsed/max(1,totals['public_events']),
        limitation='No move choices or strength estimate. Events disclose battle ranks only; each model receives its own setup. Old screening histories are development evidence only.')
    args.out.write_text(json.dumps(doc,indent=2)+'\n');print(json.dumps(doc))


if __name__=='__main__':main()
