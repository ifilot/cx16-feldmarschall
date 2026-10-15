"""Post-audit mechanical first-player orientation control, not model fitting."""
import hashlib
import json
from pathlib import Path
from audit_opening_actions import OUT,TEMPLATES,action_event,compatibility,empirical_information


def mirror(s):return ''.join(s[k:k+10][::-1]for k in range(0,40,10))


def main():
    main_config=json.loads((OUT/'config.json').read_text())
    seed=main_config['private_research_move_rng_seeds'][0]
    templates=tuple(mirror(t)for t in TEMPLATES)
    own={name:mirror(formation)for name,formation in main_config['own_formations'].items()}
    config=dict(purpose='Additional mechanical first-player control after zero-increment main audit; no fitting, RNG generalization or symmetry equivalence claimed.',
                template_hypotheses=templates,own_formations=own,seed=seed,calls=32,dos_side=0,first_own_move=None,
                reflection='Horizontal row reflection of BOTH canonical armies creates physical180-degree counterpart under Position.setup_squares and OriginalAI.local.',
                reason='DOSRed moves first; DOSBlue main experiment instead observes a legal ownRed quiet first move. These are different conditioning contexts.',
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    config_path=OUT/'orientation-control-config.json'
    if config_path.exists():raise FileExistsError(config_path)
    config_path.write_text(json.dumps(config,indent=2)+'\n')
    rows=[]
    for name,formation in own.items():
        for t,template in enumerate(templates):
            row=dict(formation=name,template=t,**action_event(formation,template,seed,side=0,first_own=False))
            row['compatible']=list(compatibility(row,templates));assert t in row['compatible'];rows.append(row)
    result=dict(config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),raw_rows=rows,
                information_by_formation={name:empirical_information([r for r in rows if r['formation']==name])for name in own},
                timing_seconds=sum(r['seconds']for r in rows),
                scope='One independent research seed only; mechanical side/turn context check, not another fitted predictor or strength test.')
    (OUT/'orientation-control-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='raw_rows'},indent=2))


if __name__=='__main__':main()
