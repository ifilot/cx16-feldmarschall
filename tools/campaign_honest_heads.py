"""Prespecified honest head-to-head validation; prepare never starts games.

Prepare: python3 tools/campaign_honest_heads.py prepare
Run only after review: python3 tools/campaign_honest_heads.py run
Analyse existing games: python3 tools/campaign_honest_heads.py analyze
"""
import argparse
import contextlib
from datetime import datetime, timezone
import json
import traceback
from pathlib import Path
import zipfile

from ai_registry import ROOT, catalog, get_policy, receives_opponent_setup
from information_strategy_cycle import analyze_match, digest, validate_metadata
from tournament_store import Tournament

DEFAULT = ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-17-honest-head-validation'
FAMILIES = ['fortified','uniform','unguarded','forward','decoy','presets','broad-mixed']
MATCHES = [
    ('row-prior-vs-context', 'teacher-flag-row-control-v1-normal', 'teacher-context-v1-normal', 2250001),
    ('joint-vs-context', 'teacher-joint-setup-v1-normal', 'teacher-context-v1-normal', 2260001),
    ('native-contact-vs-guard', 'student-exact-contact-risk-v1-normal', 'student-guard-v1-normal', 2270001),
]
ANALYSIS_FILES = ['tools/campaign_honest_heads.py','tools/information_strategy_cycle.py',
                  'tools/analyze_info_activity.py','tools/tournament.py','tools/tournament_store.py',
                  'tools/feldmarschall.py','tools/ai_registry.py']


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def plan():
    return dict(cycle=17, phase='independent honest opponent validation', rules='classic',
                setup_mode='referee', new_policies=[], rounds=100, games_per_match=1400,
                planned_games=4200, jobs=4, backend='openmp', max_plies=1000, families=FAMILIES,
                matches=[dict(name=name, group='head', policy=policy, opponent=opponent,
                              seed=seed, rounds=100) for name,policy,opponent,seed in MATCHES],
                hypotheses=[
                    'The frozen learned Flag-row Teacher improves against the honest Context Teacher.',
                    'The frozen joint Flag/Bomb Teacher improves against the honest Context Teacher.',
                    'The frozen native exact-contact policy improves against the honest native guard.'
                ],
                null_score=.5, intervals=[.95, .9833333333333333],
                analysis='Each direct candidate-versus-reference match has a fair-null score of 0.5. '
                         'Report win/draw/loss scores, all planned attempts/errors, paired-family bootstrap 95% '
                         'and 98.3333% intervals and differences from 0.5. The latter intervals account for '
                         'three prespecified endpoints by Bonferroni, subject to bootstrap limitations. '
                         'Complete error-free pairs are the bootstrap units; also report all-attempt missing-score bounds. '
                         'No self-play control, parameter tuning or policy changes on this cohort.',
                promotion='No promotion from honest heads alone. Independent DOS validation in cycles12/14, '
                          'honest-opponent results, correctness and cost all require joint review.',
                evidence='Existing immutable policy IDs and original source/model recipes only. '
                         'All failed attempts and legal error prefixes are preserved; no error is scored as a loss.')


def validate_plan(document):
    expected = plan()
    if document != expected:
        raise ValueError('honest-head plan differs from the prespecified three matches/settings')
    for match in document['matches']:
        if match['policy'] == match['opponent']:
            raise ValueError('direct distinct-policy comparisons required')


def prepare(directory=DEFAULT):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError('prepare requires an empty destination; preserve existing evidence')
    document = plan(); validate_plan(document)
    prefix = catalog()
    identities = list(dict.fromkeys(identity for match in document['matches']
                                    for identity in (match['policy'],match['opponent'])))
    frozen = {identity:get_policy(identity) for identity in identities}
    for identity, spec in frozen.items():
        if receives_opponent_setup(spec) or spec.get('difficulty') != 'normal':
            raise ValueError('honest Normal policies only')
        if digest(ROOT/spec['archive']) != spec['source_sha256']:
            raise ValueError('existing source archive integrity failure: '+identity)
    write(directory/'plan.json', document)
    write(directory/'catalog-prefix.json', prefix)
    write(directory/'frozen-policies.json', frozen)
    write(directory/'freeze.json', dict(prepared_utc=datetime.now(timezone.utc).isoformat(),
          state='prepared only; no games started', plan_sha256=digest(directory/'plan.json'),
          catalog_prefix_sha256=digest(directory/'catalog-prefix.json'),
          frozen_policies_sha256=digest(directory/'frozen-policies.json'),
          policy_sources={identity:spec['source_sha256'] for identity,spec in frozen.items()}))
    (directory/'README.md').write_text(
        '# Independent honest head-to-head validation\n\n'
        'Prepared only. No games have started. Three frozen direct comparisons, each with '
        '100 paired rounds across seven Classic setup families (1,400 games), use fresh seeds '
        '2250001, 2260001 and 2270001.\n\n'
        'Review plan.json before running. Existing policy source archives and catalog identities '
        'are fixed; no new policy is registered. The run action freezes analysis sources before '
        'the first game, then uses the Classic runner and Python/native/Qt6 replay checks. '
        'Failed files and error prefixes remain preserved.\n\n'
        'Run when resources are available: `python3 tools/campaign_honest_heads.py run`. '
        'Results report candidate scores and paired intervals relative to 50%. '
        'These tests alone cannot justify promotion; independent DOS validation remains required.\n')
    return document


