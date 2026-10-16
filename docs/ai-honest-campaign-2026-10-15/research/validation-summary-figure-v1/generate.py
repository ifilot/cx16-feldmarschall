"""Plot prespecified independent-validation aggregates; reads plans/results only."""
import csv
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/feldmarschall-figure-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(cycle):
    directory, = BASE.glob(f'cycle-{cycle:02d}-*')
    result_path, plan_path = directory/'result.json', directory/'plan.json'
    return json.loads(result_path.read_text()), json.loads(plan_path.read_text()), dict(
        result=str(result_path.relative_to(BASE)), result_sha256=digest(result_path),
        plan=str(plan_path.relative_to(BASE)), plan_sha256=digest(plan_path))


def rows():
    output = []
    definitions = [
        (26, 'DOS', 'Public template prior − validated native',
         'Same own deployment policy; original-DOS armies'),
        (41, 'DOS', 'Fortress + book − mixture + book',
         'Own deployment treatment; original-DOS armies'),
        (46, 'DOS', 'Compact back-row prior − validated native',
         'Same own deployment policy; original-DOS armies'),
        (14, 'DOS', 'Exact contact risk − native guard',
         'Common referee armies; seven stress families'),
        (25, 'Honest controlled contrast', 'Fortress − validated deployment mixture',
         'Against honest guard; original-DOS opponent armies'),
    ]
    for cycle, panel, label, context in definitions:
        result, plan, binding = load(cycle)
        assert len(plan['contrasts']) == len(result['comparisons']) == 1
        candidate, control = plan['contrasts'][0]
        key = candidate+' minus '+control
        comparison = result['comparisons'][key]
        metric = comparison['metrics']['score']
        sensitivity = result['error_sensitivity'][key]
        output.append(dict(cycle=cycle, panel=panel, label=label, context=context,
            estimand='Matched difference in score between candidate and control arms',
            candidate=candidate, comparator=control, opponent=plan['opponent'],
            setup_mode=result['setup_mode'], families=';'.join(plan['families']),
            effect_pp=100*metric['mean'], lower_pp=100*metric['interval_95'][0],
            upper_pp=100*metric['interval_95'][1], confidence_percent=95.0,
            complete_pairs=comparison['complete_pairs'],
            finite_missing_lower_pp=100*sensitivity['paired_cohort_effect_bounds'][0],
            finite_missing_upper_pp=100*sensitivity['paired_cohort_effect_bounds'][1],
            **binding))
    result, plan, binding = load(17)
    labels = {'row-prior-vs-context': 'Learned Flag-row teacher vs Context',
              'joint-vs-context': 'Joint Flag/Bomb teacher vs Context',
              'native-contact-vs-guard': 'Exact contact native vs guard'}
    assert set(labels) == set(result['endpoints'])
    for match in plan['matches']:
        endpoint = result['endpoints'][match['name']]
        metric = endpoint['paired_score_minus_half']
        output.append(dict(cycle=17, panel='Honest direct heads', label=labels[match['name']],
            context='Direct head-to-head; common referee armies; seven stress families',
            estimand='Candidate head-to-head score minus fair-null score 50%; NOT a policy-arm difference',
            candidate=match['policy'], comparator='Fair-null score 50%', opponent=match['opponent'],
            setup_mode=plan['setup_mode'], families=';'.join(plan['families']),
            effect_pp=100*metric['mean'], lower_pp=100*metric['interval_98_3333'][0],
            upper_pp=100*metric['interval_98_3333'][1], confidence_percent=98.33333333333333,
            complete_pairs=endpoint['complete_pairs'],
            finite_missing_lower_pp=100*(endpoint['all_attempt_score_bounds'][0]-.5),
            finite_missing_upper_pp=100*(endpoint['all_attempt_score_bounds'][1]-.5),
            **binding))
    return output


