"""Frozen train/calibration/heldout source-structured background predictive study."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import secrets
import shutil
import sys
import tempfile
import time
from structural_model import ROOT,StructuralModel,fit_row_odds
sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import get_policy
from campaign_template_beliefs import TEMPLATES,background_log_evidence
from campaign_dos_deployment import generate_setup,EXPECTED
from feldmarschall import GLYPHS
from analyze_campaign_template_predictions import saved_seeds
V3=Path(__file__).resolve().parent.parent/'template-action-identification-v3';sys.path.insert(0,str(V3))
from audit_native_prefixes import trajectory,score
OUT=Path(__file__).resolve().parent
EPSILONS=(.01,.05,.10,.20,.50,1.)
POLICY='student-validated-deployment-v1-normal'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def predict(row,model,epsilon,with_bombs=False):
    """Public original identities/mobility only; no seed, army or truth input."""
    known={int(o):r for o,r in row['known_enemy_origins'].items()};moved=set(row['moved_enemy_origins'])
    log_uniform=background_log_evidence(known,moved)
    structural=model.predict(known,moved,with_bombs=with_bombs)
    logs=[math.log(.1)if i in row['compatible']else-math.inf for i in range(8)]
    logs += [math.log(.2*(1-epsilon))+structural['log_evidence']if epsilon<1 else-math.inf,
             math.log(.2*epsilon)+log_uniform]
    maximum=max(logs);weights=[math.exp(v-maximum)for v in logs];total=sum(weights);weights=[w/total for w in weights]
    flag=[weights[-1]*p for p in row['background_Flag']]
    for t,w in zip(TEMPLATES,weights[:8]):flag[t.index('F')]+=w
    if weights[-2]:
        for s,p in enumerate(structural['flag']):flag[s]+=weights[-2]*p
    assert abs(sum(flag)-1)<1e-9
    bomb=None
    if with_bombs:
        known_bombs={o for o,r in known.items()if r==10};eligible=set(range(40))-set(known)-moved
        uniform=[1. if s in known_bombs else(6-len(known_bombs))/len(eligible)if s in eligible else 0. for s in range(40)]
        bomb=[weights[-1]*p for p in uniform]
        for t,w in zip(TEMPLATES,weights[:8]):
            for s,g in enumerate(t):bomb[s]+=w*(g=='B')
        if weights[-2]:
            for s,p in enumerate(structural['bomb']):bomb[s]+=weights[-2]*p
        assert abs(sum(bomb)-6)<1e-8
    return dict(flag=flag,bomb=bomb,component_weights=weights,structural_log_evidence=structural['log_evidence'],uniform_log_evidence=log_uniform)


def trajectory_means(rows):
    groups=defaultdict(list)
    for row in rows:groups[row['formation'],row['branch'],row['case']].append(row)
    return[dict(formation=f,branch=b,case=c,delta=sum(r['delta_logloss_nats']for r in group)/len(group))for(f,b,c),group in groups.items()]


def primary(rows):
    means=trajectory_means(rows)
    forms=sorted({r['formation']for r in means});result=[]
    for f in forms:
        t=[r['delta']for r in means if r['formation']==f and r['branch']=='template']
        p=[r['delta']for r in means if r['formation']==f and r['branch']=='procedural']
        result.append(.8*sum(t)/len(t)+.2*sum(p)/len(p))
    return sum(result)/len(result)


def bootstrap(rows):
    means=trajectory_means(rows);forms=sorted({r['formation']for r in means});blocks={}
    for f in forms:
        t=defaultdict(list);p=[]
        for row in means:
            if row['formation']!=f:continue
            if row['branch']=='template':t[row['case'].split('-R')[1]].append(row['delta'])
            else:p.append(row['delta'])
        blocks[f]=([sum(v)/len(v)for v in t.values()],p)
    rng=random.Random(0xB6C41990);values=[]
    for _ in range(20000):
        total=0.
        for t,p in blocks.values():
            total+=.8*sum(rng.choice(t)for _ in t)/len(t)+.2*sum(rng.choice(p)for _ in p)/len(p)
        values.append(total/len(forms))
    values.sort();return dict(mean=primary(rows),interval_95=[values[499],values[19499]],replicates=20000,
        method='Formation-stratified paired bootstrap. Foreground resamples own/DOS RNG-context blocks containing all8fixedtemplates; procedural resamples independent full-generator armies. Equal4formations, fixed80/20component weights. Average each trajectory over its available decisions.')


def summarize(rows):
    result={}
    for branch in('template','procedural','all'):
        result[branch]={}
        for step in range(1,5):
            group=[r for r in rows if r['step']==step and(branch=='all'or r['branch']==branch)]
            result[branch][str(step)]=dict(samples=len(group),
                hard={k:sum(r['hard'][k]for r in group)/len(group)for k in group[0]['hard']},
                candidate={k:sum(r['candidate'][k]for r in group)/len(group)for k in group[0]['candidate']},
                mean_delta_logloss_nats=sum(r['delta_logloss_nats']for r in group)/len(group),
                hard_Bomb_brier=sum(r['hard_Bomb_brier']for r in group)/len(group),
                candidate_Bomb_brier=sum(r['candidate_Bomb_brier']for r in group)/len(group),
                calibration={name:[dict(lower=lo,upper=min(hi,1.),count=len(bucket),
                    confidence=sum(r[name]['confidence']for r in bucket)/len(bucket)if bucket else None,
                    accuracy=sum(r[name]['top_tie_accuracy']for r in bucket)/len(bucket)if bucket else None)
                    for lo,hi in zip((0.,.25,.5,.75,.9),(.25,.5,.75,.9,1.0000001))
                    for bucket in[[r for r in group if lo<=r[name]['confidence']<hi]]]for name in('hard','candidate')})
    return result


def evaluate(rows,model,epsilon):
    scores=[]
    for row in rows:
        candidate=predict(row,model,epsilon,with_bombs=True);baseline=predict(row,model,1.,with_bombs=True)
        for a,b in zip(baseline['flag'],row['hard_Flag']):assert abs(a-b)<1e-10
        hard=score(baseline['flag'],row['truth_Flag']);new=score(candidate['flag'],row['truth_Flag'])
        true_bombs=set(row['truth_Bombs'])
        scores.append(dict(formation=row['formation'],branch=row['branch'],case=row['case'],step=row['step'],
            hard=hard,candidate=new,delta_logloss_nats=new['logloss_nats']-hard['logloss_nats'],
            hard_Bomb_brier=sum((p-float(s in true_bombs))**2 for s,p in enumerate(baseline['bomb']))/40,
            candidate_Bomb_brier=sum((p-float(s in true_bombs))**2 for s,p in enumerate(candidate['bomb']))/40,
            posterior_components=candidate['component_weights']))
    return scores


def freeze():
    previous=json.loads((V3/'config.json').read_text());excluded,files=saved_seeds()
    for name in('DOS_private_research_rng','native_own_private_research_rng'):excluded.update((s&65535)or 1 for s in previous[name])
    for folder,key in[('template-action-identification','private_research_move_rng_seeds'),('template-action-identification-v2','dos_private_research_rng')]:
        excluded.update(json.loads((OUT.parent/folder/'config.json').read_text())[key])
    available=[s for s in range(1,65536)if s not in excluded];secrets.SystemRandom().shuffle(available)
    assert len(available)>192;cursor=0
    phases={}
    for phase in('calibration','heldout'):
        phases[phase]={}
        for kind,n in(('DOS_foreground',16),('native_foreground',16),('DOS_procedural',32),('native_procedural',32)):
            phases[phase][kind]=available[cursor:cursor+n];cursor+=n
    candidates={};used=set()
    for phase,n in(('training',2048),('calibration',512),('heldout',512)):
        pool=[]
        while len(pool)<n:
            seed=secrets.randbits(32)
            if seed>65535 and seed not in used and seed not in previous['private_deployment_candidates']:
                pool.append(seed);used.add(seed)
        candidates[phase]=pool
    spec=get_policy(POLICY);program=ROOT/'build/ai-catalog'/POLICY/'engine'
    receipt=json.loads(program.with_name('build.json').read_text());assert receipt['policy']==spec and digest(program)==receipt['executable_sha256']
    sources=[Path(__file__),OUT/'structural_model.py',V3/'audit_native_prefixes.py',OUT.parent/'template-action-identification-v2/audit_prefixes.py',ROOT/'tools/campaign_template_beliefs.py',ROOT/'tools/campaign_joint_beliefs.py',ROOT/'tools/msdos1990.py',ROOT/'tools/campaign_dos_deployment.py']
    config=dict(hypothesis='A source-screen procedural background improves calibrated public Flag prediction over uniform legal armies.',
        frozen_before_sampling=True,policy=spec,native_runtime_sha256=digest(program),own_formations=previous['own_formations'],
        contexts='Four fixed own formations, actual frozen nativeRed policy against originalDOSBlue Colonel. No generalization over allownarmies or bothorientations.',
        private_deployment_candidate_pools=candidates,independent_move_RNG=phases,
        seed_contract='All native/DOS move RNG inputs are unique16-bit states, disjoint across every role and calibration/heldout context and excluded from saved tournament seeds/prioraction studies. Independent original deployment states are fresh32-bit private states, separate pools byphase. No observedmatch seed is a model input.',
        procedural_targets=dict(training=128,calibration=32,heldout=32),
        template_trajectories_per_phase=128,template_sampling='Enumerate8fixedsourcehypotheses ×4fixedownformations ×4independentown/DOS RNGcontexts. Theyare fixed support, not128newtemplates.',
        source_model='12source Flag/screen geometries with priorsbackrowcolumn1/10, corners.2adjacent/.8outer. Exactcount residualBomb conditionalBernoulli weights. Uniformcountconditional mobileranks; rolelikelihoodmisspecification explicit.',
        training='Fit residualBomb rowodds using128proceduralarmies and fixed Beta(1,1) smoothing. No calibration/heldoutarmy enters fit; no whole-army particleposterior.',
        whole_prior='Exactly.8source-templateforeground +.2*((1-epsilon)*structural +epsilon*uniformlegalbackground). Epsilon1 reproducesoldmodel. Templateweight neverchanged.',
        epsilon_grid=list(EPSILONS),selection='Choose lowest properFlaglogloss on calibration160trajectories, meanpertrajectoryoveravailabledecisions then equal4formations/fixed80%template20%procedural. Ties within1e-12 preferlargest uniformtail. Freeze selection receipt before heldout move queries.',
        max_DOS_decisions=4,max_DOS_queries=1280,
        endpoints='PrimaryheldoutdeltaFlaglogloss_nats candidate-minusbaseline, pertrajectoryaverage. Also categoricalFlagBrier/topaccuracy/confidencebins and mean40originBombBrier. Capturedpublicranks retained; predictfrompublicoriginfacts only.',
        acceptance='Predictive acceptance only if selectedepsilon<1, primaryheldoutpaired95%bootstrapinterval entirelybelow0, proceduralmeanFlaglogloss nonworse and proceduralconfidentwrong count notincreased. OtherwiseDEFER. Alltemplate/proceduraltradeoffsreported. Evenacceptance requiresrootreview before runtime and doesnotestablishplayingstrength.',
        uncertainty='20,000formationstratified pairedbootstrap: foreground resamples own/DOS RNGcontextblocks that contain all8templates, proceduralresamplesindependentgeneratorarmies. Fourfixedformations/eighttemplates areboundedcontexts.',
        calibration_bins=[0.,.25,.5,.75,.9,1.],confident_wrong_threshold=.8,assets_sha256=EXPECTED,
        source_sha256={str(p.relative_to(ROOT)):digest(p)for p in sources},excluded_saved_files=files,excluded_move_seed_count=len(excluded))
    path=OUT/'protocol.json'
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(config,indent=2)+'\n');return config


def main():
    config=freeze();started=time.perf_counter();generations={};armies={}
    source=ROOT/'ai/msdos1990';assets=OUT.parent/'dos-deployment-original-v1'
    for phase,pool in config['private_deployment_candidate_pools'].items():
        selected=[];attempts=[];goal=config['procedural_targets'][phase]
        for seed in pool:
            setup,audit=generate_setup(source,seed,level=3,setup_assets=assets)
            attempts.append(dict(seed=seed,branch=audit['branch'],setup_sha256=hashlib.sha256(setup.encode()).hexdigest()))
            if audit['branch']=='original-procedural':selected.append(dict(setup=setup,audit=audit))
            if len(selected)==goal:break
        assert len(selected)==goal;generations[phase]=dict(attempts=attempts,selected=selected);armies[phase]=selected
        (OUT/'generation-evidence.json').write_text(json.dumps(generations,indent=2)+'\n')
        print('Generated',phase,len(selected),'from',len(attempts),flush=True)
    weights,fit=fit_row_odds([[GLYPHS.index(g)for g in row['setup']]for row in armies['training']])
    model=StructuralModel(weights=weights)
    training=dict(weights=weights,fit=fit,source_training_generation_sha256=digest(OUT/'generation-evidence.json'))
    (OUT/'trained-model.json').write_text(json.dumps(training,indent=2)+'\n')
    errors=[];datasets={};selected_epsilon=None
    built=ROOT/'build/ai-catalog'/POLICY/'engine'
    with tempfile.TemporaryDirectory(prefix='feld-procedural-prior-')as temp:
        program=Path(temp)/'native';shutil.copyfile(built,program);program.chmod(0o755);assert digest(program)==config['native_runtime_sha256']
        for phase in('calibration','heldout'):
            if phase=='heldout':assert(OUT/'calibration-selection.json').exists()
            rows=[];rng=config['independent_move_RNG'][phase]
            for f,(name,own)in enumerate(config['own_formations'].items()):
                cases=[dict(case=f'T{t}-R{k}',branch='template',enemy=template,
                    dos=rng['DOS_foreground'][f*4+k],native=rng['native_foreground'][f*4+k])for t,template in enumerate(TEMPLATES)for k in range(4)]
                cases +=[dict(case=f'P{f*8+k}',branch='procedural',enemy=armies[phase][f*8+k]['setup'],
                    dos=rng['DOS_procedural'][f*8+k],native=rng['native_procedural'][f*8+k])for k in range(8)]
                for case in cases:
                    data,error=trajectory(own,case['enemy'],case['dos'],case['native'],program)
                    if error:errors.append(dict(phase=phase,formation=name,case=case['case'],**error))
                    for row in data:rows.append(dict(phase=phase,formation=name,case=case['case'],branch=case['branch'],
                        truth_Flag=case['enemy'].index('F'),truth_Bombs=[s for s,g in enumerate(case['enemy'])if g=='B'],**row))
                print('Queried',phase,name,flush=True)
            datasets[phase]=rows;(OUT/(phase+'-public-prefixes.json')).write_text(json.dumps(rows,indent=2)+'\n')
            if phase=='calibration':
                grid=[]
                for epsilon in EPSILONS:
                    scores=evaluate(rows,model,epsilon);grid.append(dict(epsilon=epsilon,primary_delta=primary(scores)))
                minimum=min(r['primary_delta']for r in grid);selected_epsilon=max(r['epsilon']for r in grid if r['primary_delta']<=minimum+1e-12)
                selection=dict(epsilon=selected_epsilon,grid=grid,calibration_prefixes_sha256=digest(OUT/'calibration-public-prefixes.json'),
                    trained_model_sha256=digest(OUT/'trained-model.json'),frozen_before_heldout_move_queries=True)
                (OUT/'calibration-selection.json').write_text(json.dumps(selection,indent=2)+'\n')
                print('Selectedepsilon',selected_epsilon,flush=True)
    scores=evaluate(datasets['heldout'],model,selected_epsilon);summary=summarize(scores);interval=bootstrap(scores)
    procedural=[r for r in scores if r['branch']=='procedural'];proc_delta=sum(r['delta_logloss_nats']for r in procedural)/len(procedural)
    confident_hard=sum(r['hard']['confident_wrong']for r in procedural);confident_new=sum(r['candidate']['confident_wrong']for r in procedural)
    accepted=selected_epsilon<1 and interval['interval_95'][1]<0 and proc_delta<=0 and confident_new<=confident_hard and not errors
    result=dict(kind='frozen-source-structured-background-predictive-study',strength_evidence=False,protocol_sha256=digest(OUT/'protocol.json'),
        elapsed_seconds=time.perf_counter()-started,selected_epsilon=selected_epsilon,errors=errors,
        primary_delta_logloss=interval,procedural_delta_logloss=proc_delta,procedural_confident_wrong_counts=dict(hard=confident_hard,candidate=confident_new),
        acceptance_criteria_passed=accepted,decision='Predictiveacceptanceonly;rootreviewrequiredbeforeruntime'if accepted else'DEFER',summaries=summary,scored_rows=scores)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('summaries','scored_rows')},indent=2))


if __name__=='__main__':main()
