"""Frozen native-policy opening lookup feasibility and procedural calibration."""
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import secrets
import shlex
import shutil
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import get_policy
from campaign_template_beliefs import TEMPLATES,TemplateMixtureBeliefs
from campaign_dos_deployment import generate_setup,EXPECTED
from feldmarschall import Engine,GLYPHS,parse_square,square_name
from msdos1990 import OriginalAI
from analyze_campaign_template_predictions import saved_seeds
OUT=Path(__file__).resolve().parent;V2=OUT.parent/'template-action-identification-v2'
sys.path.insert(0,str(V2))
from audit_prefixes import emit_public
POLICY='student-validated-deployment-v1-normal'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def public_prediction(model):
    components,_=model.posterior()
    known={o:r for(owner,o),r in model.known.items()if owner==1}
    moved={o for owner,o in model.moved if owner==1}
    known_flag=[o for o,r in known.items()if r==11]
    sites=known_flag or[o for o in range(40)if o not in known and o not in moved]
    assert sites
    background=[1/len(sites)if o in sites else 0. for o in range(40)]
    probabilities=[components[-1]*p for p in background]
    for t,w in zip(TEMPLATES,components[:-1]):probabilities[t.index('F')]+=w
    assert abs(sum(probabilities)-1)<1e-10
    return dict(component_weights=components,background_Flag=background,hard_Flag=probabilities,
        compatible=[i for i,w in enumerate(components[:-1])if w],
        known_enemy_origins={str(o):r for o,r in known.items()},moved_enemy_origins=sorted(moved),enemy_lost=model.lost[:])


def trajectory(own,enemy,dos_seed,own_seed,program):
    ai=OriginalAI(ROOT/'ai/msdos1990',1,[own,enemy],seed=dos_seed,level=3)
    model=TemplateMixtureBeliefs();model.observe(['new','red']);model.observe(['setup',own]);transcript=[];rows=[]
    bot=Engine(shlex.quote(str(program))+' --difficulty normal')
    try:
        for line in('new red','rules 0','seed '+str(own_seed),'setup '+own):bot.send(line)
        bot.ask('isready','readyok')
        for step in range(1,5):
            selected=bot.ask('go','move')
            if selected=='none':break
            move=tuple(map(parse_square,selected.split()))
            assert move in ai.position.moves(0)
            terminal=emit_public(ai,model,transcript,move);bot.send(' '.join(transcript[-1]))
            if terminal:break
            before=public_prediction(model)
            enemy_move=ai.choose()
            if enemy_move is None:break
            terminal=emit_public(ai,model,transcript,enemy_move);bot.send(' '.join(transcript[-1]))
            rows.append(dict(step=step,transcript=[w[:]for w in transcript],before_enemy=before,**public_prediction(model)))
            if terminal:break
        return rows,None
    except Exception as exc:
        return rows,dict(error=repr(exc),public_prefix=transcript)
    finally:bot.close()


def prefix_key(row):return json.dumps(row['transcript'],separators=(',',':'))


def lookup(training,row):
    # Lookup never receives truth label, branch or either RNG seed.
    counts=Counter(r['template']for r in training if prefix_key(r)==prefix_key(row))
    base=row['component_weights'];fg=sum(base[:-1]);comp=row['compatible']
    weights=[counts[t]+1 if t in comp else 0 for t in range(8)];total=sum(weights)
    posterior=[fg*w/total if total else 0 for w in weights]+[base[-1]]
    probs=[base[-1]*p for p in row['background_Flag']]
    for template,w in zip(TEMPLATES,posterior[:-1]):probs[template.index('F')]+=w
    assert abs(sum(probs)-1)<1e-9
    return probs,sum(counts.values()),posterior


def score(p,flag):
    maximum=max(p);tops=[i for i,w in enumerate(p)if abs(w-maximum)<1e-14]
    accuracy=1/len(tops)if flag in tops else 0.
    return dict(logloss_nats=-math.log(max(p[flag],1e-300)),brier=sum((w-float(i==flag))**2 for i,w in enumerate(p)),
                top_tie_accuracy=accuracy,confidence=maximum,confident_wrong=float(maximum>=.8 and accuracy==0.),
                true_Flag_probability=p[flag])


