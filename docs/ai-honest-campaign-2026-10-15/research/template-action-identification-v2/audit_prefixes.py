"""Frozen bounded public-prefix action-identification experiment, research only."""
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import secrets
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from campaign_template_beliefs import TEMPLATES,TemplateMixtureBeliefs
from feldmarschall import Position,GLYPHS,square_name
from msdos1990 import OriginalAI
from analyze_campaign_template_predictions import saved_seeds
OUT=Path(__file__).resolve().parent
V1=OUT.parent/'template-action-identification'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def own_public_moves(position,army=0):
    p=Position();p.shuttle=dict(position.shuttle)
    p.cells=[None if c is None else c[:]for c in position.cells]
    for c in p.cells:
        if c and c[0]!=army and not c[3]:c[1]=12
    return p.moves(army)


def emit_public(ai,tracker,transcript,move):
    src,dst=move;a,d=ai.position.cells[src],ai.position.cells[dst]
    if d:
        words=['battle',square_name(src),square_name(dst),GLYPHS[a[1]],GLYPHS[d[1]]]
        terminal=d[1]==11
        ai.observe(src,dst,a[1],d[1])
    else:
        words=['moved',square_name(src),square_name(dst)];terminal=False;ai.observe(src,dst)
    tracker.observe(words);transcript.append(words)
    return terminal


def hard_state(tracker):
    posterior,_=tracker.posterior()
    compatible=[i for i,p in enumerate(posterior[:-1])if p>0]
    assert compatible
    return dict(compatible=compatible,
        known_enemy_origins={str(origin):rank for(owner,origin),rank in tracker.known.items()if owner==1},
        moved_enemy_origins=sorted(origin for owner,origin in tracker.moved if owner==1),
        enemy_lost=tracker.lost[:])


def trajectory(own,template,dos_seed,own_seed):
    ai=OriginalAI(ROOT/'ai/msdos1990',1,[own,template],seed=dos_seed,level=3)
    model=TemplateMixtureBeliefs();model.observe(['new','red']);model.observe(['setup',own])
    own_rng=random.Random(own_seed);transcript=[];rows=[]
    for step in range(1,5):
        legal=own_public_moves(ai.position)
        if not legal:break
        if emit_public(ai,model,transcript,own_rng.choice(legal)):break
        before=hard_state(model)
        move=ai.choose()
        if move is None:break
        terminal=emit_public(ai,model,transcript,move)
        rows.append(dict(step=step,transcript=[w[:]for w in transcript],
            before_enemy_action_hard=before,**hard_state(model)))
        if terminal:break
    return rows


def flag_posterior(weights):
    probs=defaultdict(float)
    for t,w in zip(TEMPLATES,weights):probs[t.index('F')]+=w
    return dict(probs)


def key(row):return json.dumps(row['transcript'],separators=(',',':'))


def classify(training,row):
    # One classifier of COMPLETE public prefixes, not a product of move scores.
    # Identical prior paths are counted once per independent trajectory.
    counts=Counter(r['template']for r in training if key(r)==key(row))
    comp=row['compatible'];weights=[counts[t]+1 if t in comp else 0 for t in range(8)]
    total=sum(weights)
    return [w/total for w in weights],sum(counts.values())


def summarize(rows):
    result={}
    for step in range(1,5):
        subset=[r for r in rows if r['step']==step]
        train=[r for r in subset if r['split']=='training'];test=[r for r in subset if r['split']=='heldout']
        scores=[]
        for r in test:
            comp=r['compatible'];hard=[1/len(comp)if t in comp else 0 for t in range(8)]
            action,support=classify(train,r);hp=flag_posterior(hard);ap=flag_posterior(action)
            flag=TEMPLATES[r['template']].index('F')
            def entropy(probs):return-sum(p*math.log2(p)for p in probs.values()if p)
            def top_accuracy(probs):
                high=max(probs.values());ties=[f for f,p in probs.items()if abs(p-high)<1e-14]
                return 1/len(ties)if flag in ties else 0.
            scores.append(dict(template=r['template'],rng_index=r['rng_index'],training_prefix_support=support,
                flag_logscore_gain_bits=math.log2(ap[flag]/hp[flag]),
                template_logscore_gain_bits=math.log2(action[r['template']]/hard[r['template']]),
                hard_flag_entropy_bits=entropy(hp),action_flag_entropy_bits=entropy(ap),
                hard_top_flag_accuracy=top_accuracy(hp),action_top_flag_accuracy=top_accuracy(ap)))
        fields=['flag_logscore_gain_bits','template_logscore_gain_bits','hard_flag_entropy_bits',
                'action_flag_entropy_bits','hard_top_flag_accuracy','action_top_flag_accuracy']
        result[str(step)]=dict(training=len(train),heldout=len(test),
            supported_heldout_prefixes=sum(r['training_prefix_support']>0 for r in scores),
            means={f:sum(r[f]for r in scores)/len(scores)for f in fields},scores=scores)
    return result


