"""Fixed public-prefix opportunity audit; never runs a policy or new game."""
import hashlib,json,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from campaign_template_beliefs import TemplateMixtureBeliefs
from campaign_native_beliefs import quantize
from feldmarschall import Position,GLYPHS,LAKES,setup_squares,square_name
from tournament_store import Tournament
from risk import quiet_corrections

COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
POLICY='student-template-flag-bomb-v1-normal'
SELECTED=set(range(0,141,20))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def public(position,army,model):
    cells=[];histories={}
    for sq,cell in enumerate(position.cells):
        if cell is None:cells.append(254 if sq in LAKES else 255);continue
        owner,rank,moved,revealed=cell
        cells.append((rank if owner==army or revealed else 12)|16*owner|32*revealed|64*moved)
        if owner!=army and not revealed:
            token=model.tokens[sq]
            histories[sq]=[0,0,setup_squares(owner)[token[1]],1023 if moved else 4095]
    return cells,histories

def run():
    rows=[];counts=Counter();durations=[];checks=0
    with Tournament(COHORT) as tournament:
        games=[tournament.game(row['id'])for row in tournament.games()[:16]]
    for game in games:
        army=int(game['blue']==POLICY)
        assert game[('red','blue')[army]]==POLICY
        model=TemplateMixtureBeliefs();model.observe(['new',('red','blue')[army]])
        model.observe(['setup',game[('red_setup','blue_setup')[army]]])
        position=Position()
        for owner in(0,1):position.place(owner,game[('red_setup','blue_setup')[owner]])
        own_index=0
        for ply,(source,target)in enumerate(game['moves']):
            if ply%2==army:
                if own_index in SELECTED:
                    cells,histories=public(position,army,model);start=time.perf_counter()
                    marginals,remaining=model.rank_marginals(cells,army,model.lost,histories)
                    flag,bomb,_,_=quantize(marginals,remaining)
                    moves=position.moves(army)
                    correction=quiet_corrections(cells,army,model.lost,remaining,marginals,flag,bomb,moves)
                    elapsed=time.perf_counter()-start;durations.append(elapsed)
                    quiet=[r for r in correction if not r['capture']]
                    counts['roots']+=1;counts['quiet_moves']+=len(quiet);counts['captures_zero']+=len(correction)-len(quiet)
                    summary={}
                    for label,key in(('occupancy','occupancy_delta'),('mobile_total','mobile_delta'),('mobile_extra','mobile_vs_occupancy_delta')):
                        values=[r[key]for r in quiet]
                        spread=max(values,default=0)-min(values,default=0)
                        summary[label]=dict(nonzero=sum(v!=0 for v in values),minimum=min(values,default=0),maximum=max(values,default=0),spread=spread)
                        counts[label+'_roots_nonzero']+=any(values)
                        counts[label+'_roots_nonuniform']+=spread!=0
                        counts[label+'_moves_nonzero']+=sum(v!=0 for v in values)
                    for before,after,label in(('native','occupancy','occupancy'),('occupancy','mobile','mobile_extra')):
                        changed=0;strict_reversals=0;pairs=0
                        for i,a in enumerate(quiet):
                            for b in quiet[i+1:]:
                                x=a['pressure'][before]-b['pressure'][before];y=a['pressure'][after]-b['pressure'][after]
                                pairs+=1;changed+=(x>0)-(x<0)!=(y>0)-(y<0);strict_reversals+=x*y<0
                        summary[label].update(pairwise_comparisons=pairs,changed_pairwise_signs=changed,strict_reversals=strict_reversals)
                        counts[label+'_roots_pairwise_changed']+=changed>0
                        counts[label+'_roots_strict_reversal']+=strict_reversals>0
                    if len(rows)<12:
                        mutated=[(cell&240)|((sq*7+5)%12)if cell<254 and bool(cell&16)!=bool(army)and not cell&32 else cell for sq,cell in enumerate(cells)]
                        other,rem=model.rank_marginals(mutated,army,model.lost,histories)
                        assert other==marginals and rem==remaining
                        assert quiet_corrections(mutated,army,model.lost,rem,other,flag,bomb,moves)==correction
                        checks+=1
                    _,posterior=model.posterior()
                    rows.append(dict(game=game['id'],army=army,ply=ply,own_decision=own_index,quiet_moves=len(quiet),captures=len(correction)-len(quiet),channels=summary,posterior=posterior,elapsed_ms=elapsed*1000,corrections=correction))
                own_index+=1
            assert(source,target)in position.moves(ply%2)
            attacker,defender=position.cells[source],position.cells[target]
            words=['moved',square_name(source),square_name(target)]if defender is None else['battle',square_name(source),square_name(target),GLYPHS[attacker[1]],GLYPHS[defender[1]]]
            model.observe(words)
            if defender is None:position.move(source,target)
            else:position.fight(source,target,attacker[1],defender[1])
    sources=[Path(__file__),Path(__file__).with_name('risk.py'),Path(__file__).with_name('PROTOCOL.json'),ROOT/'tools/campaign_template_beliefs.py',ROOT/'tools/campaign_native_beliefs.py',ROOT/'tools/campaign_belief_values.py',ROOT/'src/core/ai.c',ROOT/'tools/feldmarschall.py']
    return dict(kind='fixed-public-prefix-component-feasibility',strength_evidence=False,cohort=str(COHORT.relative_to(ROOT)),cohort_sha256=sha(COHORT),selected_games=[g['id']for g in games],selection='first16 ids, own decision indices0,20,40,60,80,100,120,140; no replacement',counts=dict(counts),private_nibble_invariance_roots=checks,timing_ms=dict(mean=1000*sum(durations)/len(durations),maximum=1000*max(durations),includes='marginals+Q12quantization+all legal quiet danger channels; Python research implementation, no native search'),sources={str(p.relative_to(ROOT)):sha(p)for p in sources},roots=rows)
if __name__=='__main__':
    out=Path(__file__).with_name('result.json');out.write_text(json.dumps(run(),indent=2)+'\n');print(out)
