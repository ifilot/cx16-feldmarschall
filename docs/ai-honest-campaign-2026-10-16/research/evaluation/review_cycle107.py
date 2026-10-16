"""Independent read-only C107 settlement; writes only its review JSON."""
import hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import get_policy,receives_opponent_setup
from tournament_store import Tournament,verify
from new_campaign_divergence import compare
from information_strategy_cycle import digest

BASE=ROOT/'docs/ai-honest-campaign-2026-10-16';directory=BASE/'cycle-107-missed-capture-generality'
plan=json.loads((directory/'plan.json').read_text());result=json.loads((directory/'result.json').read_text());frozen=json.loads((directory/'frozen-policies.json').read_text());candidate=plan['contrasts'][0][0];baseline=plan['baseline']
manifest=json.loads((directory/'manifest.json').read_text());assert all(digest(directory/name)==expected for name,expected in manifest.items())
for identity,spec in frozen.items():
 assert get_policy(identity)==spec
 if identity in plan['policies']:assert not receives_opponent_setup(spec)
 assert digest(ROOT/spec['archive'])==spec['source_sha256']
reports={};metadata={}
for identity in plan['policies']:
 path=directory/(identity+'.fmtour');reports[identity]=verify(path)
 with Tournament(path)as store:metadata[identity]=store.metadata()
 report=json.loads(path.with_suffix('.report.json').read_text())
 assert digest(path)==report['tournament_sha256']
 assert report['verification']['native_replayed_all_states']==96
 assert report['verification']['python_replayed']==96
 assert metadata[identity]['setup_dataset']['split']=='development'
 assert metadata[identity]['setup_dataset']['offset']==0
 assert next(row['policy'] for row in metadata[identity]['participants'] if row['policy']['id']==identity)['source_sha256']==frozen[identity]['source_sha256']
a=metadata[baseline]['setup_dataset'];b=metadata[candidate]['setup_dataset'];assert a==b
r=compare(directory/(baseline+'.fmtour'),baseline,directory/(candidate+'.fmtour'),candidate)
assert r['summary']['complete_case_paired_effect']==result['comparisons'][candidate+' minus '+baseline]['metrics']['score']['mean']
assert r['summary']['paired_score_directions']==dict(positive=2,negative=1,tied=45,unscored_error_pair=0)
assert r['summary']['complete_game_trajectories']['different_moves']==9
with zipfile.ZipFile(ROOT/frozen[candidate]['archive'])as bundle:
 source=bundle.read('tools/new_campaign_information_background_v2.py').decode()
 assert 'after=self.tokens.copy();after.pop(source);after[target]=token' in source
 assert 'attacks(sq,target,self.known[ally],after)' in source
 assert source.encode()==(ROOT/'tools/new_campaign_information_background_v2.py').read_bytes()
review=dict(passed=True,cycle=107,manifest_files_verified=len(manifest),attempts=192,unscored_errors=0,
 all_initial_armies_seeds_game_ids_matched=True,immutable_policy_and_honest_capability_checks=True,
 frozen_v2_source_vacancy_correction_verified=True,all_games_independently_python_replayed=192,native_all_state_evidence_verified=192,
 identical_trajectories=87,first_different_move_games=9,same_outcome_despite_different_moves=6,
 paired_score_directions=r['summary']['paired_score_directions'],complete_case_effect=r['summary']['complete_case_paired_effect'],
 cohort='frozen development partition only; validation splits not run by this study',
 conclusion='No established honest-opponent gain, regression or equivalence. Single speculative missed-capture likelihood is a soft opponent model; hidden rank is not logically inferred. V2 corrects source-vacancy geometry, not the fundamental rationality assumption.')
output=BASE/'research/evaluation/cycle-107-independent-review.json';output.write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review,indent=2))