def review(data):
    # Independent manually transcribed aggregate anchors; catches unit/endpoint errors.
    expected = [(26, 19.318181818181817), (41, 4.978118161925602),
                (46, 17.830423940149625), (14, .3727634194831014),
                (25, 7.0), (17, .821428571428573),
                (17, 1.5357142857142847), (17, 4.321428571428576)]
    assert len(data) == 8
    for row, (cycle, effect) in zip(data, expected):
        assert row['cycle'] == cycle and abs(row['effect_pp']-effect) < 1e-10
        assert row['lower_pp'] <= row['effect_pp'] <= row['upper_pp']
        assert row['finite_missing_lower_pp'] <= row['finite_missing_upper_pp']
    assert data[3]['lower_pp'] < 0 < data[3]['upper_pp']
    assert all(row['confidence_percent'] == 95 for row in data[:5])
    assert all(abs(row['confidence_percent']-98.33333333333333) < 1e-12 for row in data[5:])
    return dict(passed=True, rows=8, c17_all_three_prespecified_heads_included=True,
                c14_null_dos_result_included=True, manually_transcribed_effect_anchors_match=True,
                only_result_and_plan_aggregate_inputs=True, no_pooling_or_ranking=True,
                intervals='Sampling bootstrap intervals; finite missing-score bounds are CSV-only.')


def plot(data):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [4, 1.5, 3]}, sharex=True)
    panels = [data[:4], data[4:5], data[5:]]
    titles = ['A  DOS validation: paired policy-arm score differences (95% primary intervals)',
              'B  Honest guard: paired policy-arm score difference (95% primary interval)',
              'C  Honest direct heads: score minus fair-null 50% (98.3333% intervals; three endpoints)']
    for ax, subset, title in zip(axes, panels, titles):
        ax.axvline(0, color='#64748b', linewidth=1, linestyle='--')
        for i, row in enumerate(subset):
            y = len(subset)-1-i
            ax.errorbar(row['effect_pp'], y,
                xerr=[[row['effect_pp']-row['lower_pp']], [row['upper_pp']-row['effect_pp']]],
                color='#164e63', marker='o', markersize=6, linewidth=2, capsize=4)
            ax.text(26.5, y, f"{row['effect_pp']:+.2f} [{row['lower_pp']:+.2f}, {row['upper_pp']:+.2f}]",
                    va='center', ha='left', fontsize=9)
        ax.set_yticks(range(len(subset)))
        ax.set_yticklabels([f"C{r['cycle']}  {r['label']}\n{r['context']}" for r in reversed(subset)], fontsize=9)
        ax.set_ylim(-.65, len(subset)-.35)
        ax.set_title(title, loc='left', fontsize=11, fontweight='bold', pad=13)
        ax.grid(axis='x', color='#e2e8f0', linewidth=.7)
        ax.set_axisbelow(True)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='y', length=0, pad=10)
    axes[-1].set_xlim(-5, 26)
    axes[-1].set_xlabel('Percentage points relative to the explicitly labelled comparator / fair null')
    fig.suptitle('Selected independent Classic validations: distinct questions, separate evidence', fontsize=15, x=.02, ha='left', y=.985)
    fig.text(.02, .025, 'Score = wins + ½ draws; errors remain unscored. Bars are sampling intervals, NOT finite missing-score bounds.\n'
             'Different opponents, setups and estimands: no pooled estimate, ranking, equivalence or target-readiness claim.', fontsize=10)
    fig.subplots_adjust(left=.43, right=.78, top=.91, bottom=.105, hspace=.67)
    fig.savefig(HERE/'validation-summary.png', dpi=180)
    fig.savefig(HERE/'validation-summary.pdf', metadata={'CreationDate': None})
    plt.close(fig)


if __name__ == '__main__':
    data = rows()
    with (HERE/'validation-summary.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    (HERE/'numeric-review.json').write_text(json.dumps(review(data), indent=2)+'\n')
    bindings = {row[key]: row[key+'_sha256'] for row in data for key in ('plan', 'result')}
    (HERE/'source-bindings.json').write_text(json.dumps(bindings, indent=2)+'\n')
    plot(data)
    manifest = {str(f.relative_to(HERE)): dict(bytes=f.stat().st_size, sha256=digest(f))
                for f in sorted(HERE.iterdir()) if f.is_file() and f.name != 'manifest.json'}
    (HERE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Eight rows generated; numeric review passed. Source bindings are in CSV.')
