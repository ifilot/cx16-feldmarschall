"""Frozen honest-AI campaign cycles: matched Classic DOS games and full replay."""
import argparse
import contextlib
import copy
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from ai_registry import ROOT, build_policy, catalog, get_policy, register, receives_opponent_setup
from information_strategy_cycle import analyze_match, bootstrap, digest, validate_metadata
from tournament import run
from tournament_store import Tournament

BASE = ROOT / 'docs/ai-honest-campaign-2026-10-15'
FAMILIES = ['fortified', 'uniform', 'unguarded', 'forward', 'decoy', 'presets', 'broad-mixed']


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def freeze(directory):
    plan = json.loads((directory/'plan.json').read_text())
    assert plan['baseline'] in plan['policies'], 'Baseline absent from comparison arms'
    assert all(a in plan['policies'] and b in plan['policies'] for a,b in plan['contrasts']), 'Contrast references an absent arm'
    assert not (directory/'frozen-policies.json').exists()
    write(directory/'registry-before.json', dict(policies=catalog()))
    for spec in plan['new_policies']:
        assert not receives_opponent_setup(spec)
        assert 'AI_DIAGNOSTIC_TRUTH' not in spec['defines']
        assert '--diagnostic-truth' not in spec.get('driver_args', [])
        register(spec)
    identities = list(dict.fromkeys([*plan['policies'], plan['opponent'], plan['baseline']]))
    write(directory/'frozen-policies.json', {p: get_policy(p) for p in identities})
    write(directory/'registration.json', dict(epoch=time.time(), plan_sha256=digest(directory/'plan.json')))


def revise_setup_mode_before_games(directory, mode, reason):
    """Preserve a superseded design before any saved matches, without changing policies."""
    assert mode == 'policy-owned-rotated-v1'
    assert not list(directory.glob('*.fmtour')) and not (directory/'result.json').exists()
    registration = json.loads((directory/'registration.json').read_text())
    assert registration['plan_sha256'] == digest(directory/'plan.json')
    plan = json.loads((directory/'plan.json').read_text())
    assert plan.get('setup_mode') == 'policy-owned'
    revision = directory/'plan-revisions/v1'
    revision.mkdir(parents=True, exist_ok=False)
    for name in ('plan.json','registration.json','frozen-policies.json','registry-before.json'):
        (revision/name).write_bytes((directory/name).read_bytes())
    plan['setup_mode'] = mode
    plan['prerun_revision'] = reason
    write(directory/'plan.json', plan)
    write(directory/'registration.json', dict(epoch=time.time(), revision=2,
          plan_sha256=digest(directory/'plan.json'),
          supersedes_plan_sha256=registration['plan_sha256'], reason=reason,
          policy_ids_and_sources_unchanged=True, saved_matches_before_revision=0))


def evaluate(directory):
    plan = json.loads((directory/'plan.json').read_text())
    assert plan['baseline'] in plan['policies'], 'Baseline absent from comparison arms'
    assert all(a in plan['policies'] and b in plan['policies'] for a,b in plan['contrasts']), 'Contrast references an absent arm'
    frozen = json.loads((directory/'frozen-policies.json').read_text())
    registration = json.loads((directory/'registration.json').read_text())
    assert registration['plan_sha256'] == digest(directory/'plan.json')
    before = json.loads((directory/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)] == before
    assert all(get_policy(p) == spec for p, spec in frozen.items())
    reports, pairs, signature = {}, {}, None
    for identity in plan['policies']:
        match = dict(name=identity, group='dos', policy=identity, opponent=plan['opponent'],
                     seed=plan['seed'], rounds=plan['rounds'])
        path = directory/(identity+'.fmtour')
        shared = plan.get('shared_control')
        if shared and identity == shared['policy'] and not path.exists():
            # The new treatment can run first while its prospectively shared
            # control is finishing in the other pool. Never rerun that control.
            subprocess.run([sys.executable, str(directory/'shared-control.py'), 'prepare'], check=True)
        if not path.exists():
            print('Running', identity, flush=True)
            with path.with_suffix('.log').open('x') as log, contextlib.redirect_stdout(log):
                result = run(identity, plan['opponent'], path, rounds=plan['rounds'], seed=plan['seed'],
                             jobs=plan['jobs'], families=plan['families'], max_plies=plan['max_plies'],
                             backend=plan['backend'], setup_mode=plan.get('setup_mode','referee'))
                print(json.dumps(result), flush=True)
        validate_metadata(path, match, plan, frozen)
        assert path.stat().st_mtime >= registration['epoch']
        report_path = path.with_suffix('.report.json')
        # Reanalyse from artifacts: never silently reuse stale cached statistics.
        report, complete, current = analyze_match(path, match, plan, frozen)
        with Tournament(path) as tournament:
            assert tournament.metadata().get('setup_mode','referee') == plan.get('setup_mode','referee')
            if plan.get('setup_mode','referee') != 'referee':
                # Own deployments are the treatment; only DOS armies must match across arms.
                current = [(g['id'],g['pair_id'],g['family'],g['seed'],
                            g['red_setup'] if g['red']==plan['opponent'] else g['blue_setup'])
                           for g in (tournament.game(row['id']) for row in tournament.games())]
        if signature is None:
            signature = current
        assert current == signature, 'Unmatched armies or seeds'
        reports[identity], pairs[identity] = report, complete
        write(report_path, report)
        print('Verified', identity, report['summary']['standings'][identity], flush=True)
    comparisons = {}
    error_sensitivity = {}
    for first, second in plan['contrasts']:
        common = sorted(pairs[first].keys() & pairs[second].keys())
        comparisons[first+' minus '+second] = bootstrap([
            (pairs[first][key][0], dict(score=pairs[first][key][1]['score']-pairs[second][key][1]['score']))
            for key in common])
        from campaign_error_sensitivity import compare as compare_errors
        name = first+' minus '+second
        error_sensitivity[name] = compare_errors(directory/(first+'.fmtour'), first,
                                                directory/(second+'.fmtour'), second)
    write(directory/'error-sensitivity.json', error_sensitivity)
    if plan['cycle'] == 1:
        base8, learned8, base32, learned32 = plan['policies']
        common = sorted(set.intersection(*(set(pairs[p]) for p in plan['policies'])))
        comparisons['model by sampling-budget interaction'] = bootstrap([
            (pairs[base8][key][0], dict(score=
             pairs[learned32][key][1]['score'] - pairs[base32][key][1]['score'] -
             pairs[learned8][key][1]['score'] + pairs[base8][key][1]['score'])) for key in common])
    result = dict(cycle=plan['cycle'], hypotheses=plan['hypotheses'], opponent=plan['opponent'], families=plan['families'], setup_mode=plan.get('setup_mode','referee'),
                  standings={p:dict(r['summary']['standings'][p], errors=r['summary']['errors'])
                             for p,r in reports.items()},
                  execution_seconds={p:r['execution_seconds'] for p,r in reports.items()},
                  comparisons=comparisons, attempts=sum(r['summary']['games'] for r in reports.values()),
                  error_sensitivity={name:value['summary'] for name,value in error_sensitivity.items()},
                  errors=sum(r['summary']['errors'] for r in reports.values()),
                  production='Unchanged. Campaign screening evidence, not a promotion decision.',
                  verified_games=sum(r['verification']['native_replayed_all_states'] for r in reports.values()))
    write(directory/'result.json', result)
    write(directory/'manifest.json', {str(p.relative_to(directory)):digest(p)
          for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'manifest.json'})
    overview()
    return result