def main():
    previous=json.loads((V1/'config.json').read_text());excluded,files=saved_seeds()
    dos_seeds=[]
    while len(dos_seeds)<8:
        s=secrets.randbelow(65535)+1
        if s not in excluded and s not in previous['private_research_move_rng_seeds']and s not in dos_seeds:dos_seeds.append(s)
    own_seeds={name:secrets.randbits(64)for name in previous['own_formations']}
    sources=[Path(__file__),ROOT/'tools/msdos1990.py',ROOT/'tools/campaign_template_beliefs.py',ROOT/'tools/campaign_joint_beliefs.py']
    config=dict(hypothesis='Cumulative passive template identification from2nd–4th DOS actions beyond ALL public rank/movement facts.',
        frozen_before_queries=True,v1_result_sha256=digest(V1/'result.json'),
        templates=list(TEMPLATES),own_formations=previous['own_formations'],dos_private_research_rng=dos_seeds,
        own_private_research_rng_by_formation=own_seeds,trajectories=256,max_DOS_decisions=4,max_total_move_queries=1024,
        rules='Classic; original Colonel level3; DOSBlue follows ownRed',
        own_policy='Uniform random among legal public moves using own ranks and enemy occupancy/revealed ranks only; one independent own RNG seed per formation, reset for each hypothetical trajectory as common random numbers.',
        split='DOS RNG indices0..3 training,4..7 heldout. Own-policy RNG is controlled/fixed per formation and not a heldout generalization axis.',
        baseline='Uniform source-template foreground conditioned on ALL historical public origin/rank/mobility facts, retaining captured disclosures.',
        classifier='Fixed add-one COMPLETE-public-prefix frequency classifier, independently per formation/decision step. Exact unseen prefix gives uniform hard posterior. No sequential multiplication, independent-action assumption or parameter search.',
        primary_endpoint='Heldout cumulative Flag log-score gain beyond full hard posterior at each of decisions1,2,3,4; diagnostic only, no strength claim.',
        orientation='DOSRed first-player sequences not modeled; do not infer full orientation generalization from Blue sequences.',
        exclusions=dict(saved_files=files,saved_move_seeds=len(excluded)),source_sha256={str(p.relative_to(ROOT)):digest(p)for p in sources})
    path=OUT/'config.json'
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(config,indent=2)+'\n')
    rows=[];start=time.perf_counter()
    for name,own in config['own_formations'].items():
        for t,template in enumerate(TEMPLATES):
            for k,seed in enumerate(dos_seeds):
                for row in trajectory(own,template,seed,own_seeds[name]):
                    assert t in row['compatible']
                    rows.append(dict(formation=name,template=t,rng_index=k,
                        split='training'if k<4 else'heldout',**row))
        print('Completed',name,flush=True)
    result=dict(kind='bounded-sequential-public-prefix-template-identification-v2',strength_evidence=False,model_tuned=False,
        config_sha256=digest(path),elapsed_seconds=time.perf_counter()-start,enemy_decisions=len(rows),
        summaries={name:summarize([r for r in rows if r['formation']==name])for name in config['own_formations']},raw_rows=rows,
        limits=['Template foreground only; procedural20% not modeled.','Exact-prefix frequency diagnostic is not a calibrated source likelihood.','Four own RNG contexts are controlled and shared across training/test; only DOS RNG values are held out.','No policy/source changes, saved matches, actual match seeds or validation observations enter fitting.'])
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(seconds=result['elapsed_seconds'],decisions=len(rows),
        means={name:{s:v['means']for s,v in summaries.items()}for name,summaries in result['summaries'].items()}),indent=2))


if __name__=='__main__':main()
