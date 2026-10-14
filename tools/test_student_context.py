"""Public inventory features must agree with their counts and preserve teacher choices."""
import json
import unittest

from feldmarschall import ROOT, Engine
from train_teacher_student import label_record, public_record


class StudentContextTests(unittest.TestCase):
    def test_features_follow_only_disclosed_inventory(self):
        cases = [json.loads(line) for line in (ROOT / 'docs/ai-mission-cases/cases.jsonl').read_text().splitlines()]
        record = cases[4]
        info = record['input']; army = info['army']
        cells = bytes.fromhex(info['board_hex']); lost = bytes.fromhex(info['enemy_lost_hex'])
        remaining = [max(0, n - lost[r]) for r, n in enumerate([1,1,2,3,4,4,4,5,8,1,6,1])]
        mobile = sum(remaining[:10]); miners = 0; unknown = 0
        for cell in cells:
            if cell >= 254: continue
            if bool(cell & 16) == bool(army): miners += (cell & 15) == 7
            elif cell & 32: remaining[cell & 15] -= 1
            elif not cell & 64: unknown += 1
        engine = Engine(str(ROOT / 'build/feldmarschall-teacher-observer-context'))
        try:
            engine.send(f"features {army} {info['enemy_lost_hex']} {info['board_hex']} 1")
            rows = []
            while True:
                words = engine.read().split()
                if words[0] == 'features_done': break
                self.assertEqual(words[0], 'feature')
                src, dst, *features = map(int, words[1:])
                self.assertEqual(len(features), 21)
                self.assertEqual(features[16:20], [remaining[10]*255//unknown if unknown else 0,
                                                   remaining[11]*255//unknown if unknown else 0, miners, mobile])
                self.assertEqual(features[20], 10 + (src//10-dst//10 if army else dst//10-src//10))
                rows.append(features)
            self.assertTrue(rows)
        finally: engine.close()

    def test_context_observer_preserves_teacher_and_original_features(self):
        cases = [json.loads(line) for line in (ROOT / 'docs/ai-mission-cases/cases.jsonl').read_text().splitlines()]
        for case in (cases[4], next(c for c in cases if c['input']['army'] != cases[4]['input']['army'])):
            record = public_record(case)
            teacher = str(ROOT / 'build/feldmarschall-teacher-rollout')
            old = label_record((record, str(ROOT / 'build/feldmarschall-teacher-observer'), teacher, 2))
            new = label_record((record, str(ROOT / 'build/feldmarschall-teacher-observer-context'), teacher, 2))
            self.assertEqual(old['nodes'], new['nodes'])
            self.assertEqual(len(old['rows']), len(new['rows']))
            for a, b in zip(old['rows'], new['rows']):
                self.assertEqual(a['features'], b['features'][:16])
                self.assertEqual({k:v for k,v in a.items() if k != 'features'},
                                 {k:v for k,v in b.items() if k != 'features'})


if __name__ == '__main__': unittest.main()