def overview(through_cycle=None, exclude_results=()):
    lines = ['# Honest AI campaign: cumulative DOS results', '',
             'Scores count wins plus half of draws; original DOS errors are excluded. '
             'Compare policies within their matched cycle. Screening results do not establish promotion.', '',
             '| Cycle | Setup context | Policy | W / D / L | DOS score | Errors |',
             '|---|---|---|---:|---:|---:|']
    details = []
    for path in sorted(BASE.glob('cycle-*/result.json')):
        result = json.loads(path.read_text())
        if result['cycle'] in exclude_results:
            continue
        if through_cycle is not None and result['cycle']>through_cycle:
            continue
        if result.get('independent_honest_heads'):
            details += ['', '**Cycle 17: independent honest opponents**', '',
                        'These scores are against honest references, so their comparison point is 50%; they are excluded from the DOS table.', '']
            for name, endpoint in result['endpoints'].items():
                standing=endpoint['official_scored']
                metric=endpoint['paired_score']
                interval=metric['interval_98_3333'] if metric else None
                details += [f"- {name}: {standing['wins']} wins / {standing['draws']} draws / {standing['losses']} losses; "
                            f"score {standing['score']:.1%}; {endpoint['error_games']} unscored errors. "
                            +(f"98.3333% paired interval [{interval[0]:.1%}, {interval[1]:.1%}]." if interval else 'No complete pairs.')]
            details += ['', 'Evidence: ['+path.parent.name+']('+path.parent.name+'/result.json).', '']
            continue
        plan = json.loads((path.parent/'plan.json').read_text())
        frozen = json.loads((path.parent/'frozen-policies.json').read_text())
        is_dos = frozen[plan['opponent']].get('driver') == 'msdos1990'
        mode = plan.get('setup_mode','referee')
        setup_context = ('Fixed armies, seven stress families' if mode=='referee' else
                         'Own setup, original DOS, rotated' if 'original-dos' in plan['families'] else
                         'Own setup, seven stress families')
        honest_rows = []
        for policy, standing in result['standings'].items():
            # Standings preserve the canonical tournament schema.
            wins, draws, losses = (standing[k] for k in ('wins','draws','losses'))
            count = wins+draws+losses
            score = (wins+.5*draws)/count if count else 0
            if is_dos:
                lines.append(f"| {result['cycle']} | {setup_context} | {policy} | {wins} / {draws} / {losses} | {score:.1%} | {standing['errors']} |")
            else:
                honest_rows.append(f"- {policy}: {wins} wins / {draws} draws / {losses} losses; score {score:.1%}; {standing['errors']} unscored errors.")
        details += ['', '**Cycle '+str(result['cycle'])+' hypotheses:** '+
                  '; '.join(result['hypotheses']), '',
                  'Evidence: ['+path.parent.name+']('+path.parent.name+'/result.json).', '']
        if not is_dos:
            army_note = ('Both treatments use the same forced army population; compare their matched effects against this reference.'
                         if mode == 'referee' else
                         'Own army distributions differ by policy; compare matched treatment effects rather than using 50% as a fair-null benchmark.')
            details += ['Opponent: '+plan['opponent']+'. These are honest-opponent results, excluded from the DOS table. '
                        +army_note, '', *honest_rows, '']
        if result.get('setup_mode','referee') != 'referee':
            details += ['Policy-owned setups: end-to-end deployment and play; own armies intentionally differ across policies.', '']
        if mode == 'policy-owned-rotated-v1':
            details += ['Both armies rotate 180 degrees across colors, preserving DOS local deployment. Original deployment machine code runs; the move adapter independently reseeds its RNG.', '']
        for name, contrast in result['comparisons'].items():
            metric = contrast['metrics']['score']
            low, high = metric['interval_95']
            details.append(f"- {name}: {100*metric['mean']:+.1f} percentage points; 95% paired interval [{100*low:+.1f}, {100*high:+.1f}].")
        if result['cycle'] == 3:
            details += ['', 'Recurrence caveat: only five pair scores changed. The exact two-sided direction test is p=0.0625; its sparse bootstrap interval alone does not establish a regression.']
        if result['cycle'] == 5:
            details += ['', 'Exploratory signal only: the joint-minus-Context interval at 98.3333% is [-0.8, +8.6] points and includes zero. Spatial coupling did not clearly beat the simpler Flag-row control.']
        if result['cycle'] == 12:
            details += ['', 'Prespecified independent validation: interpret the three contrasts with the 98.3333% intervals recorded in result.json; no tuning on this cohort.']
        if result['cycle'] == 24:
            details += ['', 'Missing-outcome qualification: 276 original-DOS errors leave finite planned-cohort effect bounds of [-2.65, +11.15] percentage points. These are sensitivity bounds, not confidence intervals; the positive complete-case validation interval alone does not settle the effect with missing outcomes.']
        if result['cycle'] == 27:
            details += ['', 'Five-contrast screening qualification: combination minus template is +4.28 points, but its 99% paired interval is [-0.67, +9.36]. The positive 95% interval is suggestive; fresh cycle 41 tests the unchanged combination independently. See the retained 99% supplement and conclusion.']
        details.append('')
    lines += details
    failures = []
    for path in sorted(BASE.glob('cycle-*/preflight-result.json')):
        record = json.loads(path.read_text())
        if through_cycle is not None and record['cycle'] > through_cycle:
            continue
        failures += [f"- Cycle {record['cycle']}: {record['reason']} "
                     f"[Preserved evidence]({path.parent.name}/CONCLUSION.md)."]
    if failures:
        lines += ['', '**Preflight failures, without DOS strength results:**', '', *failures, '']
    deferred = [
        ('Lower-tail risk optimization', 'Eight worlds leave only one or two tail samples, and nonlinear aggregation changes the correction reference; deferred before strength tests.', 'research/horizon/cvar-decision.json'),
        ('Exact public-belief endgame proofs', 'Eligibility occurred in only two of 552 old games; bounded search found no win proof. This does not rule out deeper wins.', 'research/endgame-feasibility-decision.json'),
        ('Scout probes to identify the opening', 'Opening probes identify formations but almost always lose the Scout; no tested immediate Miner followup route. Information gain alone is insufficient.', 'research/template-identification-proposal.json'),
        ('Persistent Miner escorts', 'Existing missions already clear disclosed guards; most observed recapturers were concealed. No distinct executable handoff established.', 'research/miner-assault/proposal.json'),
        ('Irreplaceable Miner trap avoidance', 'A public proof refutes all 30 rescue replies and a retreat preserves the Miner for two turns; only one of 552 old games would change. Deferred for sparse coverage, not rejected on playing strength.', 'research/miner-assault/last-miner-trap-proposal.json'),
        ('Motion conditioned on our Spy location', 'Historical model selection chose zero Spy-factor strength; retained as a rejected prediction hypothesis, without a separate playing-strength claim.', 'research/inverse-objectives/README.md'),
        ('Passive opening-action inference', 'A fixed first-move study added no information beyond public rank facts; controlled random own play later showed predictive information. Under actual frozen native play, the extra Flag log-score gain shrank to 0.010–0.043 bits over four opening decisions, with declining prefix coverage and procedural-army overconfidence. Runtime lookup deferred; no strength tournament.', 'research/template-action-identification-v3/proposal-and-conclusion.json'),
        ('Converting early Flag inference', 'In completed native-template screening games, 324 early high-confidence Flag predictions were correct, yet 148 lost and 67 drew. Of 197 own-Flag losses, 191 final attackers were Miners; no missed final-turn public survival alternative was found. The existing two-turn interceptor could demote the saved quiet move at 11 earlier roots in ten losses; this is opportunity coverage, not saved games. No new policy or strength claim.', 'research/template-conversion-screen/README.md'),
        ('Source-structured procedural background', 'An independently heldout prediction study reduced Flag log loss by 0.250 nats while preserving the fixed 80% template mass. One procedural army remains confidently wrong. Predictive quality and playing strength are separate; the frozen DOS strength comparison is cycle 29.', 'research/procedural-background-v1/CONCLUSION.json'),
        ('Cheap procedural back-row control', 'A post-hoc ablation recovered nearly the same Flag prediction gain using only the source back-row constraint: -0.246 versus -0.250 nats. The richer model improved secondary Bomb prediction. Reused prediction data do not confirm the new control; the frozen playing-strength comparison is cycle 29, with independent final validation required for promotion.', 'research/procedural-backrow-ablation/README.md'),
        ('Earlier home interception', 'A public stationary-piece scheduling audit found 232 selected quiet moves across 37 screening games which lost time to deploy a guard against a disclosed Miner. All were outside the existing local interceptor. A mechanical fixture proves one avoidable invasion, but repeated retrospective opportunities are not saved games or a strength estimate.', 'research/home-miner-interceptor-v1/CONCLUSION.md'),
        ('Paired Miner breach', 'A forcing two-entry assault works in a public mechanical fixture, but none of 85,971 screening decisions had two Miners within three actions of distinct disclosed Bomb entries. Deferred for sparse short-horizon coverage; no gate relaxation, runtime or strength claim.', 'research/paired-miner-breach-v1/CONCLUSION.md'),
        ('Two-square tempo windows', 'A forcing public fixture works, but 693,230 screening decisions contain no strict eligible breakthrough. Five apparent last-piece traps were already lost after checking every alternative and both terminal objectives. Deferred without changing the gate or playing-strength claim.', 'research/shuttle-tempo-v1/CONCLUSION.md'),
        ('Belief-conditioned quiet approaches', 'A frozen 117-root screening audit found strict danger-order reversals at 13 roots from mobile occupancy and 34 additional roots from token-specific mobile ranks. Native threat parity passed 2,880 public comparisons. These are component changes, not selected moves or a strength result; separate runtime comparisons are required.', 'research/quiet-contact-risk-v1/CONCLUSION.md'),
        ('Public double threats with conversion proofs', 'The full fixed gate found 100 candidate roots in 13 of 400 screening games with a positive short material certificate absent for the saved native move; these collapse to 20 distinct public comparisons, with most repeated roots in one game. Proofs include hidden Scout action unions and collateral losses. This is correlated opportunity evidence, not improved outcomes. The executable-witness runtime is a separately recorded refinement; eligible-root host proof work averaged 644 ms, without a target-fit claim.', 'research/disclosed-fork-preflight-v1/CONCLUSION.md'),
        ('Executable public fork followthrough', 'The refined fixed screening audit finds 101 proposed replacements across 14 games, collapsing to 20 distinct public comparisons. A one-turn plan stores 9,429 legal public-successor capture witnesses; 82 roots fall back under the shared node cap. Mechanical and portable-history checks pass. Mean eligible-root host proof cost is 396 ms, without target qualification or playing-strength evidence. Earlier fixture metadata aliasing is explicitly corrected while retaining original artifacts and unchanged proof outputs.', 'research/quiet-fork-runtime-v1/CONCLUSION.md'),
        ('Cooperative two-piece capture nets', 'A fixed screening gate found 361 eligible roots across 91 games. The same-cohort full expansion found 81 proposed improvements across 13 games, with 63 distinct normalized public comparisons; 58 roots are concentrated in two games. All 1,524 witness states and 361 native public fixtures pass checks; 20 roots hit the shared cap. The control permits the same generalized continuations, including after a victim voluntarily attacks and dies. Mean eligible-root host proof cost is 299 ms. This is correlated tactical opportunity evidence, without playing-strength or target-fit claims.', 'research/capture-net-preflight-v1/EXPANSION-CONCLUSION.md'),
        ('Mobile beliefs in pursuit objectives: component pilot', 'The fixed Red-only sample has 298 roots in 40 games, with 5,434 persistent native prefix choices matching the frozen reference. Mobile-rank expectations change 411 actor goals; 236 strict changes are between hidden targets. Distance-progress-only quiet argmax changes occur 17 times across 10 games, including three baseline-chosen-actor cases. These are component diagnostics, not full counterfactual policy decisions or game gains; both-color study and isolated goal-only runtime remain future work.', 'research/template-mobile-objectives-pilot-v1/CONCLUSION.md'),
        ('Goal-only mobile beliefs: storage and arithmetic preflight', 'Frozen target source supports streaming goal rows through the existing transfer union, then restoring capture rows, without a second 960-byte table. An exact conditional Q24 formulation needs up to 58-bit signed magnitude arithmetic; 3,000 synthetic rational-oracle cases pass. Scratch and operation bounds are static estimates, with no implemented policy, target fit, timing or strength claim.', 'research/template-mobile-objectives-cost-preflight-v1/README.md'),
    ]
    available = [row for row in deferred if (BASE/row[2]).exists()]
    if available:
        lines += ['', '**Research screened before tournaments; no DOS strength score:**', '']
        lines += [f'- {name}: {finding} [Evidence]({source}).' for name,finding,source in available]
        lines.append('')
    if (BASE/'research/template-mobile-objectives-proposal-v1/README.md').exists():
        progress = ('A separate component pilot is recorded above; a full-policy implementation and strength test remain unrun.'
                    if (BASE/'research/template-mobile-objectives-pilot-v1/CONCLUSION.md').exists() else
                    'No opportunity diagnostic, implementation or strength test has run.')
        lines += ['**Future full-policy research:** Full mobile-rank beliefs could guide native pursuit objectives, extending the capture-only and quiet-contact bridges. The source/literature proposal specifies controls and arithmetic/target limits. '+progress+' [Proposal](research/template-mobile-objectives-proposal-v1/README.md).', '']
    if (BASE/'research/native-belief-target-fit/audit.json').exists():
        lines += ['', '**Target cost evidence:**', '',
                  '- Native belief interface: desktop prototype; the unchanged CX16 production link overflows the AI bank by 1,198 bytes. [Evidence](research/native-belief-target-fit/README.md).',
                  '- Double-shell deployment: full CX16 link passes with 395 bytes free in the mission bank; 282 extra code bytes, no extra storage. [Evidence](research/deployment-double-shell/full-target-link.json).', '']
    if (BASE/'research/native-belief-main-fit/README.md').exists():
        lines += ['- Moving the prior interface into unbanked memory resolves the AI-bank limit but overflows main memory by 748 bytes. Simple relocation is insufficient; no production source changed. [Evidence](research/native-belief-main-fit/README.md).', '']
    if (BASE/'research/compact-backrow-native-v1/README.md').exists():
        lines += ['- Compact native back-row prior: full CX16 link passes with 97 AI-bank bytes and 41 MAIN bytes free below the reserved stack. All 80 banked decisions match native execution; 18 public simulator fixtures add about 52 ms on average at an assumed 8 MHz. Cycle 31 subsequently screens playing strength; independent validation is still required. [Evidence](research/compact-backrow-native-v1/README.md).', '']
    if (BASE/'research/template-target-port-feasibility/README.md').exists():
        lines += ['- Full source-template target interface feasibility: the original isolated link with a nonfunctional inference stub left 154 MAIN bytes and 4,724 bytes in a new bank. This established interface space only; the subsequent actual prototype has separate evidence below. [Evidence](research/template-target-port-feasibility/README.md).', '']
    if (BASE/'research/template-target-prototype-v1/qualification.json').exists():
        lines += ['- Native Q24 source-template research prototype: the standard link overflows MAIN by 232 bytes; an explicit experimental runtime-helper relocation recipe links with 84 MAIN and 81 AI-bank bytes free. Three layouts cover 96 real banked decisions with matching moves, probabilities and signed gain caches; 32 also compare output RNG state. Music remains active, with 996 stack-canary bytes untouched in these traces. Maximum observed whole-AI cost is about 1.48 seconds at an assumed 8 MHz. This qualifies a distinct numerical policy for cycle 42, without enabling production or establishing strength. [Evidence](research/template-target-prototype-v1/README.md).', '']
    if (BASE/'research/template-target-cache-v2/qualification.json').exists():
        lines += ['- Exact public-evidence cache V2: 1,940 historical decisions preserve moves, RNG, probabilities and gains exactly, with 1,276 natural cache hits. The 48-decision actual-target retention fixture measures preparation at 16–21 ms on hits versus 0.98–1.10 seconds on misses; it does not measure a natural target average. Cache-off native and five target binaries remain byte-identical to V1. The custom link leaves 66 MAIN bytes free; production remains off. [Evidence](research/template-target-cache-v2/README.md).', '']
    pending = []
    for path in sorted(BASE.glob('cycle-*/plan.json')):
        plan = json.loads(path.read_text())
        if ((path.parent/'result.json').exists() and plan['cycle'] not in exclude_results) or (path.parent/'preflight-result.json').exists():
            continue
        if through_cycle is not None and plan['cycle']>through_cycle:
            continue
        count = plan.get('planned_games',2*len(plan['families'])*plan['rounds']*len(plan.get('policies',[])))
        state = 'registered' if (path.parent/'frozen-policies.json').exists() else 'prepared; registration pending'
        pending.append(f"- Cycle {plan['cycle']}: {'; '.join(plan['hypotheses'])} "
                       f"{count:,} planned comparison attempts; {state}; no completed strength result. [Plan]({path.parent.name}/plan.json).")
    if pending:
        lines += ['', '**Experiments awaiting completed results:**', '', *pending, '']
    (BASE/'OVERVIEW.md').write_text('\n'.join(lines)+'\n')


