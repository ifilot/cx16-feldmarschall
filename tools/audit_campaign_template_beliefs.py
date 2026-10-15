"""Check fixed template provenance and public posterior algebra without saved games."""
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import time

from campaign_dos_deployment import EXPECTED,SOURCE_COMMIT,TEMPLATE_OFFSET,load_assets,templates
from campaign_template_beliefs import TEMPLATES,TemplateMixtureBeliefs,background_log_evidence
from feldmarschall import COUNTS,GLYPHS,setup_squares
from msdos1990 import FELD_RANK

ROOT=Path(__file__).resolve().parents[1]


def audit():
    assets=ROOT/'ai/msdos1990';setup=ROOT/'docs/ai-honest-campaign-2026-10-15/research/dos-deployment-original-v1'
    original=templates(assets,setup);canonical=[]
    for row in original[4:]:
        for mirror in (False,True):
            canonical.append(''.join(GLYPHS[FELD_RANK[row[10*r+c]]] for r in range(3,-1,-1)
                                     for c in (range(9,-1,-1) if mirror else range(10))))
    assert tuple(canonical)==TEMPLATES
    counts=(2,1,1);worlds=set(itertools.permutations((0,0,1,2)));cases=0;maxerror=0.
    for K in range(4):
        for origins in itertools.combinations(range(4),K):
            for ranks in itertools.product(range(3),repeat=K):
                known=dict(zip(origins,ranks))
                remaining=[o for o in range(4) if o not in known]
                for M in range(len(remaining)+1):
                    for moved in itertools.combinations(remaining,M):
                        exact=sum(all(w[o]==r for o,r in known.items()) and all(w[o]<2 for o in moved) for w in worlds)/len(worlds)
                        observed=math.exp(background_log_evidence(known,set(moved),counts,2))
                        maxerror=max(maxerror,abs(exact-observed));assert abs(exact-observed)<1e-14
                        cases+=1
    m=TemplateMixtureBeliefs();m.observe(['new','red']);m.observe(['setup',''.join(g*n for g,n in zip(GLYPHS,COUNTS))])
    cells=[255]*100;histories={}
    for sq,(owner,origin) in m.tokens.items():
        cells[sq]=owner*16+(m.known[owner,origin] if owner==0 else 12)
        if owner:
            history=[0]*11;history[2]=setup_squares(owner)[origin];history[-1]=4095;histories[sq]=history
    rng=random.Random(1987);start=time.perf_counter();batches=1000
    for _ in range(batches):m.sample_worlds(cells,[0]*12,histories,rng,0,8)
    sampling=(time.perf_counter()-start)/batches;start=time.perf_counter()
    for _ in range(batches):m.rank_marginals(cells,0,[0]*12,histories)
    marginal=(time.perf_counter()-start)/batches
    weights,report=m.posterior()
    files=['tools/campaign_template_beliefs.py','tools/test_campaign_template_beliefs.py','tools/audit_campaign_template_beliefs.py']
    return dict(kind='pinned-public-template-mixture-correctness',strength_evidence=False,passed=True,
                source_repository='https://github.com/ifilot/stratego-decompilation',source_commit=SOURCE_COMMIT,
                pinned_original_assets=EXPECTED,template_memory_location=dict(dgroup='1fe5',offset=hex(TEMPLATE_OFFSET),table_indices=[4,5,6,7]),
                canonical_templates=canonical,provenance_matches_runtime=True,
                background_exact_enumeration_cases=cases,background_likelihood_maximum_absolute_error=maxerror,
                initial_component_probabilities=weights,initial_posterior_report=report,
                initial_eight_world_sampling_mean_seconds=sampling,initial_rank_marginals_mean_seconds=marginal,
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})

if __name__=='__main__':
    out=ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-mixture-correctness.json'
    out.write_text(json.dumps(audit(),indent=2)+'\n')
