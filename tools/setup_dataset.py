"""Frozen Classic setup corpora, independent partitions and referee-only provenance.

Stored armies are test inputs, never a policy feature or a training target. Old
datasets load from their pinned bytes without executing a current generator.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import random
import re

from feldmarschall import (BLUE, RED, COUNTS, GLYPHS, Position, ROOT,
                          describe_setup, presets, setup_neighbors, stress_setup,
                          valid_setup)

SCHEMA = 'classic-setup-dataset-v1'
DATASET_ID = 'classic-generalization-v1'
DEVELOPMENT = ('uniform-v1', 'rear-shell-v1', 'exposed-rear-v1',
               'forward-flag-v1', 'single-decoy-v1', 'scattered-guards-v1')
HELD_OUT = ('interior-shell-v1', 'flank-flag-v1', 'double-decoy-v1',
            'front-fence-v1', 'mobile-squads-v1', 'lane-vanguard-v1')
SPLITS = ('development', 'seed-validation', 'generator-holdout')
LANES = (0, 1, 4, 5, 8, 9)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def reflected(layout):
    return ''.join(layout[i:i+10][::-1] for i in range(0, 40, 10))


def canonical(layout):
    return min(layout, reflected(layout))


def finish(cells, rng, squads=False):
    pool = [g for g, n in zip(GLYPHS, COUNTS) for _ in range(n-cells.count(g))]
    if squads:
        ranks = list(GLYPHS[:10]); rng.shuffle(ranks)
        pool = [g for g in ranks for _ in range(pool.count(g))]
        positions = [r*10+c for r in range(4)
                     for c in (range(10) if r % 2 == 0 else range(9, -1, -1))]
        offset = rng.randrange(40)
        positions = positions[offset:] + positions[:offset]
        if rng.randrange(2): positions.reverse()
    else:
        rng.shuffle(pool)
        positions = range(40)
    for i in positions:
        if cells[i] is None: cells[i] = pool.pop()
    return ''.join(cells)


def shell(rng, flags, maximum=4, forbidden_bombs=()):
    cells = [None]*40
    flag = rng.choice(list(flags)); cells[flag] = 'F'
    neighbors = setup_neighbors(flag)
    eligible = [i for i in neighbors if i not in forbidden_bombs]
    guards = rng.sample(eligible, rng.randrange(min(maximum, len(eligible))+1))
    for i in guards: cells[i] = 'B'
    elsewhere = [i for i in range(40) if cells[i] is None
                 and i not in neighbors and i not in forbidden_bombs]
    for i in rng.sample(elsewhere, 6-len(guards)): cells[i] = 'B'
    return cells


def generate_army(family, rng):
    legacy = dict(zip(DEVELOPMENT[:5], ('uniform', 'fortified', 'unguarded', 'forward', 'decoy')))
    if family in legacy:
        return stress_setup(legacy[family], rng)
    if family == 'scattered-guards-v1':
        return finish(shell(rng, range(40), maximum=2), rng)
    if family == 'interior-shell-v1':
        return finish(shell(rng, range(10, 30)), rng)
    if family == 'flank-flag-v1':
        return finish(shell(rng, [r*10+c for r in range(4) for c in (0, 1, 8, 9)], maximum=3), rng)
    if family == 'double-decoy-v1':
        cells = [None]*40
        for center in (rng.choice((31, 32, 33)), rng.choice((36, 37, 38))):
            cells[center] = rng.choice('456789')
            for i in setup_neighbors(center): cells[i] = 'B'
        cells[rng.randrange(20)] = 'F'
        return finish(cells, rng)
    if family == 'front-fence-v1':
        cells = [None]*40
        while True:
            bombs = rng.sample(range(10), 6)
            if len(set(LANES)-set(bombs)) >= 2: break
        for i in bombs: cells[i] = 'B'
        cells[rng.randrange(10, 40)] = 'F'
        return finish(cells, rng)
    if family == 'mobile-squads-v1':
        cells = [None]*40
        cells[rng.randrange(40)] = 'F'
        for i in rng.sample([i for i, g in enumerate(cells) if g is None], 6): cells[i] = 'B'
        return finish(cells, rng, squads=True)
    if family == 'lane-vanguard-v1':
        cells = shell(rng, range(20, 40), maximum=3, forbidden_bombs=LANES)
        scouts_miners = list('999988'); rng.shuffle(scouts_miners)
        for i, rank in zip(LANES, scouts_miners): cells[i] = rank
        return finish(cells, rng)
    raise ValueError('Unknown setup generator: '+str(family))


def playable(layout):
    if not isinstance(layout, str) or not valid_setup(layout): return False
    for side in (RED, BLUE):
        board = Position(); board.place(side, layout)
        if not board.moves(side): return False
    return True


def legacy_exclusions():
    # Read public constants as data; no model, emulator or prediction is run.
    source = ROOT/'tools/campaign_template_beliefs.py'
    tree = ast.parse(source.read_text())
    templates = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'TEMPLATES' for t in node.targets))
    return dict(schema='classic-legacy-setup-exclusions-v1',
                layouts=sorted(set(templates) | {layout for _, layout in presets()}),
                sources={'campaign_template_beliefs.py': sha(source.read_bytes()),
                         'presets.c': sha((ROOT/'src/core/presets.c').read_bytes())})


def audit_documents(manifest, documents, exclusions):
    if manifest.get('schema') != SCHEMA or manifest.get('rules') != 'classic':
        raise ValueError('Unsupported Classic setup dataset')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*-v[1-9][0-9]*', manifest.get('id', '')):
        raise ValueError('Dataset requires an immutable descriptive version ID')
    if set(manifest['splits']) != set(SPLITS) or set(documents) != set(SPLITS):
        raise ValueError('Missing dataset partition')
    development = manifest['splits']['development']['families']
    if (manifest['splits']['seed-validation']['families'] != development
            or set(development) & set(manifest['splits']['generator-holdout']['families'])):
        raise ValueError('Generator holdout overlaps development families')
    legacy = exclusions.get('layouts', [])
    if not legacy or any(not isinstance(g, str) or not valid_setup(g) for g in legacy):
        raise ValueError('Invalid legacy setup exclusion reference')
    legacy = sorted(set(legacy) | {reflected(g) for g in legacy})
    minimum = manifest['minimum_legacy_hamming_distance']
    if type(minimum) is not int or not 1 <= minimum <= 40:
        raise ValueError('Invalid legacy distance threshold')
    seen, ids, coverage = set(), set(), {}
    for split in SPLITS:
        spec, doc = manifest['splits'][split], documents[split]
        families, count = spec['families'], spec['pairs_per_family']
        if (type(count) is not int or count < 1 or len(set(families)) != len(families)
                or not families or any(f not in (*DEVELOPMENT, *HELD_OUT) for f in families)):
            raise ValueError('Invalid dataset families or sample count')
        if (doc.get('schema') != 'classic-setup-records-v1' or doc.get('dataset_id') != manifest['id']
                or doc.get('split') != split or doc.get('families') != families
                or len(doc.get('records', [])) != len(families)*count):
            raise ValueError('Dataset partition metadata mismatch')
        coverage[split] = {}
        for family in families:
            coverage[split][family] = dict(pairs=count, armies=0, flag_rows=[0]*4,
                flag_columns=[0]*10, adjacent_bomb_guards=[0]*5, minimum_legacy_distance=40)
        for index, record in enumerate(doc['records']):
            family = families[index//count]
            expected_id = f'{split}/{family}/{index%count+1:04d}'
            if record.get('id') != expected_id or record.get('family') != family or expected_id in ids:
                raise ValueError('Duplicate or mismatched dataset record ID')
            ids.add(expected_id)
            for key in ('army_a', 'army_b'):
                layout = record.get(key)
                if not playable(layout): raise ValueError('Invalid or immobile Classic setup')
                unique = canonical(layout)
                if unique in seen: raise ValueError('Duplicate or mirrored setup across dataset partitions')
                seen.add(unique)
                distance = min(sum(a != b for a, b in zip(layout, old)) for old in legacy)
                if distance < minimum: raise ValueError('Setup is a legacy formation or near copy')
                info = describe_setup(layout); row = coverage[split][family]
                row['armies'] += 1
                row['flag_rows'][info['flag_row_from_front']] += 1
                row['flag_columns'][layout.index('F') % 10] += 1
                row['adjacent_bomb_guards'][info['adjacent_bomb_guards']] += 1
                row['minimum_legacy_distance'] = min(row['minimum_legacy_distance'], distance)
    return dict(schema='classic-setup-coverage-v1', dataset_id=manifest['id'],
                pairs=len(ids), unique_armies_including_reflection_check=len(seen),
                cross_split_duplicate_or_mirror_count=0, splits=coverage)


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or str(path) != name:
        raise ValueError('Unsafe dataset path')
    return path


def validate_bundle(manifest, files):
    declared = manifest.get('files', {})
    if not declared or set(files) != set(declared): raise ValueError('Missing dataset files')
    for name, record in declared.items():
        safe_name(name)
        if sha(files[name]) != record['sha256'] or len(files[name]) != record['bytes']:
            raise ValueError('Dataset integrity mismatch: '+name)
    documents = {split: json.loads(files[split+'.json']) for split in SPLITS}
    coverage = audit_documents(manifest, documents, json.loads(files['exclusions.json']))
    if json.loads(files['coverage.json']) != coverage:
        raise ValueError('Dataset coverage does not match actual records')
    return documents, coverage


def load_dataset(directory):
    root = Path(directory).resolve()
    raw = (root/'manifest.json').read_bytes(); manifest = json.loads(raw)
    files = {}
    for name in manifest.get('files', {}):
        path = root/str(safe_name(name))
        if not path.resolve().is_relative_to(root): raise ValueError('Dataset path escapes its directory')
        files[name] = path.read_bytes()
    documents, coverage = validate_bundle(manifest, files)
    return dict(manifest=manifest, manifest_bytes=raw, files=files,
                documents=documents, coverage=coverage)


def select_records(bundle, split, rounds, offset=0):
    if split not in SPLITS: raise ValueError('Unknown dataset partition')
    spec = bundle['manifest']['splits'][split]
    count = spec['pairs_per_family']
    if type(rounds) is not int or rounds < 1 or type(offset) is not int or offset < 0 or offset+rounds > count:
        raise ValueError('Dataset rounds/offset exceed its frozen records; records never wrap or repeat')
    rows = bundle['documents'][split]['records']
    return [record for i in range(len(spec['families'])) for record in rows[i*count+offset:i*count+offset+rounds]]


def validate_role(role,setup_mode):
    expected={'referee-v1':'referee','opponent-only-v1':'policy-owned-rotated-v1'}
    if role not in expected or setup_mode!=expected[role]:
        raise ValueError('Dataset role requires its explicit setup mode: referee-v1/referee or opponent-only-v1/policy-owned-rotated-v1')


def freeze_dataset(tournament, bundle, split, rounds, offset,role='referee-v1'):
    validate_role(role,tournament.metadata().get('setup_mode','referee'))
    selected = select_records(bundle, split, rounds, offset)
    pinned = {name: tournament.artifact('setup-dataset/'+name, data)
              for name, data in bundle['files'].items()}
    manifest_sha = tournament.artifact('setup-dataset/manifest.json', bundle['manifest_bytes'])
    tournament.set_metadata(dict(setup_dataset=dict(id=bundle['manifest']['id'], split=split,
        offset=offset, record_ids=[r['id'] for r in selected], manifest_sha256=manifest_sha,
        files=pinned,role=role,
        contract=('Frozen referee inputs only; no dataset metadata or enemy setup sent to honest policies.' if role=='referee-v1' else
                  'Frozen Army B is the opponent only; Army A is unused. First policy selects its own army through the frozen setup protocol. Both armies reflect horizontally when the owner is Blue. No corpus or enemy setup is sent to honest policies.'))))
    if role=='opponent-only-v1':
        pin=tournament.metadata()['setup_dataset']
        pin['selection_source_sha256']=tournament.artifact('setup-dataset/opponent-only-selector.py',Path(__file__).read_bytes())
        tournament.set_metadata(dict(setup_dataset=pin))


def frozen_schedule(metadata, artifact):
    """Validate a self-contained tournament's corpus and its exact selected cohort."""
    pin = metadata['setup_dataset']
    manifest_raw = artifact(pin['manifest_sha256']); manifest = json.loads(manifest_raw)
    files = {name: artifact(value) for name, value in pin['files'].items()}
    documents, _ = validate_bundle(manifest, files)
    role=pin.get('role','referee-v1')
    validate_role(role,metadata.get('setup_mode','referee'))
    if role=='opponent-only-v1':artifact(pin['selection_source_sha256'])
    if manifest['id'] != pin['id']:
        raise ValueError('Dataset tournament identity/setup mode mismatch')
    bundle = dict(manifest=manifest, documents=documents)
    selected = select_records(bundle, pin['split'], metadata['rounds'], pin['offset'])
    if (pin['record_ids'] != [r['id'] for r in selected]
            or metadata['families'] != manifest['splits'][pin['split']]['families']
            or metadata['planned_games'] != 2*len(selected)):
        raise ValueError('Dataset tournament cohort mismatch')
    rng = random.Random(metadata['seed'])
    return {i+1: dict(record, move_seed=rng.randrange(1, 60000),dataset_role=role) for i, record in enumerate(selected)}