def audit(directory):
    plan = json.loads((directory/'plan.json').read_text())
    frozen = json.loads((directory/'frozen-policies.json').read_text())
    before = json.loads((directory/'registry-before.json').read_text())['policies']
    assert catalog()[:len(before)] == before
    assert all(get_policy(p) == spec for p, spec in frozen.items())
    result = json.loads((directory/'result.json').read_text())
    games_per_policy = 2*len(plan['families'])*plan['rounds']
    assert result['attempts'] == result['verified_games'] == games_per_policy*len(plan['policies'])
    reproduced = {}
    for spec in plan['new_policies']:
        policy = frozen[spec['id']]
        assert not receives_opponent_setup(policy)
        assert 'AI_DIAGNOSTIC_TRUTH' not in policy['defines']
        assert '--diagnostic-truth' not in policy.get('driver_args', [])
        executable, previous = build_policy(policy['id'])
        (executable.parent/'build.json').unlink()
        _, rebuilt = build_policy(policy['id'])
        assert rebuilt == previous, policy['id']
        reproduced[policy['id']] = rebuilt['runtime_sha256']
    for policy in plan['policies']:
        path = directory/(policy+'.fmtour')
        report = json.loads(path.with_suffix('.report.json').read_text())
        assert report['tournament_sha256'] == digest(path)
        assert report['verification']['python_replayed'] == games_per_policy
        assert report['verification']['native_replayed_all_states'] == games_per_policy
        assert path.with_suffix('.png').is_file()
        if plan.get('setup_mode','referee') != 'referee':
            from audit_policy_setups import audit as audit_setups
            write(path.with_suffix('.setups-audit.json'), audit_setups(path))
        if 'original-dos' in plan['families']:
            from campaign_dos_setup_runtime import audit_original_setups
            write(path.with_suffix('.original-dos-setups-audit.json'), audit_original_setups(path))
    tests = directory/'checks.log'
    assert tests.is_file()
    test_text = tests.read_text()
    assert re.search(r'^OK(?: \(skipped=\d+\))?$', test_text, re.M) and 'FAILED' not in test_text
    counts = re.findall(r'^Ran (\d+) tests? in ', test_text, re.M)
    assert counts and all(int(count)>0 for count in counts)
    write(directory/'audit.json', dict(passed=True, previous_policies_unchanged=len(before),
          attempts=result['attempts'], errors_preserved_unscored=result['errors'],
          all_games_python_native_replayed=True, qt6_captures=len(plan['policies']),
          exact_rebuild_runtime_sha256=reproduced, production_unchanged=True,
          test_counts=[int(n) for n in counts],
          test_skip_summaries=re.findall(r'^OK \(skipped=\d+\)$',test_text,re.M)))
    write(directory/'manifest.json', {str(p.relative_to(directory)):digest(p)
          for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'manifest.json'})


