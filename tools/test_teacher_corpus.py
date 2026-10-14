"""Check phase/side coverage, public replay and validation quarantine."""
from collections import Counter
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from build_teacher_corpus import build, extract, select
from feldmarschall import ROOT
from train_teacher_student import own_initial, public_record


class TeacherCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ROOT / 'docs/ai-runs/teacher-rollout-correction-development-20261014.zip') as archive:
            cls.games = [json.loads(line) for line in archive.read('games.jsonl').splitlines()]

    def test_selection_ignores_outcome_and_both_sides_share_split(self):
        selected = select(self.games, 2)
        altered = copy.deepcopy(self.games)
        for game in altered: game['winner'] = 'arbitrary'; game['reason'] = 'arbitrary'
        self.assertEqual(selected, select(altered, 2))
        records = list(extract(self.games, selected, 'test'))
        coverage = Counter((r['source']['group'], r['source']['phase'], r['input']['army']) for r in records)
        self.assertEqual(len(coverage), 7 * 3 * 2)
        self.assertEqual(set(coverage.values()), {2})
        for record in records:
            game = self.games[record['source']['game_index']]
            army = record['input']['army']
            self.assertEqual(own_initial(record['input'], record['public_history']), game['deployments'][army])
            self.assertEqual(len(record['public_history']), record['source']['ply'])
            self.assertEqual(public_record(record)['split_group'], f"{game['group']}:{game['seed']}")
            for cell in bytes.fromhex(record['input']['board_hex']):
                if cell < 254 and bool(cell & 16) != bool(army) and not cell & 32:
                    self.assertEqual(cell & 15, 12)
            self.assertEqual(set(record), {'id', 'source', 'input', 'public_history'})

    def test_validation_runs_are_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / 'provenance.json').write_text(json.dumps({'phase': 'validation', 'suite': 'broad'}))
            with self.assertRaisesRegex(ValueError, 'development'):
                build(run, run / 'output', 2)
            self.assertFalse((run / 'output').exists())


if __name__ == '__main__': unittest.main()
