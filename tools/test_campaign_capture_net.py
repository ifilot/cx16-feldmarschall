"""Public capture-net selection, frozen research parity and witness lifecycle."""
import ast,gzip,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from campaign_capture_net import candidates,certificate,net_selection,own_outcomes
from campaign_mobile_capture import _fork_own_moves,_fork_enemy_lost,_fork_public_key
from campaign_native_mobile import MobileCaptureBot
from feldmarschall import COUNTS,LAKES,square_name
ROOT=Path(__file__).resolve().parents[1];RESEARCH=ROOT/'docs/ai-honest-campaign-2026-10-15/research/capture-net-preflight-v1'
def fixture():
 cells=[254 if s in LAKES else 255 for s in range(100)]
 for s,owner,rank in((22,0,1),(0,0,0),(99,0,11),(89,0,10),(98,0,10),(11,1,6),(21,1,10),(9,1,11),(88,1,8)):cells[s]=16*owner|32|rank
 remaining=[0]*12;return cells,_fork_enemy_lost(cells,0,remaining),remaining,{0:(None,None,0),1:(None,None,0)}
def bot():
 result=MobileCaptureBot.__new__(MobileCaptureBot);result.adjustment_scope='quiet-net';result._net_plan=None;result._net_discard_reason=None;result.model=SimpleNamespace(army=0,plies=0);return result
