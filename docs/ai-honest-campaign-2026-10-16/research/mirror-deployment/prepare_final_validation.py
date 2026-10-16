"""Prepare the prospectively declared C119 branch; never launch games.

Requires complete audited C117/C118 and explicit parent authorization. The
immutable protocol fixes both the winner-selection and no-positive fallback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=HERE.parents[3]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(parent_authorized=False):
    protocol_path=HERE/'FINAL-VALIDATION-PROTOCOL.json'
    protocol=json.loads(protocol_path.read_text())
    assert sha(__file__)==protocol['plan_generator_sha256']
    if not parent_authorized:raise ValueError('Parent authorization is required before preparing a final-stage plan')
    source={}
    for key in ('dos_screen','honest_screen'):
        directory=ROOT/protocol[key]['directory']
        assert sha(directory/'plan.json')==protocol[key]['plan_sha256']
        audit=json.loads((directory/'audit.json').read_text());assert audit['passed']
        result=json.loads((directory/'result.json').read_text())
        assert result['attempts']==audit['attempts']==result['verified_games']
        manifest=json.loads((directory/'manifest.json').read_text())
        actual={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name!='manifest.json'}
        assert set(manifest)==actual
        for name,value in manifest.items():assert sha(directory/name)==value,name
        for path in directory.glob('*.fmtour'):
            report=json.loads(path.with_suffix('.report.json').read_text())
            assert report['tournament_sha256']==sha(path)
        source[key]=dict(directory=str(directory.relative_to(ROOT)),result=result,
                         result_sha256=sha(directory/'result.json'),audit_sha256=sha(directory/'audit.json'))
    ranking=[]
    for identity in protocol['candidate_order']:
        key=identity+' minus '+protocol['baseline']
        comparison=source['dos_screen']['result']['comparisons'][key]
        mean=comparison['metrics']['score']['mean'] if comparison is not None else None
        ranking.append(dict(policy=identity,primary_paired_mean=mean))
    positive=[r for r in ranking if r['primary_paired_mean'] is not None and r['primary_paired_mean']>0]
    selected=max(positive,key=lambda r:r['primary_paired_mean'])['policy'] if positive else None
    branch='improvement-validation' if selected else 'unchanged-best-score-replication'
    identities=[protocol['baseline'],selected] if selected else [protocol['baseline']]
    directory=BASE/('cycle-119-mirror-independent-dos-validation' if selected else 'cycle-119-best-policy-dos-replication')
    if directory.exists():raise FileExistsError(directory)
    import sys
    sys.path.insert(0,str(ROOT/'tools'))
    from ai_registry import get_policy
    for identity in [*identities,protocol['opponent']]:
        assert get_policy(identity)==protocol['frozen_policies'][identity]
    plan=dict(cycle=119,baseline=protocol['baseline'],opponent=protocol['opponent'],policies=identities,
        new_policies=[],seed=protocol['final_seed'],rounds=protocol['paired_rounds'],jobs=protocol['jobs'],
        max_plies=protocol['max_plies'],backend='openmp',families=['original-dos'],setup_mode='policy-owned-rotated-v1',
        hypotheses=([f'Independent fresh-cohort test of the unchanged screen-selected orientation policy {selected} against the unchanged Fortress-template reference.'] if selected else
                    ['Fresh fixed-sample replication of the unchanged Fortress-template best policy to estimate DOS score stability; not an improvement comparison.']),
        contrasts=[[selected,protocol['baseline']]] if selected else [],
        analysis=('Fresh fixed independent DOS-specific validation. One prespecified paired95% primary score contrast plus finite all-planned-pair missing-score bounds. No tuning, sample extension, favorable-result stopping, promotion, general honest-superiority or hardware-fit claim.' if selected else
                  'Fresh fixed single-policy replication estimating score stability against DOS. No improvement hypothesis, paired treatment contrast, pooling with historical/current scores, favorable-result stopping, promotion, general honest-superiority or hardware-fit claim.'),
        final_stage_branch=branch,selection_protocol_sha256=sha(protocol_path),
        evidence='research/mirror-deployment/FINAL-VALIDATION-PROTOCOL.json; both source screens complete and audited before activation. C112/C113 outcomes play no role in selection or source tuning.')
    decision=dict(protocol_sha256=sha(protocol_path),prepared_epoch=time.time(),parent_authorized=True,
        branch=branch,selected_policy=selected,ranking=ranking,source_audits={k:{x:y for x,y in v.items() if x!='result'} for k,v in source.items()},
        plan_sha256=hashlib.sha256((json.dumps(plan,indent=2)+'\n').encode()).hexdigest())
    directory.mkdir()
    (directory/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (directory/'selection.json').write_text(json.dumps(decision,indent=2)+'\n')
    (directory/'checks.log').write_bytes((ROOT/protocol['dos_screen']['directory']/'checks.log').read_bytes())
    return dict(directory=str(directory.relative_to(ROOT)),branch=branch,selected_policy=selected,
                planned_attempts=2*protocol['paired_rounds']*len(identities),games_launched=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-authorized',action='store_true')
    args=parser.parse_args();print(json.dumps(prepare(args.parent_authorized),indent=2))
