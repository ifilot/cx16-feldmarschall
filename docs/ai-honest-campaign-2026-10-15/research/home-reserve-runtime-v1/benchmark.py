"""C21 public screening-only timing and selected-action eligibility; no games."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from campaign_flag_guard import position_from_public
from campaign_home_reserve import evaluate
OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent/'home-miner-interceptor-v1'/'result.json.gz'


def main():
    data=json.loads(gzip.decompress(SOURCE.read_bytes()))
    counts=Counter();selected_reasons=Counter();timings=[];eligible_timings=[];opportunities=[]
    for index,row in enumerate(data['screened_known_Miner_roots']):
        cells=bytes.fromhex(row['public_board_hex']);army=row['army'];shuttle=row['shuttle_hex']
        position=position_from_public(cells,army,shuttle)
        selected=tuple(row['selected'])
        # Actual historical chosen action only; original score vectors absent.
        # Artificial scores expose whether that selected action fails the gate.
        moves={move:1.0 if move==selected else 0.0 for move in position.moves(army)}
        before=time.perf_counter_ns();changes,report=evaluate(cells,army,[],{},moves,shuttle)
        elapsed=(time.perf_counter_ns()-before)/1e6
        timings.append(elapsed);counts[report['reason']]+=1
        if 'candidates'in report:eligible_timings.append(elapsed)
        if changes.get(selected,0)<0:
            selected_row=report['candidates'][f'{selected[0]}:{selected[1]}']
            selected_reasons[selected_row['reason']]+=1
            opportunities.append(dict(game=row['game'],ply=row['ply'],army=army,selected=list(selected),
                eventual_own_Flag_loss=row['eventual_own_Flag_loss'],eventual_captor_known_here=row['eventual_captor_known_here'],
                current_routes=report['current_routes'],repair_moves=report['repair_moves'],
                selected_schedule_reason=selected_row['reason'],selected_actor_safe=selected_row['actor_safe']))
        if(index+1)%2000==0:print('inspected',index+1,flush=True)
    def timing(values):
        ordered=sorted(values)
        return dict(count=len(values),mean_ms=statistics.mean(values),median_ms=statistics.median(values),
                    p95_ms=ordered[int(.95*(len(ordered)-1))],max_ms=max(values)) if values else None
    result=dict(kind='completed-C21-screening-public-runtime-preflight',roots=len(timings),reason_counts=counts,
        timing=timing(timings),full_candidate_evaluation_timing=timing(eligible_timings),
        selected_action_reasons=selected_reasons,
        selected_action_opportunity_roots=len(opportunities),selected_action_opportunity_games=len({r['game']for r in opportunities}),
        opportunity_loss_games=len({r['game']for r in opportunities if r['eventual_own_Flag_loss']}),
        opportunities=opportunities,
        method='No original native score vector was saved in this audit input. All legal moves receive0 except actual historical selected action1. Selected-action opportunities mean chosen quiet action fails while a certified quiet alternative exists; these are not exact native ranking replays, changed outcomes or strength estimates.',
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        module_sha256=hashlib.sha256((ROOT/'tools/campaign_home_reserve.py').read_bytes()).hexdigest(),
        limitations='Screened-known-Miner subset only, not all game roots or a fresh cohort; host Python timings, not CX16 target cost.')
    (OUT/'benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='opportunities'},indent=2))


if __name__=='__main__':main()
