"""Independent aggregate-only review of the preserved overview snapshot."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
text = (HERE / 'OVERVIEW-reviewed.md').read_text()
bindings = {'OVERVIEW.md': sha(HERE / 'OVERVIEW-reviewed.md'),
            'tools/campaign_cycle.py': sha(HERE / 'campaign_cycle-reviewed.py')}
failures, omissions = [], []
counts = dict(dos_standing_rows=0, honest_standing_rows=0, head_rows=0,
              contrasts=0, intervals_95=0, intervals_98_3333=0, links=0,
              figure_rows=0, conclusions=0)

def check(condition, message):
    if not condition:
        failures.append(message)

def bind(p):
    bindings[str(p.relative_to(BASE))] = sha(p)

paths = {}
for link in re.findall(r'\]\(([^)]+/result\.json)\)', text):
    p = BASE / link
    r = json.loads(p.read_text())
    paths[r['cycle']] = p

for cycle, p in sorted(paths.items()):
    r = json.loads(p.read_text())
    plan_path = p.with_name('plan.json')
    plan = json.loads(plan_path.read_text())
    bind(p)
    bind(plan_path)
    start = re.search(r'\*\*Cycle '+str(cycle)+r'(?: hypotheses:|: independent)',text)
    check(start is not None, f'C{cycle}: section heading')
    following = re.search(r'\*\*Cycle \d+',text[start.end():])
    section = text[start.start():start.end()+following.start()] if following else text[start.start():]
    if r.get('independent_honest_heads'):
        for name, endpoint in r['endpoints'].items():
            st = endpoint['official_scored']
            score = (st['wins'] + st['draws']/2) / sum(st[k] for k in ('wins','draws','losses'))
            check(math.isclose(score, st['score']), f'C17 {name}: score arithmetic')
            lo, hi = endpoint['paired_score']['interval_98_3333']
            lo95, hi95 = endpoint['paired_score']['interval_95']
            row = (f"- {name}: {st['wins']} wins / {st['draws']} draws / {st['losses']} losses; "
                   f"score {score:.1%}; {endpoint['error_games']} unscored errors. "
                   f"95% paired interval [{lo95:.1%}, {hi95:.1%}]; planned 98.3333% interval [{lo:.1%}, {hi:.1%}].")
            check(row in section, f'C17 {name}: rendered row/98.3333 interval')
            counts['head_rows'] += 1
            counts['intervals_95'] += 1
            counts['intervals_98_3333'] += 1
    else:
        frozen_path = p.with_name('frozen-policies.json')
        frozen = json.loads(frozen_path.read_text())
        bind(frozen_path)
        dos = frozen[plan['opponent']].get('driver') == 'msdos1990'
        for policy, st in r['standings'].items():
            w,d,l = (st[k] for k in ('wins','draws','losses'))
            score = (w+d/2)/(w+d+l)
            check(math.isclose(score,st['score']), f'C{cycle} {policy}: score arithmetic')
            if dos:
                found = [line for line in text.splitlines()
                         if line.startswith(f'| {cycle} | ') and f'| {policy} |' in line]
                check(len(found)==1, f'C{cycle} {policy}: unique DOS row')
                if found:
                    cells = [s.strip() for s in found[0].strip('|').split('|')]
                    check(cells[-3:] == [f'{w} / {d} / {l}', f'{score:.1%}', str(st['errors'])],
                          f'C{cycle} {policy}: DOS numeric cells')
                counts['dos_standing_rows'] += 1
            else:
                row = (f'- {policy}: {w} wins / {d} draws / {l} losses; '
                       f"score {score:.1%}; {st['errors']} unscored errors.")
                check(row in section, f'C{cycle} {policy}: honest numeric row')
                counts['honest_standing_rows'] += 1
        for name, comp in r['comparisons'].items():
            metric = comp['metrics']['score']
            lo,hi = metric['interval_95']
            row = f"- {name}: {100*metric['mean']:+.1f} percentage points; 95% paired interval [{100*lo:+.1f}, {100*hi:+.1f}]"
            counts['contrasts'] += 1
            counts['intervals_95'] += 1
            if 'interval_98_3333' in metric:
                lo,hi = metric['interval_98_3333']
                row += f'; 98.3333% interval [{100*lo:+.1f}, {100*hi:+.1f}]'
                counts['intervals_98_3333'] += 1
            check(row+'.' in section, f'C{cycle} {name}: contrast/interval rendering')
    conclusion = p.with_name('CONCLUSION.md')
    if conclusion.exists():
        bind(conclusion)
        target = str(conclusion.relative_to(BASE))
        if f']({target})' in text:
            counts['conclusions'] += 1
        else:
            omissions.append(f'C{cycle}: existing CONCLUSION.md not linked.')

rendered_table_rows = re.findall(r'^\| \d+ \|', text, re.M)
check(len(rendered_table_rows)==counts['dos_standing_rows'], 'unreviewed/duplicate DOS table rows')
rendered_contrasts = re.findall(r'^- .*: [+-]\d+\.\d+ percentage points;', text,re.M)
check(len(rendered_contrasts)==counts['contrasts'], 'unreviewed/duplicate rendered contrasts')
for target in re.findall(r'\]\(([^)]+)\)',text):
    if re.match(r'\w+://', target):
        continue
    resolved = BASE / target.split('#')[0]
    check(resolved.exists(), f'broken link {target}')
    counts['links'] += 1

figure = BASE/'research/validation-summary-figure-v1'
for filename, record in json.loads((figure/'manifest.json').read_text()).items():
    check(sha(figure/filename)==record['sha256'], f'figure manifest {filename}')
    bind(figure/filename)
for filename, expected in json.loads((figure/'source-bindings.json').read_text()).items():
    check(sha(BASE/filename)==expected, f'figure aggregate binding {filename}')
    bind(BASE/filename)
for row in csv.DictReader((figure/'validation-summary.csv').open()):
    r = json.loads((BASE/row['result']).read_text())
    plan = json.loads((BASE/row['plan']).read_text())
    if int(row['cycle'])==17:
        name = next(m['name'] for m in plan['matches'] if m['policy']==row['candidate'])
        endpoint = r['endpoints'][name]
        metric = endpoint['paired_score_minus_half']
        bounds = [v-.5 for v in endpoint['all_attempt_score_bounds']]
        pairs = endpoint['complete_pairs']
        opponent = next(m['opponent'] for m in plan['matches'] if m['name']==name)
        check(float(row['confidence_percent']) > 98, f'figure C17 interval level {name}')
        ci = metric['interval_98_3333']
    else:
        name = row['candidate']+' minus '+row['comparator']
        metric = r['comparisons'][name]['metrics']['score']
        bounds = r['error_sensitivity'][name]['paired_cohort_effect_bounds']
        pairs = r['comparisons'][name]['complete_pairs']
        opponent = plan['opponent']
        ci = metric['interval_95']
        check(float(row['confidence_percent'])==95, f'figure C{r["cycle"]} interval level')
    expected = [100*metric['mean'],100*ci[0],100*ci[1],100*bounds[0],100*bounds[1]]
    actual = [float(row[k]) for k in ('effect_pp','lower_pp','upper_pp','finite_missing_lower_pp','finite_missing_upper_pp')]
    check(all(math.isclose(a,b,abs_tol=1e-10) for a,b in zip(actual,expected)), f'figure numeric row {row["label"]}')
    check(sha(BASE/row['result'])==row['result_sha256'], 'figure result SHA')
    check(sha(BASE/row['plan'])==row['plan_sha256'], 'figure plan SHA')
    check(int(row['complete_pairs'])==pairs, 'figure complete pairs')
    check(row['opponent']==opponent, 'figure opponent')
    check(row['setup_mode']==plan.get('setup_mode','referee'), 'figure setup context')
    check(row['families'].split(';')==plan['families'], 'figure families')
    counts['figure_rows'] += 1

receipt = dict(numeric_and_link_checks_passed=not failures, failures=failures,
               presentation_omissions=omissions, counts=counts,
               included_cycles=sorted(paths), exact_source_sha256=bindings,
               scope='Preserved overview snapshot and aggregate JSON/CSV only; no trajectories or saved games read. Later overview regeneration is outside this receipt.')
(HERE/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='exact_source_sha256'},indent=2))