class CaptureNetTests(unittest.TestCase):
 def test_research_functions_and_old_fork_methods_ast_unchanged(self):
  for before,after,names in((RESEARCH/'net.py',ROOT/'tools/campaign_capture_net.py',('capture','candidates','own_outcomes','certificate')),(ROOT/'docs/ai-honest-campaign-2026-10-15/research/capture-net-runtime-v1/before/campaign_native_mobile.py',ROOT/'tools/campaign_native_mobile.py',('_fork_event','_select_fork'))):
   trees=[ast.parse(p.read_text())for p in(before,after)]
   for name in names:
    nodes=[next(n for n in ast.walk(t)if isinstance(n,ast.FunctionDef)and n.name==name)for t in trees];self.assertEqual(ast.dump(nodes[0]),ast.dump(nodes[1]))
 def test_all_first20_proofs_exact_research_parity(self):
  rows=json.loads(gzip.decompress((RESEARCH/'first20-proofs.json.gz').read_bytes()))
  for row in rows:
   f=row['public_fixture'];state={int(k):tuple(v)for k,v in f['shuttle'].items()};args=(f['cells'],row['army'],f['lost'],f['remaining'],state);budget=[0,20000]
   native=certificate(*args,tuple(row['native']),budget);self.assertEqual(native,row['reports']['native'])
   net=certificate(*args,tuple(row['candidate']['move']),budget,row['candidate']);self.assertEqual(net,row['reports']['net']);self.assertEqual(budget[0],row['enemy_nodes'])
 def test_first_full_legal_candidate_and_missing_score_fallback(self):
  c,l,r,s=fixture();scores=dict.fromkeys(_fork_own_moves(c,0,s),0);parent=(22,23)
  selected,report=net_selection(c,0,l,r,scores,parent,s);self.assertEqual(selected,(22,12));self.assertEqual(report['selected_bound'],15)
  first=tuple(report['first_candidate']['move']);scores.pop(first)
  with patch('campaign_capture_net.certificate',side_effect=AssertionError('must not search replacement')):
   selected,report=net_selection(c,0,l,r,scores,parent,s)
  self.assertEqual(selected,parent);self.assertEqual(report['reason'],'first-candidate-absent-native-scores')
 def test_native_captures_terminal_and_caps_preserved(self):
  c,l,r,s=fixture();scores=dict.fromkeys(_fork_own_moves(c,0,s),0);parent=(22,23)
  scores[parent]=30000;self.assertEqual(net_selection(c,0,l,r,scores,parent,s)[0],parent);scores[parent]=0
  with patch('campaign_capture_net.certificate',return_value=dict(certified=False,inconclusive=True)):
   selected,report=net_selection(c,0,l,r,scores,parent,s)
  self.assertEqual(selected,parent);self.assertEqual(report['reason'],'global-node-cap')
  c[23]=16|32|8;l[8]-=1;scores=dict.fromkeys(_fork_own_moves(c,0,s),0)
  self.assertEqual(net_selection(c,0,l,r,scores,parent,s)[1]['reason'],'preserve-native-capture-or-terminal')
 def test_quiet_suicide_witness_and_one_use_lifecycle(self):
  c,l,r,s=fixture();scores=dict.fromkeys(_fork_own_moves(c,0,s),0);selected,report=net_selection(c,0,l,r,scores,(22,23),s)
  proof=report['net_certificate'];response=next(x for x in proof['responses']if not x['victim_alive']);key=response['public_key'];army,board,fallen,hidden,red,blue=json.loads(key);witness=tuple(response['response']);self.assertEqual(board[witness[1]],255)
  b=bot();chosen,root=b._select_net(c,0,l,r,scores,(22,23),s);self.assertEqual(chosen,selected)
  b._net_event(['moved',square_name(22),square_name(12)]);b.model.plies=1;b._net_event(['battle',square_name(11),square_name(12),'7','2']);self.assertEqual(b._net_plan['stage'],'ready')
  legal=_fork_own_moves(board,army,{0:tuple(red),1:tuple(blue)});parent=next(m for m in legal if m!=witness);follow,detail=b._select_net(board,army,fallen,hidden,dict.fromkeys(legal,0),parent,{0:tuple(red),1:tuple(blue)})
  self.assertEqual(follow,witness);self.assertEqual(detail['phase'],'followup');self.assertIsNone(b._net_plan)
 def test_uncertain_capture_witness_is_allowed_only_exact_key_and_legal(self):
  rows=json.loads(gzip.decompress((RESEARCH/'full361-proofs.json.gz').read_bytes()));case=None
  for row in rows:
   if not row['incremental']:continue
   for response in row['reports']['net'].get('responses',[]):
    army,board,lost,hidden,red,blue=json.loads(response['public_key']);w=tuple(response['response'])
    if response.get('victim_alive')is False and board[w[1]]<254 and not board[w[1]]&32:case=(response,army,board,lost,hidden,red,blue);break
   if case:break
  self.assertIsNotNone(case);response,army,c,l,r,red,blue=case;w=tuple(response['response']);s={0:tuple(red),1:tuple(blue)};legal=_fork_own_moves(c,army,s);parent=next(m for m in legal if m!=w)
  b=bot();b.model.army=army;b._net_plan=dict(stage='ready',states={response['public_key']:w},bound=15)
  selected,detail=b._select_net(c,army,l,r,dict.fromkeys(legal,0),parent,s);self.assertEqual(selected,w);self.assertEqual(detail['phase'],'followup')
  b._net_plan=dict(stage='ready',states={response['public_key']:w},bound=15);scores=dict.fromkeys(legal,0);scores.pop(w)
  self.assertEqual(b._select_net(c,army,l,r,scores,parent,s)[1]['reason'],'unmatched-or-illegal-public-witness');self.assertIsNone(b._net_plan)
 def test_reset_correction_mismatch_and_immediate_win_dominate(self):
  c,l,r,s=fixture();b=bot();key=_fork_public_key(c,0,l,r,s)
  for command in('new','rules','custom','position','setup','seed','played'):
   b._net_plan=dict(stage='ready',states={key:(22,12)},bound=15);b._net_event([command]);self.assertIsNone(b._net_plan)
  b._net_plan=dict(stage='ready',states={key:(22,12)},bound=15)
  self.assertEqual(b._select_net(c,0,l,r,{(22,12):0,(22,23):30000},(22,23),s)[0],(22,23));self.assertIsNone(b._net_plan)
  b._net_plan=dict(stage='ready',states={'wrong':(22,12)},bound=15)
  self.assertEqual(b._select_net(c,0,l,r,{(22,23):0},(22,23),s)[0],(22,23));self.assertIsNone(b._net_plan)
 def test_private_nibbles_counts_and_no_strategy_fusion_outcomes(self):
  c,l,r,s=fixture();c[88]=16|64|12;r[8]=1;l=_fork_enemy_lost(c,0,r);scores=dict.fromkeys(_fork_own_moves(c,0,s),0);reference=None
  for nibble in(0,7,11,12):
   c[88]=(c[88]&240)|nibble;result=net_selection(c,0,l,r,scores,(22,23),s)
   if reference is None:reference=result
   self.assertEqual(result,reference)
  bad=r[:];bad[11]=1;self.assertEqual(net_selection(c,0,l,bad,scores,(22,23),s)[1]['reason'],'inconsistent-public-inventory')
if __name__=='__main__':unittest.main()
