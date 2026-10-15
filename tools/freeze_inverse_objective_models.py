"""Reproduce v1 conditional geometry assets solely from preserved development fits."""
import copy
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from ai_registry import ROOT
from belief_experiment import rows

DIRECTORY=ROOT/'docs/ai-honest-campaign-2026-10-15/research/inverse-objectives'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    candidates=json.loads((DIRECTORY/'model-candidates.json').read_text())
    selection=json.loads((DIRECTORY/'development-selection.json').read_text())
    corpus=ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.jsonl.gz'
    partitions=defaultdict(lambda:dict(games=set(),pairs=set()))
    for row in rows(corpus):
        partitions[row['partition']]['games'].add(row['game']);partitions[row['partition']]['pairs'].add(row['pair'])
    files=[corpus,corpus.with_name('development.fmtour'),ROOT/'ai/models/public-history-beliefs-v1.json',
           ROOT/'tools/research_inverse_objectives.py',ROOT/'tools/research_inverse_objective_sampling.py',
           ROOT/'tools/campaign_inverse_objectives.py',ROOT/'tools/calibrated_beliefs.py',
           DIRECTORY/'campaign_inverse_objectives.original.py',DIRECTORY/'model-candidates.json',
           DIRECTORY/'development-selection.json',DIRECTORY/'sampling-followup.json']
    provenance=dict(scope='Historical development only. Never campaign validation or fresh outcomes.',
        observer_filter='Only own side opposite msdos-1990-v2-normal; fit labels only moved concealed enemy mobile ranks.',
        partitions={part:{key:sorted(values) for key,values in fields.items()} for part,fields in partitions.items()},
        training_views=1498,calibration_views=660,training_moved_labels=6857,calibration_moved_labels=2756,
        fitting='Train partition only; each piece weighted by inverse number of views of its game; rank-conditional categorical tables; alpha=10 pooled-frequency smoothing.',
        calibration_selection='Same old whole-pair calibration partition; choose feature group and strength by game-weighted approximate fractional moved-rank log loss. Flag strength .5 selected on grid [0,.125,.25,.5,1]; Spy strength0 rejected. These are development selections, not unbiased validation.',
        control='Mirrored file objectives have separately fitted tables using identical training recipe. Control uses SAME Flag feature indices [0,1,2] and SAME real-selected strength .5; no independent control-strength selection.',
        bounds='Extra log factor clipped to +/-.75; resulting old+extra log likelihood clipped to +/-2. Unmoved and immobile ranks retain old factors. Exact public counts/masks preserved; 8-world importance estimate remains approximate.',
        interpretation='Conditional public geometry, not causal inverse planning. Real vs mirrored calibration intervals include zero; both outperform baseline descriptively.',
        empirical_source_sha256=selection['module_sha256'],
        files={str(path.relative_to(ROOT)):sha(path) for path in files},
        primary_sources=selection['primary_sources'],
        limitations=['DOS-specific training may not generalize to honest heads.',
                      'Own Flag and own Spy are legitimate private inputs. Enemy hidden nibbles and enemy setup are never features.',
                      'Only Flag features [0,1,2] active; Spy-only gamma0 rejection and all grid/control predictions preserved.'])
    for mirrored,name,key in [(False,'own-flag-motion-beliefs-v1','flag'),(True,'mirrored-own-flag-motion-beliefs-v1','mirrored-control')]:
        document=copy.deepcopy(candidates[key]);document.update(model_id=name,version=1,
            factor_strength=.5,selected_features=[0,1,2],mirrored_control=mirrored,provenance=provenance)
        path=ROOT/'ai/models'/f'{name}.json'
        payload=json.dumps(document,indent=2)+'\n'
        if path.exists() and path.read_text()!=payload:raise RuntimeError(f'Immutable asset differs: {path}')
        if not path.exists():path.write_text(payload)
        print(name,sha(path))

if __name__=='__main__':main()
