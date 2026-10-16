"""Independent retained-receipt and trace-only modification checks."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'docs/ai-honest-campaign-2026-10-16/research/full-position-symmetry-prejitter';OLD=HERE.parent/'full-position-symmetry'
class Prejitter(unittest.TestCase):
 def test_protocol_exact_same_cohort(self):
  a=json.loads((HERE/'PROTOCOL.json').read_text());b=json.loads((OLD/'PROTOCOL.json').read_text())
  for key in ('reference','history','game_ids','sample_own_ordinals','maximum_own_decisions'):self.assertEqual(a[key],b[key])
 def test_only_additive_trace_patch(self):
  lines=(HERE/'trace-only.patch').read_text().splitlines();added=[x[1:]for x in lines if x.startswith('+')and not x.startswith('+++')];removed=[x for x in lines if x.startswith('-')and not x.startswith('---')]
  self.assertEqual(removed,[]);self.assertEqual(len(added),2);self.assertNotIn('random_', ''.join(added));self.assertIn('ai_trace_base(from,to,s)',added[0]);self.assertIn('if(tracing == 1)',added[1])
 def test_exact_original_choices_and_final_scores(self):
  a=json.loads((HERE/'result.json').read_text());b=json.loads((OLD/'result.json').read_text());self.assertEqual(len(a['records']),356)
  for row,old in zip(a['records'],b['records']):
   for key,value in old.items():self.assertEqual(row[key],value)
  self.assertEqual(a['counts']['trace_frozen_choice_parity'],712)
 def test_base_classification_recount(self):
  r=json.loads((HERE/'result.json').read_text());rows=r['records'];c=r['counts']
  self.assertEqual(sum(x['different_base_scores']for x in rows),c['changed_base_scores'])
  self.assertEqual(sum(bool(x['different_base_scores'])for x in rows),c['roots_with_changed_base_scores'])
  self.assertEqual(sum(x['changed_choice']and not x['different_base_scores']for x in rows),c['changed_choices_with_equivalent_base_map'])
  self.assertEqual(sum(x['equal_base_in_mirrored_frame']for x in rows),c['changed_choice_equal_base_in_mirrored_frame'])
if __name__=='__main__':unittest.main()
