"""Concise fixed-prior predictive results; no generator/model calls or tuning."""
import argparse
import hashlib
import json
from pathlib import Path


def summarize(path):
    data=json.loads(path.read_text());rows=[]
    for entry in data['aggregates']:
        branch=entry['branch'];K=entry['disclosures']
        group=[r for r in data['rows'] if r['disclosures']==K and (branch=='all' or r['branch']==branch)]
        confident=[r for r in group if r['template']['top_flag_probability']>=.5]
        wrong=[r for r in confident if not r['template']['flag_top_accuracy']]
        rows.append(dict(branch=branch,disclosures=K,armies=len(group),
            mixture_flag_logloss=entry['metrics']['template']['flag_logloss'],
            uniform_flag_logloss=entry['metrics']['uniform']['flag_logloss'],
            mixture_flag_brier=entry['metrics']['template']['flag_brier'],
            uniform_flag_brier=entry['metrics']['uniform']['flag_brier'],
            mixture_bomb_logloss=entry['metrics']['template']['bomb_logloss_per_original_slot'],
            uniform_bomb_logloss=entry['metrics']['uniform']['bomb_logloss_per_original_slot'],
            mixture_bomb_brier=entry['metrics']['template']['bomb_brier_per_original_slot'],
            uniform_bomb_brier=entry['metrics']['uniform']['bomb_brier_per_original_slot'],
            mixture_tie_adjusted_flag_top_accuracy=entry['metrics']['template']['flag_top_tie_adjusted_accuracy'],
            uniform_tie_adjusted_flag_top_accuracy=entry['metrics']['uniform']['flag_top_tie_adjusted_accuracy'],
            background_only_count=sum(r['background_only'] for r in group),
            flag_predictions_with_probability_at_least_half=len(confident),
            wrong_flag_predictions_with_probability_at_least_half=len(wrong),
            wrong_flag_high_confidence_rate=len(wrong)/len(group),
            conditional_error_when_high_confidence=len(wrong)/len(confident) if confident else None))
    return dict(kind='fixed-template-prediction-calibration-summary',source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                armies=data['armies'],branches=data['branches'],model_tuned=False,strength_evidence=False,
                interpretation=['Large predictive improvement on template branch; none of these metrics establishes stronger play.',
                                'The procedural branch demonstrates a real calibration hazard after one disclosure:9 of42 armies receive a wrong top Flag prediction with probability at least0.5.',
                                'After3 controlled disclosures all42 procedural armies reject every template and predictions equal uniform counts.',
                                'Use tie-adjusted top accuracy: deterministic lowest-index uniform ties never pick rear Flags in this cohort, so its raw0% top accuracy is a tie-rule artifact.',
                                'The raw audit field template_dominant_wrong_flag_rate means >0.5 TOTAL template mass on all other Flag sites combined; it is NOT the rate of confident wrong point predictions. Use the explicit high-confidence counts here.'],
                protocol=data['synthetic_observation_protocol'],metrics=data['metrics'],timings=data['timings'],rows=rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():raise FileExistsError('Preserve previous summary evidence')
    args.out.write_text(json.dumps(summarize(args.source),indent=2)+'\n')