def init_sampling():
    directory = BASE/'cycle-01-sampling-budget'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline, learned = 'teacher-context-v1-normal', 'teacher-calibrated-beliefs-v1-normal'
    new = []
    for parent, identity in ((baseline, 'teacher-context-worlds32-v1-normal'),
                             (learned, 'teacher-calibrated-worlds32-v1-normal')):
        spec = copy.deepcopy(get_policy(parent))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental',
                    description='Honest 32-world sampling-budget ablation of '+parent,
                    model='Unchanged four-ply guarded Context Teacher; 32 independent public-compatible armies.')
        spec['driver_args'][spec['driver_args'].index('--samples')+1] = '32'
        new.append(spec)
    policies = [baseline, learned, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=1, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2090001, rounds=20, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES,
          hypotheses=['More public-compatible enemy armies reduce decision noise at four times rollout work.',
                      'Calibrated beliefs benefit more from 32 armies than from eight; test the model-by-budget interaction.'],
          contrasts=[[policies[2],baseline],[policies[3],learned],[learned,baseline],[policies[3],policies[2]]],
          analysis='Fixed fresh screening cohort. 20000 family-stratified swapped-pair bootstrap replicates. '
                   'Report every contrast and cost, no production promotion from these exploratory comparisons. '
                   'All public-state traces replayed independently in Python and native worker; Qt6 capture each policy.',
          honesty='No opponent setup, diagnostic observer or referee ranks enter any policy. '
                  'Learned model was frozen before this campaign; no fitting on these seeds.'))
    return directory


