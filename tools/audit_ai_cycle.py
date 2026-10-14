"""Audit the requested cycle against retained gates, sources and final variant evidence."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from feldmarschall import ROOT
from test_ai_mission_cases import verify as verify_cases
from verify_ai_archives import verify as verify_archive
from verify_teacher_stage import gate as teacher_gate
from verify_student_stage import verify as student_gate
from verify_student_runtime import verify as runtime_gate


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(variants):
    ledger=json.loads((ROOT/'docs/ai-experiments.json').read_text())
    games=sum(verify_archive(entry,ROOT/'docs') for entry in ledger)
    for folder in ('ai-selection','ai-teacher','ai-student-production'):
        directory=ROOT/'docs'/folder;manifest=json.loads((directory/'manifest.json').read_text())
        archive=directory/manifest['archive'];assert sha(archive)==manifest['archive_sha256']
        with zipfile.ZipFile(archive) as data:
            assert data.testzip() is None
            for name,expected in manifest.get('files',{}).items():assert hashlib.sha256(data.read(name)).hexdigest()==expected
            for name,expected in manifest.get('runtime_sha256',{}).items():
                matches=[n for n in data.namelist() if n.rsplit('/',1)[-1]==name]
                assert len(matches)==1 and hashlib.sha256(data.read(matches[0])).hexdigest()==expected
    selection={}
    for level in ('normal','hard'):
        run=ROOT/'build/ai-selection'/f'{level}-validation'
        from verify_ai_selection import verify
        verify(run);selection[level]=json.loads((run/'selection-integrity.json').read_text())
        assert json.loads((run/'summary.json').read_text())['promotion_passed']
    verify_cases(ROOT/'docs/ai-mission-cases')
    teacher=teacher_gate(ROOT/'build/ai-teacher/frozen-correction-policy.json',
                         ROOT/'build/ai-teacher/correction-mission-validation',ROOT/'build/ai-teacher/correction-material-validation')
    assert teacher['both_gates_passed']
    student=student_gate(ROOT/'build/ai-student/coop-guard-development/frozen-policy.json',ROOT/'build/ai-student/coop-guard-validation')
    assert student['strength_gate_passed']
    runtime=runtime_gate(ROOT/'build/ai-student/coop-guard-production',ROOT/'build/ai-student/balanced-v2/model.json')
    isolated=[e for e in ledger if e['name'].startswith('mission-') and 'development' in e['name']]
    assert len(isolated)==14 and all(e['decision']=='reject' for e in isolated)
    assert sum(sum(v['games'] for v in e['comparisons'].values()) for e in isolated)==3920
    source_identity=[]
    with zipfile.ZipFile(ROOT/'docs/ai-student-production/evidence-20261014.zip') as data:
        turns=json.loads(data.read('build/ai-student/coop-guard-production/banked-student-decisions.json'))
        assert len(turns['turns'])==80 and {r['army'] for r in turns['turns']}=={0,1} and turns['mismatches']==0
        assert turns['minimum_stack_canary_untouched_bytes']>=32
        cases=json.loads(data.read('build/ai-student/coop-guard-cases/summary.json'))
        improvements=sum(r['baseline']['known_losing_capture'] and not r['candidate']['known_losing_capture'] and r['candidate']['curated_alternative'] for r in cases['positions'])
        assert improvements==2
        with zipfile.ZipFile(io.BytesIO(data.read('sources.zip'))) as sources:
            source_identity=[name for name in sources.namelist() if name.startswith(('src/core/','src/ui/','src/scenes/')) and Path(name).suffix in ('.c','.h','.s')]
            assert all(sources.read(name)==(ROOT/name).read_bytes() for name in source_identity)
            assert sources.read('src/Makefile')==(ROOT/'src/Makefile').read_bytes()
            old=re.search(r'^AI_PRODUCTION_FLAGS\s*=(.*)$',sources.read('Makefile').decode(),re.M).group(1)
            current=re.search(r'^AI_PRODUCTION_FLAGS\s*=(.*)$',(ROOT/'Makefile').read_text(),re.M).group(1)
            assert old==current
    with zipfile.ZipFile(ROOT/'docs/ai-teacher/evidence-20261014.zip') as data:
        rows=[json.loads(line) for line in data.read('build/ai-student/balanced-v2/labels.jsonl').splitlines()]
        train={r['split_group'] for r in rows if not r['validation']};holdout={r['split_group'] for r in rows if r['validation']}
        assert train and holdout and not train&holdout and {r['history'] for r in rows}=={'full','cold'}
        assert len(rows)==46808
    summary=json.loads((variants/'verified-summary.json').read_text())
    trace=json.loads((variants/'trace-integrity.json').read_text())
    assert summary['plan_sha256']==sha(variants/'plan.json')
    assert set(summary['conditions'])==set(map(str,(0,1,2,4,8,16,32,3,10,48,63)))
    assert summary['games']==trace['games_replayed']==15400
    assert all(v['games']==700 for levels in summary['conditions'].values() for v in levels.values())
    views=sum(v['view_checks'] for levels in summary['conditions'].values() for v in levels.values())
    assert views==2*(trace['plies_replayed']+trace['games_replayed'])
    decision=json.loads((variants/'tuning-decision.json').read_text())
    assert decision['variant_specific_development_justified'] and not decision['new_variant_policy_promoted']
    return {'schema':1,'objective_sha256':sha(ROOT/'docs/ai-cycle-completion/objective.txt'),
            'requirements':[
                {'requirement':'Define and independently validate varied deployment selection','status':'complete','evidence':'docs/ai-next-cycle-2026-10-14.md; selection Normal/Hard archives'},
                {'requirement':'Integrate successful deployment policy into X16 and packages','status':'complete','evidence':'docs/ai-selection/manifest.json; docs/ai-student-production/manifest.json'},
                {'requirement':'Focused public decoy, stall, Miner and specialist diagnostics','status':'complete','evidence':'docs/ai-mission-cases/manifest.json; 18 cases and oracle-exclusion checks'},
                {'requirement':'Isolated mission experiments and a reliable accepted improvement','status':'complete','evidence':'14 rejected runs, 3920 games; cooperation-guard student 54.0% and two diagnostic improvements'},
                {'requirement':'Actual X16 fairness, parity, resources, timing and save/load gates','status':'complete','evidence':'docs/ai-student-production/manifest.json; exact current game-source identity'},
                {'requirement':'Stronger public-input desktop teacher','status':'complete','evidence':'docs/ai-teacher/manifest.json; recomputed independent teacher gates'},
                {'requirement':'Compact full/cold-history student with independent strength and target gates','status':'complete','evidence':'46808 grouped labels; recomputed student and runtime gates'},
                {'requirement':'Individual/combined variant strength for Normal/Hard and tuning decision','status':'complete','evidence':'docs/ai-variants/manifest.json; 15400 audited/replayed final games'},
                {'requirement':'Retain sources, programs, seeds, traces, decisions and commit checkpoints','status':'complete','evidence':'docs/ai-experiments.json; immutable bundles; repository commit containing this audit'}],
            'archives_verified':len(ledger),'games_in_ledger':games,'selection':selection,
            'teacher_gate_passed':True,'student_gate_passed':True,'runtime':runtime,
            'unchanged_game_source_files':len(source_identity),'grouped_labels':len(rows),
            'diagnostic_improvements':improvements,'variant_plies_replayed':trace['plies_replayed'],
            'variant_views_audited':views,'remaining_required_work':[]}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--variants',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();report=audit(args.variants)
    with args.out.open('x') as output:output.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'requirements':len(report['requirements']),'archives':report['archives_verified'],'games':report['games_in_ledger'],'remaining_required_work':report['remaining_required_work']},indent=2))
