"""Separate public replay and split review of v2; no secret-rank board input."""
import hashlib
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_template_beliefs import TemplateMixtureBeliefs,TEMPLATES
from feldmarschall import Position,GLYPHS,parse_square
V2=Path(__file__).resolve().parent.parent/'template-action-identification-v2'


def main():
    config=json.loads((V2/'config.json').read_text());result=json.loads((V2/'result.json').read_text())
    prefixes=0;own_actions=0;captured=0
    for row in result['raw_rows']:
        own=config['own_formations'][row['formation']]
        model=TemplateMixtureBeliefs();model.observe(['new','red']);model.observe(['setup',own])
        p=Position();p.place(0,own);p.place(1,TEMPLATES[0],known=False)
        rng=random.Random(config['own_private_research_rng_by_formation'][row['formation']])
        for ply,words in enumerate(row['transcript']):
            src,dst=map(parse_square,words[1:3])
            if ply%2==0:
                assert (src,dst)==rng.choice(p.moves(0));own_actions+=1
            if words[0]=='battle':
                ar,dr=map(GLYPHS.index,words[3:]);p.fight(src,dst,ar,dr)
            else:p.move(src,dst)
            model.observe(words)
        comp=[i for i,t in enumerate(TEMPLATES)if all(GLYPHS.index(t[o])==rank
            for(owner,o),rank in model.known.items()if owner==1)and all(t[o]not in'BF'for owner,o in model.moved if owner==1)]
        assert row['compatible']==comp
        live=set(model.tokens.values());captured+=sum(owner==1 and token not in live for token in model.known for owner in[token[0]])
        assert row['enemy_lost']==model.lost;prefixes+=1
    report=dict(passed=True,scope='Separate public replay/split review by same research agent; not a third-party review.',
        full_prefixes_checked=prefixes,own_random_choices_reconstructed_from_public_board=own_actions,
        captured_enemy_disclosures_retained_across_prefixes=captured,
        first_action_negative_scope='v1 fixed first own move only; does not contradict v2 positive in other first-own-action contexts.',
        qualifications=['Only DOS RNG is held out in v2; own RNG is fixed per formation.','Four fixed own armies and eight known templates are controlled contexts, not heldout army generalization.','All sampled DOS seeds produce the same paths within context.128 heldout rows/step are not128 independent formations.','Fixed full-prefix frequency classifier is not a calibrated exact original-engine likelihood.','No original source-engine query or rank-truth board was required by this replay audit.'],
        result_sha256=hashlib.sha256((V2/'result.json').read_bytes()).hexdigest(),
        review_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (Path(__file__).with_name('v2-review.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