def init_mechanisms():
    directory = BASE/'cycle-02-cheap-mechanisms'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline = 'teacher-context-v1-normal'
    new = []
    variants = [
        ('teacher-latin-worlds-v1-normal', ['--world-sampling','latin'],
         'Latin-hypercube random coordinates spread eight count-consistent worlds without additional native searches.'),
        ('teacher-army-activation-v1-normal', ['--campaign-strategy','activation'],
         'Bounded quiet-move potential rewards opening teammates routes to central crossings; enemy ranks unused.'),
        ('teacher-paired-confidence-v1-normal', ['--paired-confidence'],
         'Require paired corrected advantage over native move to exceed one jackknife standard error; no extra rollouts.')]
    for identity, arguments, idea in variants:
        spec = copy.deepcopy(get_policy(baseline))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental', description=idea,
                    model='Unchanged eight-world four-ply Context Teacher plus isolated '+identity,
                    information_model='Own setup and public events only. No opponent setup or diagnostic disclosure.')
        spec['driver_args'] += arguments
        new.append(spec)
    policies = [baseline, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=2, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2100001, rounds=30, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES, hypotheses=[row[2] for row in variants],
          contrasts=[[p, baseline] for p in policies[1:]],
          analysis='Three distinct prespecified exploratory mechanisms, all reported. Matched armies and seeds. '
                   '20000 family-stratified swapped-pair bootstrap replicates; both 95% and 98.333% intervals retained. '
                   'No promotion without fresh independent validation and honest direct opponents.',
          honesty='Native observer has no AI_DIAGNOSTIC_TRUTH. No candidate receives opponent setup. '
                  'Each optional hook isolated; baseline snapshot and all prior IDs immutable.'))
    return directory


