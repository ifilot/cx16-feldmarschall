"""Synthetic SQL and arithmetic contracts for four-execution interaction analysis."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from feldmarschall import COUNTS,GLYPHS
from new_campaign_inner_guard_factorial import LABELS,analyze,reflected

BASE=''.join(g*n for g,n in zip(GLYPHS,COUNTS));GUARD=BASE[1]+BASE[0]+BASE[2:];OPP=BASE[10:]+BASE[:10]

class FactorialContracts(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='factorial-tests-');self.root=Path(self.temp.name);self.rounds=3
  self.protocol=self.root/'protocol.json';self.protocol.write_text(json.dumps(dict(schema='inner-guard-factorial-v1',seed=42,rounds=self.rounds)))
  self.inputs={label:(self.root/(label+'.fmtour'),label+'-v1-normal')for label in LABELS}
  self.scores={label:[[0.,0.]for _ in range(self.rounds)]for label in LABELS}
 def tearDown(self):self.temp.cleanup()
 def write(self):
  for label,(path,policy)in self.inputs.items():
   if path.exists():path.unlink()
   db=sqlite3.connect(path);db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE games(id INTEGER,pair_id INTEGER,family TEXT,red TEXT,blue TEXT,seed INTEGER,red_setup TEXT,blue_setup TEXT,result TEXT);')
   metadata=dict(rules='classic',status='complete',seed=42,rounds=self.rounds,planned_games=2*self.rounds,setup_mode='policy-owned-rotated-v1',setup_owner=policy,families=['original-dos'],max_plies=1000,participants=[dict(policy=dict(id=policy,source_sha256=label+'-source')),dict(policy=dict(id='dos',source_sha256='same-dos-source'),executable_sha256='same-dos-runtime')])
   db.executemany('INSERT INTO metadata VALUES(?,?)',[(k,json.dumps(v))for k,v in metadata.items()])
   own=GUARD if label.endswith('guard')else BASE
   for pair in range(1,self.rounds+1):
    for n,side in enumerate(('red','blue')):
     value=self.scores[label][pair-1][n]
     result='error'if value is None else'draw'if value==.5 else side if value==1 else('blue'if side=='red'else'red')
     row=(2*pair-1+n,pair,'original-dos',policy if side=='red'else'dos',policy if side=='blue'else'dos',100+pair,own if side=='red'else reflected(OPP),OPP if side=='red'else reflected(own),result)
     db.execute('INSERT INTO games VALUES(?,?,?,?,?,?,?,?,?)',row)
   db.commit();db.close()
 def result(self):return analyze(self.inputs,self.protocol,replicates=2000)
 def test_constant_interaction_bootstrap_and_four_distinct_source_pins(self):
  for pair in range(self.rounds):
   self.scores['book_guard'][pair]=[1.,1.];self.scores['native_base'][pair]=[.5,.5];self.scores['native_guard'][pair]=[1.,1.]
  self.write();r=self.result();self.assertEqual(r['common_complete_case_interaction']['mean'],.5);self.assertEqual(r['common_complete_case_interaction']['interval_95'],[.5,.5]);self.assertEqual(r['all_planned_pairs_arbitrary_error_bounds'],[.5,.5]);self.assertEqual(len({s['sha256']for s in r['sources'].values()}),4)
 def test_common_four_arm_complete_pair_not_mismatched_marginal_means(self):
  self.scores['book_guard'][0]=[1.,1.]
  self.scores['native_guard'][1]=[1.,1.];self.scores['book_base'][1]=[None,0.]
  self.scores['book_guard'][2]=[None,0.]
  self.write();r=self.result();self.assertEqual(r['common_four_arm_complete_pairs'],1);self.assertEqual(r['common_complete_case_interaction']['mean'],1.)
  self.assertEqual(r['pairs_with_any_error'],2)
  self.assertEqual(r['all_planned_pairs_arbitrary_error_bounds'],[-1/6,1/6])
 def test_all_errors_are_arbitrary_bounds_not_scored_or_dropped(self):
  self.scores={label:[[None,None]for _ in range(self.rounds)]for label in LABELS};self.write();r=self.result();self.assertIsNone(r['common_complete_case_interaction']);self.assertEqual(r['all_planned_pairs_arbitrary_error_bounds'],[-2.,2.]);self.assertEqual(r['attempted_games'],24)
 def test_missing_planned_pair_rejected(self):
  self.write();db=sqlite3.connect(self.inputs['native_guard'][0]);db.execute('DELETE FROM games WHERE pair_id=2');db.commit();db.close()
  with self.assertRaises(ValueError):self.result()
 def test_unmatched_seed_rejected(self):
  self.write();db=sqlite3.connect(self.inputs['native_guard'][0]);db.execute('UPDATE games SET seed=999 WHERE pair_id=2');db.commit();db.close()
  with self.assertRaisesRegex(ValueError,'Unmatched four-arm'):self.result()
 def test_own_armies_must_match_within_placement_level(self):
  self.write();path=self.inputs['native_base'][0];db=sqlite3.connect(path);db.execute('UPDATE games SET red_setup=? WHERE red=?',(GUARD,self.inputs['native_base'][1]));db.execute('UPDATE games SET blue_setup=? WHERE blue=?',(reflected(GUARD),self.inputs['native_base'][1]));db.commit();db.close()
  with self.assertRaisesRegex(ValueError,'Own armies differ'):self.result()
 def test_all_four_opponent_armies_must_match(self):
  self.write();db=sqlite3.connect(self.inputs['native_guard'][0]);db.execute('UPDATE games SET blue_setup=? WHERE red=?',(BASE,self.inputs['native_guard'][1]));db.execute('UPDATE games SET red_setup=? WHERE blue=?',(reflected(BASE),self.inputs['native_guard'][1]));db.commit();db.close()
  with self.assertRaisesRegex(ValueError,'Unmatched four-arm'):self.result()
 def test_reusing_control_file_or_policy_is_rejected(self):
  self.write();self.inputs['native_base']=self.inputs['book_base']
  with self.assertRaisesRegex(ValueError,'distinct execution'):self.result()
 def test_incomplete_tournament_cannot_be_analyzed(self):
  self.write();db=sqlite3.connect(self.inputs['book_base'][0]);db.execute('UPDATE metadata SET value=? WHERE key=?',(json.dumps('running'),'status'));db.commit();db.close()
  with self.assertRaisesRegex(ValueError,'status'):self.result()
 def test_scores_pair_by_side_before_interaction(self):
  for pair in range(self.rounds):self.scores['book_guard'][pair]=[1.,0.];self.scores['native_guard'][pair]=[.5,.5]
  self.write();r=self.result();self.assertEqual(r['common_complete_case_interaction']['mean'],0.);self.assertEqual(r['all_planned_pairs_arbitrary_error_bounds'],[0.,0.])

if __name__=='__main__':unittest.main()