def analyze(rows):
    results={};scored=[]
    for name in sorted({r['formation']for r in rows}):
        for step in range(1,5):
            subset=[r for r in rows if r['formation']==name and r['step']==step]
            train=[r for r in subset if r['split']=='training']
            for row in[r for r in subset if r['split']=='heldout']:
                prediction,support,components=lookup(train,row)
                hard=score(row['hard_Flag'],row['truth_Flag']);action=score(prediction,row['truth_Flag'])
                scored.append(dict(formation=name,step=step,branch=row['branch'],case=row['case'],
                    prefix_support=support,foreground_compatible=len(row['compatible']),background_probability=row['component_weights'][-1],
                    hard=hard,action=action,Flag_logscore_gain_bits=(hard['logloss_nats']-action['logloss_nats'])/math.log(2),
                    predictions_differ=any(abs(a-b)>1e-14 for a,b in zip(row['hard_Flag'],prediction))))
    for branch in('template','procedural','all'):
        results[branch]={}
        for step in range(1,5):
            group=[r for r in scored if r['step']==step and(branch=='all'or r['branch']==branch)]
            def means(label):return {k:sum(r[label][k]for r in group)/len(group)for k in group[0][label]}
            calibration={}
            for label in('hard','action'):
                bins=[]
                for lo,hi in zip((0.,.25,.5,.75,.9),(.25,.5,.75,.9,1.0000001)):
                    b=[r[label]for r in group if lo<=r[label]['confidence']<hi]
                    bins.append(dict(lower=lo,upper=min(1.,hi),count=len(b),
                        mean_confidence=sum(r['confidence']for r in b)/len(b)if b else None,
                        mean_top_accuracy=sum(r['top_tie_accuracy']for r in b)/len(b)if b else None))
                calibration[label]=bins
            results[branch][str(step)]=dict(samples=len(group),supported_prefixes=sum(r['prefix_support']>0 for r in group),
                changed_predictions=sum(r['predictions_differ']for r in group),background_only=sum(r['foreground_compatible']==0 for r in group),
                mean_background_probability=sum(r['background_probability']for r in group)/len(group),
                hard=means('hard'),action=means('action'),
                Flag_logscore_gain_bits=sum(r['Flag_logscore_gain_bits']for r in group)/len(group),
                calibration=calibration)
    return results,scored