def init_horizons():
    directory = BASE/'cycle-03-horizons-and-memory'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline = 'teacher-context-v1-normal'
    variants = [
        ('teacher-capture-quiescence-v1-normal', [], ['AI_ROLLOUT_QUIESCENCE'],
         'Finish policy-selected exchanges beyond four plies, stopping before a quiet move, with at most four extra masked decisions.'),
        ('teacher-sparse-depth-v1-normal', ['--adaptive-depth'], [],
         'Spend eight plies only when public root mobility has at most twelve legal actions, retaining four otherwise.'),
        ('teacher-recurrence-escape-v1-normal', ['--campaign-strategy','recurrence'], [],
         'Remember repeated friendly formations across actors and escape long quiet loops when a similarly valued fresh continuation exists.'),
        ('teacher-uniform-worlds-v1-normal', ['--world-sampling','uniform'], [],
         'Ablate handwritten approach/retreat weights while retaining exactly the same IID count-consistent world proposal; negative-control belief test.')]
    new = []
    for identity, arguments, defines, idea in variants:
        spec = copy.deepcopy(get_policy(baseline))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental', description=idea,
                    model='Isolated honest Context Teacher experiment: '+identity,
                    information_model='Own setup and public events only; sampled worlds never referee ranks.')
        spec['driver_args'] += arguments
        spec['teacher_defines'] += defines
        new.append(spec)
    policies = [baseline, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=3, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2110001, rounds=30, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES, hypotheses=[row[3] for row in variants],
          contrasts=[[p, baseline] for p in policies[1:]],
          analysis='Four prespecified distinct exploratory mechanisms. Fresh seeds, matched armies and side swaps. '
                   '20000 family-stratified paired bootstrap; 95% intervals descriptive across the campaign. '
                   'Uniform weights have adverse offline calibration evidence and are retained as an explicit negative control. '
                   'No tuning or promotion on this cohort.',
          evidence='Historical development mechanisms under research/: quiescence, adaptive-depth, recurrence and weight audit.'))
    return directory


