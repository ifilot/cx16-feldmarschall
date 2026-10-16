"""Structural last-mobile shuttle losses, public proof and screening only."""
from collections import Counter
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_flag_guard import clone,public_position,confirmed_danger
from preflight import inspect as tempo_inspect
from feldmarschall import Position,battle,LAKES
from tournament_store import Tournament
OUT=Path(__file__).resolve().parent
FILES=[]
for prefix in('cycle-19-','cycle-21-','cycle-22-','cycle-23-'):
 dirs=[p for p in(OUT.parents[1]).iterdir()if p.is_dir()and p.name.startswith(prefix)]
 assert len(dirs)==1,(prefix,dirs)
 FILES.extend(sorted(dirs[0].glob('student-*.fmtour')))
assert len(FILES)==11,FILES


def play(p,move):
 a,b=move
 if p.cells[b]:p.fight(a,b,p.cells[a][1],p.cells[b][1])
 else:p.move(a,b)


def certain_quiet(p,side):
 return [m for m in p.moves(side)if p.cells[m[1]]is None and(p.cells[m[0]][3]and p.cells[m[0]][1]<10 or p.cells[m[0]][2])]


def certain_has_move(p,side):
 return bool(certain_quiet(p,side)or any(p.cells[a][3]and p.cells[a][1]<10 for a,b in p.moves(side)))


def terminal_losing_capture(p,army,move):
 a,b=move;target=p.cells[b]
 if not target or not target[3]or battle(p.cells[a][1],target[1])=='attacker':return False
 q=clone(p);play(q,move)
 return not q.moves(army)and certain_has_move(q,1-army)


def wait_certificate(p,army):
 for waiting in certain_quiet(p,1-army):
  q=clone(p);play(q,waiting);responses=q.moves(army)
  if certain_has_move(q,1-army)and all(terminal_losing_capture(q,army,m)for m in responses):
   return dict(enemy_wait=waiting,all_friendly_terminal_losing_replies=responses)
 return None


def refutation(p,army,move):
 a,b=move;target=p.cells[b]
 if target:
  if not target[3]:return None
  if terminal_losing_capture(p,army,move):return dict(reason='own-terminal-losing-capture')
  if target[1]==11:return None
 q=clone(p);play(q,move)
 flag=next((s for s,c in enumerate(q.cells)if c and c[:2]==[army,11]),None)
 if flag is not None:
  attacks=confirmed_danger(q,army,flag)
  if attacks:return dict(reason='enemy-terminal-Flag-capture',reply=[attacks[0],flag])
 for reply in q.moves(1-army):
  a,b=reply;victim=q.cells[b];attacker=q.cells[a]
  if not victim or victim[0]!=army or victim[1]>=10 or not attacker[3]or attacker[1]>=10:continue
  if battle(attacker[1],victim[1])=='defender':continue
  r=clone(q);play(r,reply)
  if not r.moves(army)and certain_has_move(r,1-army):return dict(reason='enemy-terminal-capture',reply=reply)
 proof=wait_certificate(q,army)
 return dict(reason='enemy-waiting-shuttle-trap',**proof)if proof else None


def main():
 counts=Counter();records=[];sources={};tempo_rows=[]
 for path in FILES:
  policy=path.stem;counts['cohort_files']+=1;sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
  with Tournament(path)as saved:
   for meta in saved.games():
    game=saved.game(meta['id']);army=int(game['blue']==policy);assert game[('red','blue')[army]]==policy
    p=Position()
    for side in(0,1):p.place(side,game[('red_setup','blue_setup')[side]])
    counts['games']+=1
    for ply,move in enumerate(game['moves']):
     if ply%2==army:
      counts['own_roots']+=1;a,b,n=p.shuttle[army]
      if p.shuttle[1-army][2]>=5:counts['enemy_active_shuttle_roots']+=1
      if p.shuttle[1-army][2]>=5:
       tempo=tempo_inspect(p,army)
       if tempo:
        counts['enemy_disclosed_strong_ban_roots']+=1
        if tempo['entries']:counts['enemy_otherwise_lethal_quiet_entry_roots']+=1
        if any(r['strict_aligned_breach']for r in tempo['entries']):counts['enemy_strict_aligned_Miner_breach_roots']+=1
        tempo.update(cohort=str(path.relative_to(ROOT)),game=game['id'],ply=ply,army=army);tempo_rows.append(tempo)
      if n==4 and tuple(move)==(b,a)and p.cells[a]is None:
       counts['selected_quiet_reversal_reaches5']+=1
       mobile=[s for s,c in enumerate(p.cells)if c and c[0]==army and c[1]<10]
       if len(mobile)==1:
        counts['last_mobile_reversals']+=1;public=public_position(p,army);q=clone(public);q.move(*move);proof=wait_certificate(q,army)
        if proof:
         counts['certified_last_mobile_wait_traps']+=1
         alternatives={f'{s}:{t}':refutation(public,army,(s,t))for s,t in public.moves(army)}
         quiet_nonrefuted=[list(m)for m in public.moves(army)if public.cells[m[1]]is None and alternatives[f'{m[0]}:{m[1]}']is None]
         if all(alternatives.values()):counts['all_root_choices_publicly_refuted']+=1
         if quiet_nonrefuted:counts['has_nonrefuted_quiet_alternative']+=1
         records.append(dict(cohort=str(path.relative_to(ROOT)),game=game['id'],ply=ply,army=army,selected=move,own_shuttle=[a,b,n],proof=proof,
          root_refutations=alternatives,nonrefuted_quiet_alternatives=quiet_nonrefuted,
          public_board_hex=bytes(254 if s in LAKES else 255 if c is None else c[0]*16|c[1]|(64 if c[2]else 0)|(32 if c[3]else 0)for s,c in enumerate(public.cells)).hex(),
          public_shuttle=public.shuttle,result=game['result'],reason=game['reason']))
     s,t=move;actor,target=p.cells[s],p.cells[t]
     if target:p.fight(s,t,actor[1],target[1])
     else:p.move(s,t)
  print('cohort',path.parent.name,path.stem,flush=True)
 result=dict(kind='completed-screening-public-last-mobile-shuttle-terminal-audit',counters=counts,records=records,enemy_tempo_rows=tempo_rows,sources=sources,
  source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  limits='Existential known/legal quiet enemy wait plus universal friendly terminal-loss certificate. Nonrefuted alternative is not a global safety proof. No validation files, native scores, fitting, games or runtime.')
 (OUT/'expanded-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(counters=counts),indent=2))


if __name__=='__main__':main()
