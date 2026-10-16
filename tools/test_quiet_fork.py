"""Public fork proof, witness keys and lifecycle; no saved games."""
import ast,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from campaign_mobile_capture import (fork_selection,_fork_certificate,_fork_public_key,
    _fork_enemy_lost,_fork_successors,_fork_shuttle,_fork_own_moves,_fork_record,_fork_support)
from campaign_native_mobile import MobileCaptureBot
from campaign_belief_values import worths
from feldmarschall import COUNTS,LAKES,square_name
ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'docs/ai-honest-campaign-2026-10-15/research/disclosed-fork-preflight-v1'

def fixture():
 cells=[254 if sq in LAKES else 255 for sq in range(100)]
 for sq,owner,rank in ((31,0,1),(99,0,11),(89,0,10),(98,0,10),(0,1,11),(20,1,2),(22,1,3),(88,1,8)):
  cells[sq]=owner*16|32|rank
 lost=COUNTS[:]
 for rank in(11,2,3,8):lost[rank]-=1
 return cells,lost,[0]*12,{0:(None,None,0),1:(None,None,0)}

def barebot():
 bot=MobileCaptureBot.__new__(MobileCaptureBot);bot.adjustment_scope='quiet-fork'
 bot._fork_plan=None;bot._fork_discard_reason=None;bot.model=SimpleNamespace(army=0,plies=0)
 return bot

