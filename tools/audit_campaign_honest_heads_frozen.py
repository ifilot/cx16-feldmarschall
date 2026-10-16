"""Terminal receipt/replay audit for the prespecified C17 honest heads.

Reads cached frozen runtimes without rebuilding shared executables. It changes
only the cohort audit/manifest artifacts, never analysis sources or policy IDs.
"""
import hashlib
import json
from pathlib import Path
import re

from ai_registry import ROOT,receives_opponent_setup
from campaign_honest_heads import DEFAULT,audit,manifest
from information_strategy_cycle import digest
from tournament_store import Tournament


def main():
    directory=DEFAULT;plan,frozen=audit(directory)
    result=json.loads((directory/'result.json').read_text())
    assert result['independent_honest_heads'] and result['attempts']==result['verified_games']==4200
    assert result['analysis_receipt_sha256']==digest(directory/'analysis-receipt.json')
    checks=(directory/'checks.log').read_text();assert re.search(r'^OK$',checks,re.M) and 'FAILED' not in checks
    tests=list(map(int,re.findall(r'^Ran (\d+) tests? in ',checks,re.M)));assert tests and all(n>0 for n in tests)
    qualification=json.loads((directory/'checks-provenance.json').read_text())
    assert qualification['passed'] and qualification['checks_sha256']==digest(directory/'checks.log')
    assert qualification['plan_sha256']==digest(directory/'plan.json')
    for name,sha in qualification['files'].items():assert digest(ROOT/name)==sha,name
    runtimes={}
    for identity,spec in frozen.items():
        assert not receives_opponent_setup(spec)
        assert 'AI_DIAGNOSTIC_TRUTH' not in spec.get('defines',[])
        assert '--diagnostic-truth' not in spec.get('driver_args',[])
        runtime=ROOT/'build/ai-catalog'/identity
        receipt=json.loads((runtime/'build.json').read_text());assert receipt['policy']==spec
        assert receipt['recipe_sha256']==hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
        assert digest(ROOT/spec['archive'])==spec['source_sha256']
        for name,sha in receipt['runtime_sha256'].items():assert digest(runtime/name)==sha,(identity,name)
        runtimes[identity]=receipt['runtime_sha256']
    matches={};errors=0
    for match in plan['matches']:
        path=directory/(match['name']+'.fmtour');report=json.loads(path.with_suffix('.report.json').read_text())
        assert report['tournament_sha256']==digest(path)
        assert report['verification']['artifacts_verified']
        assert report['verification']['python_replayed']==report['verification']['native_replayed_all_states']==1400
        assert path.with_suffix('.png').stat().st_size>0
        assert report['summary']['games']==1400
        with Tournament(path) as saved:
            assert saved.metadata()['status']=='complete' and len(saved.games())==1400
        endpoint=result['endpoints'][match['name']]
        assert endpoint['attempted_games']==1400 and endpoint['null_score']==.5
        assert endpoint['error_games']==report['summary']['errors']
        assert endpoint['paired_score']==report['complete_pair_statistics']['metrics']['score']
        errors+=endpoint['error_games']
        matches[match['name']]=dict(attempts=1400,errors=endpoint['error_games'],tournament_sha256=digest(path),
            python_native_all_states_replayed=True,artifacts_verified=True,qt6_capture=path.with_suffix('.png').name)
    assert errors==result['errors']
    evidence=dict(passed=True,attempts=4200,errors_preserved_unscored=errors,
        independent_honest_heads=True,analysis_source_archive_sha256=digest(directory/'analysis-sources.zip'),
        analysis_and_preflight_sources_unchanged=True,all_policies_honest=True,
        cached_runtime_receipts_verified_without_rebuild=runtimes,matches=matches,test_counts=tests,
        audit_script_sha256=digest(Path(__file__)),production_unchanged=True)
    (directory/'audit.json').write_text(json.dumps(evidence,indent=2)+'\n');manifest(directory)
    print(json.dumps(dict(passed=True,attempts=4200,errors=errors,heads=len(matches),test_counts=tests),indent=2))

if __name__=='__main__':main()
