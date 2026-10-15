"""Research-only inverse DOS first-action identification; no policy/tournaments.

Only eight fixed public source templates and four pre-existing own formations
are passed to the original engine. Every move RNG seed is independently sampled
for this experiment and is never read from an observed match.
"""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import secrets
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from campaign_template_beliefs import TEMPLATES
from feldmarschall import Position, GLYPHS, setup_squares, valid_setup
from msdos1990 import OriginalAI
from analyze_campaign_template_predictions import saved_seeds

OUT=Path(__file__).resolve().parent
FORMATIONS=ROOT/'docs/ai-honest-campaign-2026-10-15/research/deployment-double-shell/geometry-and-history.json'
NAMES=('Fortress','Evolved2','Evolved3','DoubleShellFortress')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def first_own_quiet(own):
    # Our own army plus initial public enemy occupancy; no enemy hidden ranks.
    p=Position();p.place(0,own);p.place(1,TEMPLATES[0],known=False)
    return next(move for move in p.moves(0) if p.cells[move[1]] is None)


def action_event(own, template, seed, side=1, first_own=True):
    """Generate one legal opening prefix; own full rank access is legitimate.

    Side0 is a separate actual first-player context, with no prior own move.
    Side1 is conditioned on the public quiet first move selected using own
    ranks and initial public occupancy only.
    """
    setups=[None,None];setups[side]=template;setups[1-side]=own
    start=time.perf_counter();ai=OriginalAI(ROOT/'ai/msdos1990',side,setups,seed=seed,level=3)
    prefix=None
    if first_own:
        assert side==1
        prefix=first_own_quiet(own);ai.observe(*prefix)
    move=ai.choose();assert move is not None
    src,dst=move;target=ai.position.cells[dst]
    origin=setup_squares(side).index(src)
    rank=GLYPHS.index(template[origin])
    long=abs(src//10-dst//10)+abs(src%10-dst%10)>1
    revealed=rank if target or long else None
    # Keep absolute coordinates: every classifier context fixes side/formation.
    event=(src,dst,revealed)
    return dict(move=list(move),origin=origin,revealed_rank=revealed,
                battle=bool(target),first_own_move=list(prefix)if prefix else None,
                seconds=time.perf_counter()-start,event=list(event))


def compatibility(row, templates=TEMPLATES):
    origin=row['origin'];revealed=row['revealed_rank']
    return tuple(i for i,t in enumerate(templates)
                 if GLYPHS.index(t[origin])<10 and
                 (revealed is None or GLYPHS.index(t[origin])==revealed))


def entropy(probs):return -sum(p*math.log2(p)for p in probs if p)


def empirical_information(rows):
    n=len(rows);ta=Counter((r['template'],tuple(r['event']))for r in rows)
    t=Counter(r['template']for r in rows);a=Counter(tuple(r['event'])for r in rows)
    tm=Counter((r['template'],tuple(r['compatible']))for r in rows)
    am=Counter((tuple(r['event']),tuple(r['compatible']))for r in rows)
    m=Counter(tuple(r['compatible'])for r in rows)
    tam=Counter((r['template'],tuple(r['event']),tuple(r['compatible']))for r in rows)
    mutual=sum(v/n*math.log2(v*n/(t[key[0]]*a[key[1]]))for key,v in ta.items())
    conditional=sum(v/n*math.log2(v*m[mask]/(tm[(typ,mask)]*am[(act,mask)]))for(typ,act,mask),v in tam.items())
    return dict(plugin_template_action_mi_bits=mutual,
                plugin_template_action_conditional_mi_given_compatibility_mask_bits=conditional,
                distinct_actions=len(a),samples=n,
                warning='Finite-sample plug-in information, upward biased; not a predictive or strength estimate.')


def predict(training, event, compatible):
    # Fixed add-one discriminative frequency classifier. No parameter search.
    # We do NOT claim an exact normalized Bayesian original-engine likelihood.
    counts=Counter((r['template'],tuple(r['event']))for r in training)
    weight=[counts[i,tuple(event)]+1 if i in compatible else 0 for i in range(8)]
    total=sum(weight);assert total>0
    return [w/total for w in weight]


def flag_probs(weights,templates=TEMPLATES):
    result=defaultdict(float)
    for t,p in zip(templates,weights):result[t.index('F')]+=p
    return dict(result)


def summarize(rows):
    training=[r for r in rows if r['split']=='training'];test=[r for r in rows if r['split']=='heldout']
    heldout=[]
    for r in test:
        comp=r['compatible'];hard=[1/len(comp)if i in comp else 0 for i in range(8)]
        action=predict(training,r['event'],comp);fp=flag_probs(action);hp=flag_probs(hard)
        flag=TEMPLATES[r['template']].index('F')
        top=max(fp.values());tops=[f for f,p in fp.items()if abs(p-top)<1e-14]
        htop=max(hp.values());htops=[f for f,p in hp.items()if abs(p-htop)<1e-14]
        heldout.append(dict(template=r['template'],rng_index=r['rng_index'],event=r['event'],
            compatible=comp,hard_flag_entropy_bits=entropy(hp.values()),action_flag_entropy_bits=entropy(fp.values()),
            flag_logscore_gain_bits=math.log2(fp[flag]/hp[flag]),
            template_logscore_gain_bits=math.log2(action[r['template']]/hard[r['template']]),
            action_top_flag_tie_accuracy=1/len(tops)if flag in tops else 0.,
            hard_top_flag_tie_accuracy=1/len(htops)if flag in htops else 0.,
            action_flag_posterior=fp,hard_flag_posterior=hp))
    keys=('hard_flag_entropy_bits','action_flag_entropy_bits','flag_logscore_gain_bits',
          'template_logscore_gain_bits','action_top_flag_tie_accuracy','hard_top_flag_tie_accuracy')
    return dict(all_samples_information=empirical_information(rows),training_samples=len(training),heldout_samples=len(test),
                heldout_means={k:sum(r[k]for r in heldout)/len(heldout)for k in keys},heldout=heldout)


def audit():
    excluded,files=saved_seeds();rng_seeds=[]
    while len(rng_seeds)<8:
        seed=secrets.randbelow(65535)+1
        if seed not in excluded and seed not in rng_seeds:rng_seeds.append(seed)
    formations=json.loads(FORMATIONS.read_text())['existing_and_candidate_layouts']
    own={name:formations[name]['setup']for name in NAMES}
    assert all(valid_setup(s)for s in own.values())
    config=dict(templates=list(TEMPLATES),own_formations=own,private_research_move_rng_seeds=rng_seeds,
        seed_contract='Eight independently sampled16-bit OriginalAI constructor seeds, excluded from all currently saved tournament move seeds. Shared across hypotheses as common random numbers; never a seed of an observed actual game.',
        excluded_saved_files=files,excluded_saved_seed_count=len(excluded),
        split='First4 prespecified RNG indices train; last4 heldout. Fixed add-one frequency classifier, no fitting on saved game cohorts.',
        dos_side=1,first_player='honestRed first legal quiet move in existing Position.moves order; only own ranks and initial public occupancy used',
        calls=256,source_sha256={str(p.relative_to(ROOT)):digest(p)for p in
            (Path(__file__),ROOT/'tools/msdos1990.py',ROOT/'tools/campaign_template_beliefs.py',FORMATIONS)})
    config_path=OUT/'config.json'
    if config_path.exists():raise FileExistsError('Preserve prior experiment/config')
    config_path.write_text(json.dumps(config,indent=2)+'\n')
    rows=[]
    for name,formation in own.items():
        for t,template in enumerate(TEMPLATES):
            for k,seed in enumerate(rng_seeds):
                row=dict(formation=name,template=t,rng_index=k,split='training'if k<4 else'heldout',
                         **action_event(formation,template,seed))
                row['compatible']=list(compatibility(row));assert t in row['compatible'];rows.append(row)
        print('completed',name,flush=True)
    summaries={name:summarize([r for r in rows if r['formation']==name])for name in own}
    timings=[r['seconds']for r in rows]
    result=dict(kind='source-template-inverse-first-action-research',strength_evidence=False,model_tuning=False,
                config_sha256=digest(config_path),raw_rows=rows,summaries=summaries,
                timing_seconds=dict(total=sum(timings),mean=sum(timings)/len(timings),maximum=max(timings)),
                limitations=['Template component only; procedural20% background is not modeled by this classifier.',
                    'Known DOS action model retains its original own knowledge of our Flag/Spy; our own full army is legitimate private information.',
                    'Compatibility baseline includes revealed battle rank and long-range Scout disclosure, not just mobility.',
                    'Heldout RNG values are new but share source templates/own formations; this is not heldout army generalization.',
                    'Only DOSBlue after a public first own quiet move is measured. DOSRed moves first and needs a separately conditioned action model.',
                    'Plugin MI is biased and classifier entropy reduction alone does not establish useful or calibrated information.',
                    'No policy, runtime lookup, model source or saved match changed.'])
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(timing=result['timing_seconds'],summaries={k:v['heldout_means']for k,v in summaries.items()}),indent=2))


if __name__=='__main__':audit()