class QuietForkTests(unittest.TestCase):
 def test_old_function_bodies_are_ast_identical(self):
  before=ROOT/'docs/ai-honest-campaign-2026-10-15/research/quiet-fork-runtime-v1/before/campaign_mobile_capture.py'
  trees=[ast.parse(p.read_text())for p in(before,ROOT/'tools/campaign_mobile_capture.py')]
  for name in('cdiv','stable_trunc','adjustments','integer_floor','quiet_threat','quiet_adjustments'):
   nodes=[next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)for tree in trees]
   self.assertEqual(ast.dump(nodes[0]),ast.dump(nodes[1]))
 def test_first20_native_common_proofs_match_frozen_research(self):
  data=json.loads((ROOT/'docs/ai-honest-campaign-2026-10-15/research/quiet-fork-runtime-v1/corrected-first20-fixtures.json').read_text())
  common=json.loads((RESEARCH/'common-result.json').read_text())
  lookup={(r['game'],r['ply'],tuple(r['fork'])):r for r in common['results']}
  for row in data['results']:
   f=row['public_fixture'];state={int(k):tuple(v)for k,v in f['shuttle'].items()}
   proof=_fork_certificate(f['cells'],row['army'],f['lost'],f['remaining'],state,tuple(row['move']),[0,20000])
   self.assertEqual(proof,lookup[row['game'],row['ply'],tuple(row['move'])]['reports']['fork'])
 def test_restricted_proofs_match_original_actor_witnesses(self):
  data=json.loads((ROOT/'docs/ai-honest-campaign-2026-10-15/research/quiet-fork-runtime-v1/corrected-first20-fixtures.json').read_text())
  for row in data['results']:
   f=row['public_fixture'];state={int(k):tuple(v)for k,v in f['shuttle'].items()}
   proof=_fork_certificate(f['cells'],row['army'],f['lost'],f['remaining'],state,tuple(row['move']),[0,20000],[v['square']for v in row['victims']])
   for response in proof.get('responses',[]):response.pop('public_key',None)
   self.assertEqual(proof,row['proof'])
 def test_corrected_fixtures_have_consistent_counts_and_exact_prefix_metadata(self):
  path=ROOT/'docs/ai-honest-campaign-2026-10-15/research/quiet-fork-runtime-v1/corrected-first20-fixtures.json'
  data=json.loads(path.read_text());self.assertEqual(data['old_proofs_exactly_equal'],60)
  for row in data['results']:
   f=row['public_fixture'];self.assertEqual(_fork_enemy_lost(f['cells'],row['army'],f['remaining']),f['lost'])
   self.assertTrue(row['native_public_verified'])
 def test_material_fork_selects_plan_without_score_bonus(self):
  cells,lost,remaining,state=fixture();scores=dict.fromkeys(_fork_own_moves(cells,0,state),0);parent=(31,30);scores[parent]=100
  selected,report=fork_selection(cells,0,lost,remaining,scores,parent,state)
  self.assertEqual(selected,(31,21));self.assertEqual(report['selected_bound'],75)
  self.assertTrue(report['witness_plan']);self.assertEqual(scores[parent],100)
  for key,move in report['witness_plan'].items():
   army,board,fallen,hidden,red,blue=json.loads(key)
   self.assertEqual(_fork_enemy_lost(board,army,hidden),fallen)
   self.assertIn(tuple(move),_fork_own_moves(board,army,{0:tuple(red),1:tuple(blue)}))
 def test_second_enemy_flag_capture_refutes_a_material_positive_witness(self):
  cells=[254 if sq in LAKES else 255 for sq in range(100)]
  for square,owner,rank in((31,1,1),(11,1,11),(1,1,10),(2,1,10),(20,0,2),(22,0,3),(81,0,8),(99,0,11)):
   cells[square]=16*owner|32|rank
  lost=COUNTS[:]
  for rank in(2,3,8,11):lost[rank]-=1
  state={0:(None,None,0),1:(None,None,0)}
  proof=_fork_certificate(cells,1,lost,[0]*12,state,(31,21),[0,20000],[20,22])
  self.assertFalse(proof['certified']);self.assertTrue(any(r['terminal_refutation']for r in proof.get('responses',[])))
 def test_capture_preservation_and_global_cap_fallback(self):
  cells,lost,remaining,state=fixture();cells[30]=16|32|8;lost[8]-=1
  scores=dict.fromkeys(_fork_own_moves(cells,0,state),0)
  self.assertEqual(fork_selection(cells,0,lost,remaining,scores,(31,30),state)[0],(31,30))
  cells,lost,remaining,state=fixture();scores=dict.fromkeys(_fork_own_moves(cells,0,state),0)
  with patch('campaign_mobile_capture._fork_certificate',return_value=dict(certified=False,inconclusive=True,enemy_nodes=20001)):
   selected,report=fork_selection(cells,0,lost,remaining,scores,(31,30),state)
  self.assertEqual(selected,(31,30));self.assertEqual(report['reason'],'global-node-cap')
 def test_global_budget_is_shared_and_score_only_breaks_bound_ties(self):
  cells,lost,remaining,state=fixture();scores=dict.fromkeys(_fork_own_moves(cells,0,state),0);parent=(31,30);seen=[]
  def capped(*args):
   budget=args[6];seen.append(id(budget));budget[0]+=19000 if len(seen)==1 else 1001
   return dict(certified=False,enemy_nodes=19000 if len(seen)==1 else 1001,**({'inconclusive':True}if len(seen)>1 else{}))
  with patch('campaign_mobile_capture._fork_certificate',side_effect=capped):
   selected,report=fork_selection(cells,0,lost,remaining,scores,parent,state)
  self.assertEqual(selected,parent);self.assertEqual(report['reason'],'global-node-cap');self.assertEqual(len(set(seen)),1)
  cells[20]=16|32|3;cells[22]=16|32|6;cells[11]=2;lost=COUNTS[:]
  for rank in(11,3,6,8):lost[rank]-=1
  scores=dict.fromkeys(_fork_own_moves(cells,0,state),0)
  scores[11,21]=1;scores[31,21]=7
  def tied(*args):return dict(certified=args[5]!=parent,minimum_net_material=15,enemy_nodes=0,responses=[])
  with patch('campaign_mobile_capture._fork_certificate',side_effect=tied):
   selected,report=fork_selection(cells,0,lost,remaining,scores,parent,state)
  self.assertEqual(selected,(31,21))
 def test_full_key_masks_nibbles_and_tracks_enemy_lost(self):
  cells=[254 if sq in LAKES else 255 for sq in range(100)];cells[50]=1;cells[80]=16|64|12;cells[0]=16|32|11;cells[99]=11
  remaining=[0]*12;remaining[8]=1;state={0:(None,None,0),1:(None,None,0)}
  lost=_fork_enemy_lost(cells,0,remaining);reference=None
  for nibble in range(12):
   cells[80]=(cells[80]&240)|nibble
   outputs=list(_fork_successors(cells,0,remaining,state,worths(lost),[0,20000]))
   short=next(o for o in outputs if o['observation']['move']==[80,70])
   self.assertIsNone(short['observation']['rank']);self.assertFalse(short['cells'][70]&32)
   key=_fork_public_key(short['cells'],0,_fork_enemy_lost(short['cells'],0,short['remaining']),short['remaining'],short['shuttle'])
   if reference is None:reference=key
   self.assertEqual(key,reference)
   attack=next(o for o in outputs if o['observation']['move']==[80,50])
   fallen=_fork_enemy_lost(attack['cells'],0,attack['remaining'])
   self.assertEqual(fallen[8],lost[8]+1);self.assertFalse(attack['cells'][50]&64);self.assertTrue(attack['cells'][50]&32)
 def test_unknown_one_step_quiet_observation_groups_multiple_rank_hypotheses(self):
  cells=[254 if sq in LAKES else 255 for sq in range(100)];cells[50]=1;cells[80]=16|12;cells[82]=16|12;cells[0]=16|32|11;cells[99]=11
  remaining=[0]*12;remaining[0]=remaining[8]=1;state={0:(None,None,0),1:(None,None,0)}
  lost=_fork_enemy_lost(cells,0,remaining)
  outcomes=list(_fork_successors(cells,0,remaining,state,worths(lost),[0,20000]))
  short=[o for o in outcomes if o['observation']['move']==[80,70]]
  self.assertEqual(len(short),1);self.assertIsNone(short[0]['observation']['rank'])
  self.assertEqual(short[0]['remaining'],remaining);self.assertFalse(short[0]['cells'][70]&32)
 def test_public_event_lifecycle_and_one_use_followup(self):
  cells,lost,remaining,state=fixture();scores=dict.fromkeys(_fork_own_moves(cells,0,state),0)
  _,report=fork_selection(cells,0,lost,remaining,scores,(31,30),state)
  entry=next((key,move)for key,move in report['witness_plan'].items()if json.loads(key)[1][78]<254 and json.loads(key)[1][88]==255)
  key,witness=entry;army,board,fallen,hidden,red,blue=json.loads(key);future_state={0:tuple(red),1:tuple(blue)}
  bot=barebot();bot._fork_plan=dict(stage='own-move',first_move=(31,21),states={key:witness},bound=75)
  bot._fork_event(['moved',square_name(31),square_name(21)]);self.assertEqual(bot._fork_plan['stage'],'enemy-move')
  bot.model.plies=1;bot._fork_event(['moved',square_name(88),square_name(78)]);self.assertEqual(bot._fork_plan['stage'],'ready')
  other=(21,22)if witness==(21,20)else(21,20)
  self.assertIn(other,_fork_own_moves(board,army,future_state))
  selected,report=bot._select_fork(board,army,fallen,hidden,{witness:-100,other:100},other,future_state)
  self.assertEqual(selected,witness);self.assertEqual(report['phase'],'followup');self.assertIsNone(bot._fork_plan)
 def test_mismatch_correction_resets_and_immediate_win_priority(self):
  cells,lost,remaining,state=fixture();key=_fork_public_key(cells,0,lost,remaining,state)
  for command in('new','rules','custom','position','setup','seed','played'):
   bot=barebot();bot._fork_plan=dict(stage='ready',first_move=(31,21),states={key:(31,21)},bound=75)
   bot._fork_event([command]);self.assertIsNone(bot._fork_plan)
  bot=barebot();bot._fork_plan=dict(stage='ready',first_move=(31,21),states={'wrong-key':(31,21)},bound=75)
  self.assertEqual(bot._select_fork(cells,0,lost,remaining,{(31,30):0},(31,30),state)[0],(31,30));self.assertIsNone(bot._fork_plan)
  bot._fork_plan=dict(stage='ready',first_move=(31,21),states={key:(31,21)},bound=75)
  self.assertEqual(bot._select_fork(cells,0,lost,remaining,{(31,21):0,(31,30):30000},(31,30),state)[0],(31,30));self.assertIsNone(bot._fork_plan)
  bot._fork_plan=dict(stage='own-move',first_move=(31,21),states={},bound=75)
  bot._fork_event(['moved',square_name(31),square_name(30)]);self.assertIsNone(bot._fork_plan);self.assertEqual(bot._fork_discard_reason,'unexpected-public-history')
 def test_factored_support_matches_exhaustive_small_count_assignments(self):
  import itertools
  for ranks in itertools.product((0,8,10,11),repeat=3):
   remaining=[ranks.count(rank)for rank in range(12)]
   for mask in range(8):
    if any(mask>>i&1 and rank>=10 for i,rank in enumerate(ranks)):continue
    cells=[255]*100
    for i in range(3):cells[i]=16|12|(64 if mask>>i&1 else 0)
    valid=[assignment for assignment in set(itertools.permutations(ranks))if all(not(mask>>i&1)or rank<10 for i,rank in enumerate(assignment))]
    for i in range(3):
     expected=sorted({assignment[i]for assignment in valid if assignment[i]<10})
     self.assertEqual(_fork_support(cells,1,remaining,i),expected)
 def test_invalid_public_inventory_cannot_prove_vacuous_terminal_win(self):
  cells,lost,remaining,state=fixture();scores=dict.fromkeys(_fork_own_moves(cells,0,state),0)
  for broken_lost,broken_remaining in((lost,remaining[:11]+[1]),([0]*12,remaining),(lost,[-1]+remaining[1:])):
   proof=_fork_certificate(cells,0,broken_lost,broken_remaining,state,(31,21),[0,20000],[20,22])
   self.assertFalse(proof['certified']);self.assertEqual(proof['reason'],'inconsistent-public-inventory');self.assertEqual(proof['enemy_nodes'],0)
   selected,report=fork_selection(cells,0,broken_lost,broken_remaining,scores,(31,30),state)
   self.assertEqual(selected,(31,30));self.assertEqual(report['reason'],'inconsistent-public-inventory')
 def test_ambiguous_public_witness_is_inconclusive(self):
  cells,lost,remaining,state=fixture()
  with patch('campaign_mobile_capture._fork_public_key',return_value='collision'):
   proof=_fork_certificate(cells,0,lost,remaining,state,(31,21),[0,20000],[20,22])
  self.assertFalse(proof['certified']);self.assertTrue(proof['inconclusive']);self.assertEqual(proof['reason'],'ambiguous-public-witness')
 def test_shuttle_packet_matches_public_array_layout(self):
  self.assertEqual(_fork_shuttle('0a14151e0502'),{0:(10,21,5),1:(20,30,2)})
  self.assertEqual(_fork_shuttle('ffffffff0000'),{0:(None,None,0),1:(None,None,0)})

if __name__=='__main__':unittest.main()