def audit(directory):
    directory = Path(directory)
    document = json.loads((directory/'plan.json').read_text()); validate_plan(document)
    freeze = json.loads((directory/'freeze.json').read_text())
    for filename,key in (('plan.json','plan_sha256'),('catalog-prefix.json','catalog_prefix_sha256'),
                         ('frozen-policies.json','frozen_policies_sha256')):
        if digest(directory/filename) != freeze[key]:
            raise ValueError('prepared source/plan record changed: '+filename)
    prefix = json.loads((directory/'catalog-prefix.json').read_text())
    if catalog()[:len(prefix)] != prefix:
        raise ValueError('catalog prefix changed after preparation')
    frozen = json.loads((directory/'frozen-policies.json').read_text())
    for identity,spec in frozen.items():
        if get_policy(identity) != spec or digest(ROOT/spec['archive']) != spec['source_sha256']:
            raise ValueError('immutable policy source or recipe changed: '+identity)
    receipt_path = directory/'analysis-receipt.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if digest(directory/'analysis-sources.zip') != receipt['archive_sha256']:
            raise ValueError('analysis source archive changed')
        if any(digest(ROOT/name) != sha for name,sha in receipt['files'].items()):
            raise ValueError('analysis/runner code changed during this cohort; retain evidence for review')
    return document,frozen


def freeze_analysis(directory):
    directory = Path(directory)
    audit(directory)
    receipt_path = directory/'analysis-receipt.json'
    if receipt_path.exists():
        return
    archive = directory/'analysis-sources.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in ANALYSIS_FILES:
            bundle.write(ROOT/name,name)
    write(receipt_path,dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
          archive_sha256=digest(archive),files={name:digest(ROOT/name) for name in ANALYSIS_FILES}))


def score_endpoint(report):
    """Absolute paired score and the same intervals translated around 0.5."""
    paired = report['complete_pair_statistics']
    score = paired['metrics']['score'] if paired else None
    summary = report['summary']; policy = report['match']['policy']
    standing = summary['standings'][policy]
    attempts = summary['games']; errors = summary['errors']
    known_points = standing['wins']+standing['draws']/2
    result = dict(official_scored=standing, attempted_games=attempts, error_games=errors,
                  all_attempt_score_bounds=[known_points/attempts,(known_points+errors)/attempts],
                  bound_interpretation='Finite-cohort missing-score bounds, not confidence intervals. Errors remain officially unscored.',
                  complete_pairs=paired['complete_pairs'] if paired else 0, null_score=.5,
                  paired_score=score,
                  paired_score_minus_half={key:([v-.5 for v in value] if isinstance(value,list) else value-.5)
                                          for key,value in score.items()} if score else None)
    if score:
        result['exceeds_half_95'] = score['interval_95'][0] > .5
        result['exceeds_half_98_3333'] = score['interval_98_3333'][0] > .5
    return result


def manifest(directory):
    directory = Path(directory)
    write(directory/'manifest.json',{str(path.relative_to(directory)):digest(path)
          for path in sorted(directory.rglob('*')) if path.is_file() and path.name != 'manifest.json'})


def analyze(directory=DEFAULT):
    directory = Path(directory)
    document,frozen = audit(directory)
    if not (directory/'analysis-receipt.json').exists():
        raise ValueError('analysis sources must be frozen before games')
    reports,endpoints = {},{}
    for match in document['matches']:
        path = directory/(match['name']+'.fmtour')
        report,_,_ = analyze_match(path,match,document,frozen)
        reports[match['name']] = report
        endpoints[match['name']] = score_endpoint(report)
        write(path.with_suffix('.report.json'),report)
    result = dict(cycle=17, independent_honest_heads=True, endpoints=endpoints,
                  attempts=sum(r['summary']['games'] for r in reports.values()),
                  errors=sum(r['summary']['errors'] for r in reports.values()),
                  verified_games=sum(r['verification']['native_replayed_all_states'] for r in reports.values()),
                  production='Unchanged; independent DOS validation12/14 and honest heads require joint review.',
                  analysis_receipt_sha256=digest(directory/'analysis-receipt.json'))
    write(directory/'result.json',result); manifest(directory)
    return result


def run(directory=DEFAULT):
    from tournament import run as run_tournament
    directory = Path(directory)
    freeze_analysis(directory)
    document,frozen = audit(directory)
    try:
        for match in document['matches']:
            audit(directory)
            path = directory/(match['name']+'.fmtour')
            if not path.exists():
                with path.with_suffix('.log').open('x') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                    try:
                        run_tournament(match['policy'],match['opponent'],path,rounds=match['rounds'],
                                       seed=match['seed'],jobs=document['jobs'],families=document['families'],
                                       max_plies=document['max_plies'],backend=document['backend'],setup_mode='referee')
                    except BaseException:
                        traceback.print_exc(file=log)
                        raise
            # Failed/incomplete files are deliberately never overwritten/restarted.
            validate_metadata(path,match,document,frozen)
        return analyze(directory)
    finally:
        manifest(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','audit','run','analyze'))
    parser.add_argument('--out',type=Path,default=DEFAULT)
    args = parser.parse_args()
    if args.action == 'prepare': result = prepare(args.out)
    elif args.action == 'audit':
        document,frozen = audit(args.out); result=dict(valid=True,matches=len(document['matches']),policies=len(frozen))
    elif args.action == 'run': result = run(args.out)
    else: result = analyze(args.out)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
