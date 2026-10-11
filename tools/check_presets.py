"""Check that every built-in deployment in src/core/presets.c is a legal army.

Each preset must hold 40 pieces in the counts of src/core/pieces.c.
"""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMY = dict(zip('123456789SBF', [1, 1, 2, 3, 4, 4, 4, 5, 8, 1, 6, 1]))


def main():
    source = (ROOT / 'src/core/presets.c').read_text()
    names = re.findall(r'^    "([A-Z ]+)",$', source.split('preset_names')[1].split('};')[0], re.M)
    table = source.split('presets[PRESETS] = {')[1].split('};')[0]
    armies = [''.join(re.findall(r'"([^"]*)"', block)) for block in table.split(',')[:-1]]
    failures = 0
    for name, army in zip(names, armies):
        counts = Counter(army)
        wrong = {k: counts[k] for k in ARMY if counts[k] != ARMY[k]}
        if len(army) != 40 or wrong or set(army) - set(ARMY):
            print(f'{name}: {len(army)} pieces, wrong counts {wrong}')
            failures += 1
    if len(names) != len(armies):
        print(f'{len(names)} names for {len(armies)} deployments')
        failures += 1
    print(f'{len(armies)} presets checked, {failures} failures')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