def main():
    previous=json.loads((V2/'config.json').read_text());excluded,files=saved_seeds()
    excluded.update(previous['dos_private_research_rng'])
    dos=[]
    while len(dos)<40:
        s=secrets.randbelow(65535)+1
        if s not in excluded and s not in dos:dos.append(s)
    own=[]
    while len(own)<40:
        s=secrets.randbits(32)
        if s not in excluded and s not in dos and s not in own:own.append(s)
    deployment=[]
    while len(deployment)<512:
        s=secrets.randbits(32)
        if s not in excluded and s not in dos and s not in own and s not in deployment:deployment.append(s)
    policy=get_policy(POLICY);built=ROOT/'build/ai-catalog'/POLICY/'engine'
    receipt=json.loads(built.with_name('build.json').read_text())
    assert receipt['policy']==policy and receipt['executable_sha256']==digest(built)
    assert digest(ROOT/policy['archive'])==policy['source_sha256']
    sources=[Path(__file__),V2/'audit_prefixes.py',ROOT/'tools/msdos1990.py',ROOT/'tools/campaign_template_beliefs.py',ROOT/'tools/campaign_joint_beliefs.py',ROOT/'tools/campaign_dos_deployment.py']
    config=dict(hypothesis='Does full-prefix lookup retain predictive gain/coverage under frozen native play, including exact procedural-branch calibration?',
        frozen_before_sampling=True,policy=policy,native_runtime_sha256=digest(built),
        templates=list(TEMPLATES),own_formations=previous['own_formations'],DOS_private_research_rng=dos,
        native_own_private_research_rng=own,private_deployment_candidates=deployment,
        template_trajectories=256,procedural_trajectories=32,max_DOS_decisions=4,max_DOS_queries=1152,
        split='Template RNG indices0..3 train,4..7 heldout; BOTH DOS and own native RNG are distinct across splits.32 exact procedural branch armies are entirely heldout. Heldout160 trajectories form80%template/20%procedural.',
        native_inputs='Frozen normal native student policy receives own forced army, independent own RNG, rules and public actual events only. No enemy setup, private DOS RNG, template identity or generation receipt.',
        contexts='Four fixed existing own formations, DOSBlue after ownRed actual native move; no generalization over all own armies or DOSRed claimed.',
        generator='Try frozen512 independent private32-bit original-generator seeds in order, accept first32 with receipt.branch original-procedural. Never infer branch from template nonmembership. No move outcomes select deployments.',
        predictor='Train fixed add-one exact COMPLETE-prefix frequency classifier on template trajectories only, per formation/step. Redistribute only existing compatible template foreground mass. Preserve hard-evidence background probability and its exact uniform-count conditional Flag distribution. Unseen prefix is exact hard baseline; no fitted procedural/action likelihood or0.8prior change.',
        proper_scores='Flag categorical logloss in nats and summed40-origin Brier; report separately by true generator branch and pooled80/20heldout. High-confidence wrong means maxFlag>=0.8 and trueFlag not top. Fixed confidence bins0,.25,.5,.75,.9,1.',
        primary='Heldout Flag log-score gain versus full-history hard baseline at decisions1–4; report full-prefix support and confident errors. Per-step cumulative gains must not be added.',
        excluded_saved_files=files,excluded_saved_seed_count=len(excluded),assets_sha256=EXPECTED,
        source_sha256={str(p.relative_to(ROOT)):digest(p)for p in sources})
    path=OUT/'config.json'
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(config,indent=2)+'\n')
    rows=[];errors=[];generation=[];procedural=[];started=time.perf_counter()
    assets=ROOT/'ai/msdos1990';setup_assets=ROOT/'docs/ai-honest-campaign-2026-10-15/research/dos-deployment-original-v1'
    for seed in deployment:
        army,audit=generate_setup(assets,seed,level=3,setup_assets=setup_assets)
        generation.append(dict(seed=seed,branch=audit['branch'],setup_sha256=hashlib.sha256(army.encode()).hexdigest()))
        if audit['branch']=='original-procedural':procedural.append(dict(setup=army,audit=audit))
        if len(procedural)==32:break
    assert len(procedural)==32
    (OUT/'generation-evidence.json').write_text(json.dumps(dict(attempts=generation,selected=procedural),indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='feld-template-v3-')as temporary:
        program=Path(temporary)/'native';shutil.copyfile(built,program);program.chmod(0o755);assert digest(program)==config['native_runtime_sha256']
        for f,(name,formation)in enumerate(config['own_formations'].items()):
            cases=[dict(case=f'T{t}-R{k}',branch='template',template=t,enemy=template,
                dos_seed=dos[k],own_seed=own[k],split='training'if k<4 else'heldout')
                for t,template in enumerate(TEMPLATES)for k in range(8)]
            cases += [dict(case=f'P{f*8+j}',branch='procedural',template=None,enemy=procedural[f*8+j]['setup'],
                dos_seed=dos[8+f*8+j],own_seed=own[8+f*8+j],split='heldout')for j in range(8)]
            for case in cases:
                data,error=trajectory(formation,case['enemy'],case['dos_seed'],case['own_seed'],program)
                if error:errors.append(dict(formation=name,case=case['case'],**error))
                for row in data:rows.append(dict(formation=name,case=case['case'],branch=case['branch'],
                    template=case['template'],split=case['split'],truth_Flag=case['enemy'].index('F'),**row))
            print('Completed',name,flush=True)
    summaries,scored=analyze(rows)
    result=dict(kind='frozen-native-prefix-lookup-feasibility-v3',strength_evidence=False,model_tuned=False,
        config_sha256=digest(path),elapsed_seconds=time.perf_counter()-started,decisions=len(rows),errors=errors,
        generation_attempts=len(generation),procedural_armies=len(procedural),summaries=summaries,scored_rows=scored,raw_rows=rows)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(seconds=result['elapsed_seconds'],decisions=len(rows),errors=errors,
        summary={b:{s:{k:v[k]for k in('samples','supported_prefixes','changed_predictions','background_only','Flag_logscore_gain_bits')}for s,v in summaries[b].items()}for b in summaries}),indent=2))


if __name__=='__main__':main()