def init_public_defence():
    directory = BASE/'cycle-04-public-flag-defence'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline, native = 'teacher-context-v1-normal', 'student-guard-v1-normal'
    new = []
    for parent, identity in ((native,'student-public-flag-threats-v1-normal'),
                             (baseline,'teacher-public-flag-threats-v1-normal')):
        spec = copy.deepcopy(get_policy(parent))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental',
                    description='Classic public deduction: adjacent concealed enemy that already moved is a confirmed Flag threat.',
                    model='Unchanged '+parent+' except AI_PUBLIC_FLAG_THREATS.',
                    information_model='Own setup and public board/events only; no concealed enemy rank access.')
        spec['defines'].append('AI_PUBLIC_FLAG_THREATS')
        if 'teacher_defines' in spec:
            spec['teacher_defines'].append('AI_PUBLIC_FLAG_THREATS')
        spec.setdefault('asset_files', []).append('tests/ai_public_flag_threats_test.c')
        new.append(spec)
    policies = [native, new[0]['id'], baseline, new[1]['id']]
    write(directory/'plan.json', dict(cycle=4, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2120001, rounds=30, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES,
          hypotheses=['Correct a public logical omission in native Flag defence, without identifying the concealed rank.',
                      'Test the same deduction in the Context Teacher observer and masked continuations.'],
          contrasts=[[policies[1],native],[policies[3],baseline]],
          analysis='Fresh matched side-swapped Classic cohort; report both backends, no tuning or promotion. '
                   'Historical final positions often unsavable; synthetic defence correctness does not imply recovered wins.',
          evidence='research/loss-mechanisms.json and research/public-flag-threat-tests.json.'))
    return directory


def init_joint():
    directory = BASE/'cycle-05-joint-setup-beliefs'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline, independent = 'teacher-context-v1-normal', 'teacher-calibrated-beliefs-v1-normal'
    new = []
    for identity, model, idea in (
        ('teacher-flag-row-control-v1-normal','flag-row-prior-control-v1.json',
         'Control: trained Flag-row prior with exact public rank counts; no Flag/Bomb spatial coupling.'),
        ('teacher-joint-setup-v1-normal','joint-flag-bomb-beliefs-v1.json',
         'Infer protected versus loose Flag/Bomb setup style from public movement and retained Bomb disclosures.')):
        spec = copy.deepcopy(get_policy(baseline))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        path = ROOT/'ai/models'/model
        spec.update(id=identity, name=identity, status='experimental', description=idea,
                    model='Frozen two-style setup prior; exact conditional six-Bomb subset draw, eight worlds/four plies unchanged.',
                    joint_belief_model=str(path.relative_to(ROOT)),joint_belief_model_sha256=digest(path),
                    asset_files=[str(path.relative_to(ROOT))],
                    information_model='Own setup and public events only. Retains public captured Bomb origins. No enemy setup.')
        spec['driver_args'] += ['--joint-belief-model',model]
        new.append(spec)
    policies = [baseline, independent, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=5, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2130001, rounds=40, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES,
          hypotheses=['A cheap learned setup-style mixture can exploit public Flag/Bomb dependencies missed by independent rank tables.',
                      'A control with identical trained Flag-row priors and zero spatial coupling separates positional prior from cross-piece inference.'],
          contrasts=[[policies[3],policies[2]],[policies[3],baseline],[policies[2],baseline],[policies[3],independent]],
          analysis='Fresh matched cohort, all four arms retained. Joint versus identical-prior uncoupled control is primary mechanistic contrast. '
                   'Exploratory strength cohort; fresh final validation and honest opponents required for promotion. '
                   'Fit196historical training armies; calibration84 armies; no campaign seed used to fit or choose parameters.',
          evidence='research/joint-setup-development.json, joint-exact-control-calibration.json and joint-public-prefix-audit.json.'))
    return directory


def init_evaluation():
    directory = BASE/'cycle-06-evaluation-and-opponent'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline = 'teacher-context-v1-normal'
    variants = [
        ('teacher-capable-routes-v1-normal', [], ['AI_ROLLOUT_CAPABLE_ROUTES'],
         'Evaluate Flag routes an actual attacker can survive, instead of ignoring enemy mobile defenders.'),
        ('teacher-informed-opponent-v1-normal', [], ['AI_ROLLOUT_INFORMED_OPPONENT'],
         'Honestly model DOS knowledge: simulated opponent knows our Flag and Spy; root learns no enemy identity.'),
        ('teacher-parent-anchor-v1-normal', ['--correction-anchor','parent'], [],
         'Anchor clipped continuation corrections to the legal native fallback rather than an imaginary pass; no coefficient change.')]
    new = []
    for identity, arguments, defines, idea in variants:
        spec = copy.deepcopy(get_policy(baseline))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental', description=idea,
                    model='Isolated honest Context Teacher experiment: '+identity,
                    information_model='Own setup and public events only. No enemy setup or diagnostic rank disclosure.')
        spec['driver_args'] += arguments
        spec['teacher_defines'] += defines
        if identity=='teacher-informed-opponent-v1-normal':
            spec['opponent_model']='Opponent knows root-owned Flag and Spy; root masking unchanged.'
        new.append(spec)
    policies = [baseline, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=6, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2140001, rounds=30, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES, hypotheses=[row[3] for row in variants],
          contrasts=[[p, baseline] for p in policies[1:]],
          analysis='Three distinct prespecified exploratory mechanisms. Fresh matched side-swapped Classic games. '
                   'No root sampling budget increase; changed value estimates, opponent information assumptions or clipping anchor. '
                   'Report all variants and intervals. No promotion without independent validation.',
          evidence='research/horizon: capable-routes, informed-opponent-view-audit and parent-centering-mechanism.'))
    return directory


