"""Audit actual completed information cohorts, immutable runtime and activity bounds."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from ai_registry import ROOT, catalog, receives_opponent_setup
from information_strategy_cycle import matches, validate_metadata
from tournament_store import Tournament


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'docs/ai-fair-information-2026-10-15')
    args=parser.parse_args();out=args.out.resolve()
    report=json.loads((out/'report.json').read_text());plan=report['plan']
    frozen=json.loads((out/'frozen-policies.json').read_text())
    previous=json.loads((out/'registry-before.json').read_text())['policies']
    assert catalog()[:len(previous)]==previous
    baseline=frozen[plan['baseline']]
    with zipfile.ZipFile(ROOT/baseline['archive']) as archive:
        original_models={name:archive.read(name) for name in
                         ('src/core/ai_student_model_production.h','src/core/ai_student_model.h')}
    for module,identity in plan['candidates'].items():
        policy=frozen[identity]
        assert policy['sources']==baseline['sources'] and policy['defines']==baseline['defines']
        assert policy['teacher_sources']==baseline['teacher_sources']
        assert policy['teacher_defines']==baseline['teacher_defines']
        assert policy['driver_args']==baseline['driver_args']+['--information-strategy',module]
        assert not receives_opponent_setup(policy)
        with zipfile.ZipFile(ROOT/policy['archive']) as archive:
            assert all(archive.read(name)==data for name,data in original_models.items())
            for name in ('teacher_bot.py','info_common.py','info_lifetime.py','info_objectives.py','info_followthrough.py'):
                data=archive.read('tools/'+name)
                assert data==(ROOT/'tools'/name).read_bytes(),'Live policy source changed after freezing: '+name
    attempts=errors=states=0;cohorts={};error_reasons={}
    for phase in plan['cohorts']:
        count=0
        for match in matches(plan,phase):
            path=out/phase/(match['name']+'.fmtour')
            validate_metadata(path,match,plan,frozen)
            result=report['cohorts'][phase]['matches'][match['name']]
            assert result['tournament_sha256']==sha(path.read_bytes())
            with Tournament(path) as tournament:
                rows=tournament.games()
                assert result['verification']['python_replayed']==len(rows)
                assert result['verification']['native_replayed_all_states']==len(rows)
                states+=sum(g['plies']+1 for g in rows)
                for game in rows:
                    if game['result']=='error':
                        # Every excluded error must come from the documented
                        # original fatal path, never an information adapter bug.
                        assert 'Original call 1d90:134b' in game['reason'] and 'Unexpected original interrupt 3f' in game['reason']
                        errors+=1;error_reasons[game['reason']]=error_reasons.get(game['reason'],0)+1
                count+=len(rows)
            assert len(result['activities'])==len(rows)
            for activity in result['activities']:
                weak=activity['weak']
                assert weak['unit_appearances']==16 and activity['miners_lost']<=5
                assert 0<=weak['zero_disclosure_casualties']<=weak['known_enemy_terminal_deaths']<=weak['casualties']<=16
                assert weak['known_losing_attack_deaths']<=weak['known_enemy_terminal_deaths']
                assert weak['new_enemy_disclosures']<=40
                assert (weak['favorable_followup_taken']<=weak['favorable_followup_available']
                        <=weak['probe_target_survived_reply']<=weak['probe_next_turn_reached']
                        <=weak['surviving_target_disclosures']<=weak['concealed_enemy_attacks'])
        assert count==plan['planned_attempts'][phase]
        attempts+=count;cohorts[phase]=count
    assert attempts==plan['planned_attempts']['total']
    checks={path.name:sha(path.read_bytes()) for path in (out/'checks').glob('*.log')
            if path.name!='final-audit.log'}
    result=dict(attempts=attempts,unscored_dos_errors=errors,cohorts=cohorts,
                board_states_compared_python_native=states,previous_policies_unchanged=len(previous),
                frozen_strategy_sources_match=True,same_teacher_build_settings_and_model=True,
                only_public_inputs=True,activity_bounds_passed=True,error_reasons=error_reasons,checks_sha256=checks)
    result['audit_source_sha256']=sha(Path(__file__).read_bytes())
    result['report_sha256']=sha((out/'report.json').read_bytes())
    parity=json.loads((out/'checks/native-parent-parity.log').read_text())
    assert parity['passed'] and parity['tested_decisions']>=100
    result['parent_parity_decisions']=parity['tested_decisions']
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
