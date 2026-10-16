"""Explicit correction artifact; no released research file is modified."""
import hashlib,json,shlex,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
HERE=Path(__file__).resolve().parent;RESEARCH=HERE.parent/'disclosed-fork-preflight-v1'
sys.path.insert(0,str(RESEARCH))
from certificate import certify
from certificate_common import certify_common
from campaign_mobile_capture import _fork_shuttle
from feldmarschall import Position,COUNTS,GLYPHS,LAKES,Engine,square_name
from tournament_store import Tournament
COHORT=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
POLICY='student-template-flag-bomb-v1-normal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 original=json.loads((RESEARCH/'certificate-result.json').read_text());common=json.loads((RESEARCH/'common-result.json').read_text())
 controls={(r['game'],r['ply'],tuple(r['fork'])):r for r in common['results']};requests={}
 for row in original['results']:requests.setdefault(row['game'],{}).setdefault(row['ply'],[]).append(row)
 directory=ROOT/'build/ai-catalog'/POLICY;receipt=json.loads((directory/'build.json').read_text());observer=directory/'observer'
 assert sha(observer)==receipt['runtime_sha256']['observer']
 rows=[];equal=0;changed=Counter()
 with Tournament(COHORT)as saved:
  for identity,positions in requests.items():
   game=saved.game(identity);army=int(game['blue']==POLICY);p=Position();lost=[[0]*12 for _ in(0,1)]
   for owner in(0,1):p.place(owner,game[('red_setup','blue_setup')[owner]])
   native=Engine(shlex.quote(str(observer)))
   try:
    for line in('new '+('red','blue')[army],'rules 0','setup '+game[('red_setup','blue_setup')[army]]):native.send(line)
    for ply,(source,target)in enumerate(game['moves']):
     if ply in positions:
      cells=[254 if sq in LAKES else 255 if cell is None else(cell[1]if cell[0]==army or cell[3]else 12)|16*cell[0]|32*cell[3]|64*cell[2]for sq,cell in enumerate(p.cells)]
      seen=Counter(c&15 for c in cells if c<254 and bool(c&16)!=bool(army)and c&32)
      remaining=[n-lost[1-army][r]-seen[r]for r,n in enumerate(COUNTS)]
      side,board,fallen,history=native.ask('public','public').split();actual=list(bytes.fromhex(board));actual=[(c&240)|12 if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in actual]
      assert int(side)==army and actual==cells and list(bytes.fromhex(fallen))==lost[1-army]
      assert _fork_shuttle(history)==p.shuttle,(identity,ply,_fork_shuttle(history),p.shuttle)
      for old in positions[ply]:
       fixture=dict(cells=cells[:],lost=lost[1-army][:],remaining=remaining[:],shuttle=dict(p.shuttle))
       args=(cells,army,lost[1-army],remaining,p.shuttle)
       actor=certify(*args,tuple(old['move']),[v['square']for v in old['victims']]);assert actor==old['proof'],(identity,ply,'actor')
       control=controls[identity,ply,tuple(old['move'])]
       fork=certify_common(*args,tuple(old['move']));assert fork==control['reports']['fork'],(identity,ply,'common-fork')
       baseline=certify_common(*args,tuple(old['saved_selected']));assert baseline==control['reports']['native'],(identity,ply,'common-native')
       equal+=3;legacy=old['public_fixture'];fields=[]
       for name in('lost','shuttle','remaining'):
        before=legacy[name];after=json.loads(json.dumps(fixture[name]))
        if before!=after:fields.append(name);changed[name]+=1
       flags=[sq for sq,(before,after)in enumerate(zip(legacy['cells'],cells))if before!=after]
       assert all((a&~64)==(b&~64)for a,b in zip(legacy['cells'],cells))
       if flags:changed['production_MOVED_flags']+=1
       assert legacy['remaining']==remaining
       rows.append(dict(game=identity,army=army,ply=ply,move=old['move'],saved_selected=old['saved_selected'],victims=old['victims'],public_fixture=fixture,proof=actor,common_proofs=dict(fork=fork,native=baseline),native_public_verified=True,metadata_changed_fields=fields,metadata_before={name:legacy[name]for name in fields},metadata_corrected={name:fixture[name]for name in fields},production_MOVED_changed_squares=flags))
     if ply>=max(positions):break
     attacker,defender=p.cells[source],p.cells[target]
     event='moved '+square_name(source)+' '+square_name(target)if defender is None else'battle '+square_name(source)+' '+square_name(target)+' '+GLYPHS[attacker[1]]+' '+GLYPHS[defender[1]]
     native.send(event)
     if defender is None:p.move(source,target)
     else:
      defender_moved=defender[2];outcome,fallen=p.fight(source,target,attacker[1],defender[1])
      if outcome=='defender':p.cells[target][2]=defender_moved
      for owner,rank,*_ in fallen:lost[owner][rank]+=1
   finally:native.close()
 return dict(kind='explicit-public-fixture-metadata-correction',originals_unchanged=True,corrected_fixtures=len(rows),old_proofs_exactly_equal=equal,changed_fields=dict(changed),native_public_board_lost_and_shuttle_verified=True,observer_sha256=sha(observer),cohort_sha256=sha(COHORT),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),RESEARCH/'certificate-result.json',RESEARCH/'common-result.json',RESEARCH/'all-result.json',RESEARCH/'certificate.py',RESEARCH/'certificate_common.py')},results=rows)
if __name__=='__main__':
 result=run();(HERE/'corrected-first20-fixtures.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('results','sources')},indent=2))