def init_contact_risk():
    directory = BASE/'cycle-07-exact-contact-risk'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline, native = 'teacher-context-v1-normal', 'student-guard-v1-normal'
    new = []
    for parent, identity in ((native,'student-exact-contact-risk-v1-normal'),
                             (baseline,'teacher-exact-contact-risk-v1-normal')):
        spec = copy.deepcopy(get_policy(parent))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental',
                    description='Count-consistent probability that any hidden contact can beat the actor, using exact moved/unmoved eligibility and Scout rays.',
                    model='Unchanged '+parent+' except Classic AI_EXACT_CONTACT_RISK fixed-point inclusion-exclusion.',
                    information_model='Own setup, public rank counts, disclosure and movement bits only. Uniform compatible-rank prior.')
        spec['defines'].append('AI_EXACT_CONTACT_RISK')
        if 'teacher_defines' in spec:
            spec['teacher_defines'].append('AI_EXACT_CONTACT_RISK')
        spec.setdefault('asset_files', []).extend(['tests/ai_exact_contact_risk_test.c','tests/ai_contact_risk_cost.c'])
        new.append(spec)
    policies = [native, new[0]['id'], baseline, new[1]['id']]
    write(directory/'plan.json', dict(cycle=7, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2150001, rounds=30, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES,
          hypotheses=['Replace maximum of individual hidden-contact mean risks by expected lethal opportunity across contacts, respecting unique ranks and movement constraints.',
                      'Test the same cheap probability model in native play and the Context Teacher continuations.'],
          contrasts=[[policies[1],native],[policies[3],baseline]],
          analysis='Fresh matched side-swapped Classic cohort; no tuning or promotion. '
                   'Probability is exact under uniform compatible ranks, not a guarantee about opponent action choices or playing strength. '
                   'Speculative capture scoring retains existing survival-branch approximation.',
          evidence='research/exact-contact-risk-audit.json and exact-contact-risk-derivation.json; 19152 enumeration cases, default native binary parity.'))
    return directory


def init_swap():
    directory = BASE/'cycle-08-rank-swap-beliefs'
    assert not directory.exists()
    directory.mkdir(parents=True)
    baseline, independent = 'teacher-context-v1-normal', 'teacher-calibrated-beliefs-v1-normal'
    new = []
    for identity, sweeps, idea in (
        ('teacher-unweighted-beliefs-v1-normal',0,
         'Control: discard small-batch importance weights from the learned sequential proposal, with no posterior rejuvenation.'),
        ('teacher-swap-beliefs-v1-normal',4,
         'Use four sweeps of count-preserving rank-swap Metropolis updates in independent chains, then average eight equal-weight worlds.')):
        spec = copy.deepcopy(get_policy(independent))
        for key in ('archive', 'source_sha256'):
            spec.pop(key)
        spec.update(id=identity, name=identity, status='experimental', description=idea,
                    model='Unchanged frozen public-history likelihood tables; '+str(sweeps)+' independent-chain swap sweeps, eight worlds and four plies.',
                    information_model='Own setup and public history only; exact counts/masks; finite-burn-in approximate posterior.')
        spec['driver_args'] += ['--belief-sweeps',str(sweeps)]
        new.append(spec)
    policies = [baseline, independent, *[p['id'] for p in new]]
    write(directory/'plan.json', dict(cycle=8, baseline=baseline, opponent='msdos-1990-v2-normal',
          policies=policies, new_policies=new, seed=2160001, rounds=40, jobs=4, max_plies=1000,
          backend='openmp', families=FAMILIES,
          hypotheses=['Reduce finite-eight-world importance-weight noise without increasing native rollout count.',
                      'Separate equal-weight proposal control from approximate posterior correction by rank-swap rejuvenation.'],
          contrasts=[[policies[3],independent],[policies[3],policies[2]],[policies[2],independent],[policies[3],baseline]],
          analysis='Fresh matched exploratory cohort; all four arms retained. Four sweeps chosen from historical calibration prediction/mixing, never campaign win scores. '
                   'Metropolis target is invariant but finite chain convergence is not guaranteed; zero-sweep proposal intentionally has target bias. '
                   'No promotion without independent validation and honest opponents.',
          evidence='research/swap-belief-diagnosis.json and swap-marginal-mixing.json.'))
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init-sampling','init-mechanisms','init-horizons','init-public-defence','init-joint','init-evaluation','init-contact-risk','init-swap','freeze','run','overview','audit'])
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--through-cycle', type=int)
    args = parser.parse_args()
    if args.action == 'init-sampling':
        print(init_sampling())
    elif args.action == 'init-mechanisms':
        print(init_mechanisms())
    elif args.action == 'init-horizons':
        print(init_horizons())
    elif args.action == 'init-public-defence':
        print(init_public_defence())
    elif args.action == 'init-joint':
        print(init_joint())
    elif args.action == 'init-evaluation':
        print(init_evaluation())
    elif args.action == 'init-contact-risk':
        print(init_contact_risk())
    elif args.action == 'init-swap':
        print(init_swap())
    elif args.action == 'freeze':
        freeze(args.directory)
    elif args.action == 'run':
        evaluate(args.directory)
    elif args.action == 'audit':
        audit(args.directory)
    else:
        overview(args.through_cycle)


if __name__ == '__main__':
    main()
