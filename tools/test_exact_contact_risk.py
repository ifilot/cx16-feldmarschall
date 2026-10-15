"""Independent exact-enumeration audit for the native contact-risk formula."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import shlex
import subprocess
import tempfile

from ai_registry import ROOT, build_policy, get_policy
from feldmarschall import battle

ONE = 1 << 22


def fall(n, k):
    return math.prod(range(n-k+1, n+1)) if 0 <= k <= n else 0


def formula(ranks, moved, actor, contacts):
    """Exact rational transcription, separate from the native arithmetic."""
    inventory = Counter(ranks)
    mobile = sum(rank < 10 for rank in ranks)
    unmoved = len(ranks)-moved
    immobile = len(ranks)-mobile
    dangerous = sum(rank < 10 and battle(rank, actor) == 'attacker' for rank in ranks)
    total = Fraction(0)
    for size in range(1, len(contacts)+1):
        for subset in itertools.combinations(contacts, size):
            b = sum(position >= moved for position, far in subset)
            f = sum(far for position, far in subset)
            n = len(subset)-f
            if f and battle(8, actor) != 'attacker':
                continue
            denominator = fall(unmoved, b)*fall(mobile, f+n)
            if denominator:
                value = Fraction(fall(unmoved-immobile, b)*fall(inventory[8], f)
                                 *fall(dangerous-f, n), denominator)
                total += value if size % 2 else -value
    return total


def arrangements(ranks, moved):
    return [p for p in set(itertools.permutations(ranks)) if all(rank < 10 for rank in p[:moved])]


def enumerate_probability(worlds, actor, contacts):
    hits = sum(any(p[position] < 10 and (not far or p[position] == 8)
                   and battle(p[position], actor) == 'attacker'
                   for position, far in contacts) for p in worlds)
    return Fraction(hits, len(worlds))


def cases():
    """Exhaustive small inventory/contact categories, plus random larger cases."""
    actors = (0, 1, 7, 8, 9, 11)
    for size in range(1, 5):
        for ranks in itertools.combinations_with_replacement((0, 8, 9, 10, 11), size):
            counts = Counter(ranks)
            if counts[0] > 1 or counts[9] > 1 or counts[11] > 1:
                continue
            mobile = sum(rank < 10 for rank in ranks)
            for moved in range(mobile+1):
                worlds = arrangements(ranks, moved)
                for near_moved in range(min(moved, 4)+1):
                    for far_moved in range(min(moved-near_moved, 4-near_moved)+1):
                        for near_unmoved in range(min(size-moved, 4-near_moved-far_moved)+1):
                            for far_unmoved in range(min(size-moved-near_unmoved,
                                                        4-near_moved-far_moved-near_unmoved)+1):
                                contacts = ([(n, False) for n in range(near_moved)]
                                            + [(near_moved+n, True) for n in range(far_moved)]
                                            + [(moved+n, False) for n in range(near_unmoved)]
                                            + [(moved+near_unmoved+n, True) for n in range(far_unmoved)])
                                if not contacts:
                                    continue
                                for actor in actors:
                                    yield ranks, moved, actor, contacts, worlds, 'exhaustive-small'
    rng = random.Random(2098201)
    pool = (0, 1, 6, 7, 8, 8, 9, 10, 10, 11)
    for _ in range(240):
        ranks = tuple(sorted(rng.sample(pool, rng.randint(5, 7))))
        moved = rng.randrange(sum(rank < 10 for rank in ranks)+1)
        contacts = [(n, bool(rng.randrange(2))) for n in rng.sample(range(len(ranks)), rng.randint(1, 4))]
        yield ranks, moved, rng.choice(actors), contacts, arrangements(ranks, moved), 'random-larger'


def run():
    policy = get_policy('student-guard-v1-normal')
    common = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Wno-format-overflow', '-Isrc/core']
    common += ['-I'+p for p in policy.get('include_dirs', [])]
    defines = ['-D'+p for p in policy['defines']]
    links = [p for p in policy['sources'] if p not in ('src/native/engine.c', 'src/core/ai.c')]
    rows, inputs, hist = [], [], Counter()
    for ranks, moved, actor, contacts, worlds, group in cases():
        actual = enumerate_probability(worlds, actor, contacts)
        theoretical = formula(ranks, moved, actor, contacts)
        assert actual == theoretical, (ranks, moved, actor, contacts, actual, theoretical)
        inventory = Counter(ranks)
        kinds = [int(far) | (2 if position < moved else 0) for position, far in contacts]
        inputs.append(' '.join(map(str, (actor, len(ranks)-moved, *(inventory[n] for n in range(12)),
                                        len(kinds), *kinds))))
        rows.append(actual)
        hist[group] += 1
    with tempfile.TemporaryDirectory(prefix='exact-contact-risk-') as temp:
        executable = Path(temp)/'mechanism'
        command = [*common, *defines, '-DAI_EXACT_CONTACT_RISK', 'tests/ai_exact_contact_risk_test.c',
                   *links, '-o', str(executable)]
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        mechanism = json.loads(subprocess.run([str(executable)], check=True, capture_output=True, text=True).stdout)
        assert mechanism['passed']
        costs = []
        for enabled in (False, True):
            cost_program = Path(temp)/('cost-guard' if enabled else 'cost-default')
            cost_command = [*common, *defines, *(['-DAI_EXACT_CONTACT_RISK'] if enabled else []),
                            'tests/ai_contact_risk_cost.c', *links, '-o', str(cost_program)]
            subprocess.run(cost_command, cwd=ROOT, check=True, capture_output=True, text=True)
            measurements = [json.loads(subprocess.run([str(cost_program)], check=True,
                                                     capture_output=True, text=True).stdout) for _ in range(3)]
            measurements.sort(key=lambda m: m['seconds'])
            costs.append(dict(enabled=enabled, median=measurements[1], measurements=measurements))
        native = subprocess.run([str(executable), 'prob'], input='\n'.join(inputs)+'\n',
                                check=True, capture_output=True, text=True)
        outputs = list(map(int, native.stdout.splitlines()))
        assert len(outputs) == len(rows)
        differences = [abs(Fraction(output, ONE)-actual) for output, actual in zip(outputs, rows)]
        maximum = max(differences)
        assert maximum <= Fraction(128, ONE), maximum
        # Existing policy source and build identity remain exactly unchanged
        # when the new macro is absent.
        frozen, receipt = build_policy(policy['id'])
        current = Path(temp)/'default'
        default_command = [*common, '-DFELDMARSCHALL_AI_ID="'+policy['id']+'"', *defines,
                           '-o', str(current), *policy['sources']]
        subprocess.run(default_command, cwd=ROOT, check=True, capture_output=True, text=True)
        current_sha = hashlib.sha256(current.read_bytes()).hexdigest()
        frozen_sha = hashlib.sha256(frozen.read_bytes()).hexdigest()
        assert current_sha == frozen_sha, (current_sha, frozen_sha)
    return dict(passed=True, kind='exact-contact-risk-enumeration-audit', strength_evidence=False,
                cases=len(rows), cases_by_group=dict(hist), rational_formula_matches_every_enumeration=True,
                probability_fixed_point_bits=22, max_absolute_probability_error=float(maximum),
                maximum_error_in_q22_units=float(maximum*ONE),
                native_mechanism=mechanism, microseconds_per_probability_call=mechanism['seconds']*1e6/mechanism['benchmark_calls'],
                full_decision_cost=costs,
                median_full_decision_slowdown=costs[1]['median']['seconds']/costs[0]['median']['seconds'],
                default_byte_identical=True, frozen_default_sha256=frozen_sha,
                frozen_native_receipt=receipt,
                test_case_sha256=hashlib.sha256(('\n'.join(inputs)+'\n').encode()).hexdigest(),
                native_output_sha256=hashlib.sha256(native.stdout.encode()).hexdigest(),
                commands=[shlex.join(command), shlex.join(default_command)],
                source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                               ('src/core/ai.c', 'tests/ai_exact_contact_risk_test.c', 'tests/ai_contact_risk_cost.c', 'tools/test_exact_contact_risk.py')},
                assumptions=['Uniform complete assignments conditional on rank counts and public moved/unmoved status; narrower battle/history masks and behavior are deliberately omitted.',
                             'At most one opponent attack occurs: payoff is the worst available lethal attack. Equal-rank exchanges have zero net loss.',
                             'Root inventory stays frozen during speculative occupancy changes; this does not condition assignments on hypothetical survival.',
                             'Enemy attack feasibility ignores opponent two-squares restrictions, as the original danger routine does.',
                             'Formula is exact under stated prior. Native evaluation uses Q22 arithmetic and rounds material scores, with quantified finite precision.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    text = json.dumps(run(), indent=2)+'\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end='')