def build_dataset(directory, identity=DATASET_ID, seed=2026101601, development_pairs=64, validation_pairs=128):
    specs = {'development': dict(families=list(DEVELOPMENT), pairs_per_family=development_pairs),
             'seed-validation': dict(families=list(DEVELOPMENT), pairs_per_family=validation_pairs),
             'generator-holdout': dict(families=list(HELD_OUT), pairs_per_family=validation_pairs)}
    if any(type(s['pairs_per_family']) is not int or s['pairs_per_family'] < 1 for s in specs.values()):
        raise ValueError('Positive sample counts required')
    exclusions = legacy_exclusions()
    forbidden = exclusions['layouts'] + [reflected(g) for g in exclusions['layouts']]
    manifest = dict(schema=SCHEMA, id=identity, rules='classic', generation_seed=seed,
        encoding='40 glyphs, front row first; columns a..j in each row; same as setup_squares',
        minimum_legacy_hamming_distance=12, splits=specs,
        protocol='Use development for tuning; freeze policies before either validation partition. Never train on validation layouts or outcomes.')
    seen, documents = set(), {}
    for split in SPLITS:
        records = []
        for family in specs[split]['families']:
            for index in range(specs[split]['pairs_per_family']):
                armies = []
                for side in ('a', 'b'):
                    for retry in range(10000):
                        key = f'{identity}/{seed}/{split}/{family}/{index}/{side}/{retry}'
                        rng = random.Random(int(sha(key.encode()), 16))
                        layout = generate_army(family, rng)
                        if (playable(layout) and canonical(layout) not in seen
                                and min(sum(a != b for a, b in zip(layout, old)) for old in forbidden) >= 12):
                            seen.add(canonical(layout)); armies.append(layout); break
                    else: raise ValueError('Unable to produce distinct playable setups')
                records.append(dict(id=f'{split}/{family}/{index+1:04d}', family=family,
                                    army_a=armies[0], army_b=armies[1]))
        documents[split] = dict(schema='classic-setup-records-v1', dataset_id=identity,
                               split=split, families=specs[split]['families'], records=records)
    coverage = audit_documents(manifest, documents, exclusions)
    files = {split+'.json': encoded(doc) for split, doc in documents.items()}
    files.update({'exclusions.json': encoded(exclusions), 'coverage.json': encoded(coverage),
        'sources/setup_dataset.py': Path(__file__).read_bytes(),
        'sources/feldmarschall.py': (ROOT/'tools/feldmarschall.py').read_bytes(),
        'sources/legacy-template-reference.py': (ROOT/'tools/campaign_template_beliefs.py').read_bytes(),
        'sources/legacy-presets.c': (ROOT/'src/core/presets.c').read_bytes()})
    manifest['files'] = {name: dict(sha256=sha(data), bytes=len(data)) for name, data in files.items()}
    validate_bundle(manifest, files)
    root = Path(directory); root.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    (root/'manifest.json').write_bytes(encoded(manifest))
    return coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    build = actions.add_parser('build'); build.add_argument('directory', type=Path)
    build.add_argument('--id', default=DATASET_ID); build.add_argument('--seed', type=int, default=2026101601)
    build.add_argument('--development-pairs', type=int, default=64)
    build.add_argument('--validation-pairs', type=int, default=128)
    check = actions.add_parser('verify'); check.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        report = (build_dataset(args.directory, args.id, args.seed, args.development_pairs, args.validation_pairs)
                  if args.action == 'build' else load_dataset(args.directory)['coverage'])
        print(json.dumps(report, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
