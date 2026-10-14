"""Verify own-history reconstruction, cold restore and producer oracle exclusion."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from feldmarschall import ROOT
from train_teacher_student import own_initial, public_record, label_record, require_teacher_gate, canonical_shuttle


class ProducerInputs(unittest.TestCase):
    def test_own_initial_from_permitted_history(self):
        with zipfile.ZipFile(ROOT / 'docs/ai-diagnostics/positions-20261014.zip') as archive:
            records = [json.loads(line) for line in archive.read('positions.jsonl').splitlines()]
        for record in records:
            self.assertEqual(own_initial(record['input'], record['public_history']),
                             record['replay']['deployments'][record['input']['army']])

    def test_oracle_fields_cannot_reach_labels(self):
        cases = [json.loads(line) for line in (ROOT / 'docs/ai-mission-cases/cases.jsonl').read_text().splitlines()]
        original = cases[4]
        altered = copy.deepcopy(original)
        altered.update(referee_board='arbitrary truth', evidence='arbitrary oracle',
                       labels=['private flag'], replay={'deployments':['hidden','hidden']}, own_initial_setup=None)
        a, b = public_record(original), public_record(altered)
        self.assertEqual(a, b)
        self.assertEqual(set(a), {'id', 'input', 'public_history', 'split_group'})
        programs = (str(ROOT / 'build/feldmarschall-teacher-observer'), str(ROOT / 'build/feldmarschall-teacher-rollout'), 2)
        first, second = label_record((a, *programs)), label_record((b, *programs))
        self.assertEqual(first, second)
        self.assertEqual({r['history'] for r in first['rows']}, {'full', 'cold'})
        self.assertEqual(len({r['split_group'] for r in first['rows']}), 1)
        self.assertTrue(all(len(r['features']) == 16 and abs(r['target']) <= 192 for r in first['rows']))
        self.assertTrue(any(r['features'][2] == 0 for r in first['rows']))

    def test_training_requires_teacher_strength(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'gate.json'; path.write_text('{"both_gates_passed": false}')
            with self.assertRaises(ValueError): require_teacher_gate(path)

    def test_unstarted_repetition_coordinates_are_not_observations(self):
        self.assertEqual(canonical_shuttle('000000000000'), 'ffffffff0000')
        self.assertEqual(canonical_shuttle('0a0014000100'), '0aff14ff0100')
        with zipfile.ZipFile(ROOT / 'docs/ai-diagnostics/positions-20261014.zip') as archive:
            inputs = [json.loads(line) for line in archive.read('positions.jsonl').splitlines()]
        record = public_record(next(r for r in inputs if not r['public_history']))
        result = label_record((record, str(ROOT / 'build/feldmarschall-teacher-observer'),
                               str(ROOT / 'build/feldmarschall-teacher-rollout'), 2))
        self.assertTrue(result['rows'])


if __name__ == '__main__': unittest.main()
