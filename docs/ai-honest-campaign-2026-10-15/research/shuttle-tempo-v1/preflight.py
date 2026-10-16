"""Public two-square tempo incidence in completed screening only."""
from collections import Counter
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_flag_guard import public_position
from campaign_home_reserve import neighbors
from feldmarschall import Position,battle,LAKES
from tournament_store import Tournament
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-21-template-opening-prior/student-template-flag-bomb-v1-normal.fmtour'
POLICY='student-template-flag-bomb-v1-normal'


def inspect(position,army):
 p=public_position(position,army);previous,last,count=p.shuttle[1-army]
 if count<5 or last is None:return None
 defender=p.cells[last]
 if not defender or defender[0]==army or not defender[3]or defender[1]>6:return None
 if p.cells[previous]is not None:return None
 entries=[]
 for source,target in p.moves(army):
  if target!=previous or battle(defender[1],p.cells[source][1])!='attacker':continue
  row=dict(move=[source,target],actor_rank=p.cells[source][1],strict_aligned_breach=False)
  bomb=previous+(previous-last);flag=bomb+(previous-last)
  if p.cells[source][1]==7 and bomb in neighbors(previous)and flag in neighbors(bomb):
   b,f=p.cells[bomb],p.cells[flag]
   if b and b[0]!=army and b[3]and b[1]==10 and f and f[0]!=army and(f[3]and f[1]==11 or not f[3]and not f[2]):
    row.update(strict_aligned_breach=True,bomb=bomb,possible_Flag=flag)
  entries.append(row)
 return dict(enemy_shuttle=[previous,last,count],disclosed_defender_rank=defender[1],entries=entries)


def main():
 counts=Counter();rows=[];own_diagnostics=[]
 with Tournament(SOURCE)as saved:
  for meta in saved.games():
   game=saved.game(meta['id']);army=int(game['blue']==POLICY);p=Position()
   for side in(0,1):p.place(side,game[('red_setup','blue_setup')[side]])
   for ply,move in enumerate(game['moves']):
    if ply%2==army:
     counts['own_roots']+=1
     if p.shuttle[1-army][2]>=5:counts['enemy_active_shuttle_roots']+=1
     if p.shuttle[army][2]>=5:counts['own_active_shuttle_roots']+=1
     a,b,n=p.shuttle[army]
     if n>=4 and tuple(move)==(b,a):counts['actual_selected_reversal_reaches5_roots']+=1
     if n>=5 or n>=4 and tuple(move)==(b,a):
      public=public_position(p,army)
      own_diagnostics.append(dict(game=game['id'],ply=ply,army=army,own_shuttle=[a,b,n],selected=list(move),
       shuttle_actor=public.cells[b] if b is not None else None,
       legal_actor_moves=[m for m in public.moves(army)if m[0]==b],
       next_actual_moves=game['moves'][ply:ply+3],
       public_board_hex=bytes(254 if s in LAKES else 255 if c is None else c[0]*16|c[1]|(64 if c[2]else 0)|(32 if c[3]else 0)for s,c in enumerate(public.cells)).hex()))
     row=inspect(p,army)
     if row:
      counts['disclosed_strong_defender_active_ban_roots']+=1
      if row['entries']:counts['otherwise_lethal_quiet_entry_roots']+=1
      if any(r['strict_aligned_breach']for r in row['entries']):counts['strict_aligned_Miner_breach_roots']+=1
      row.update(game=game['id'],ply=ply,army=army,selected=list(move));rows.append(row)
    source,target=move;actor,defender=p.cells[source],p.cells[target]
    if defender:p.fight(source,target,actor[1],defender[1])
    else:p.move(source,target)
 result=dict(kind='public-shuttle-tempo-screening-preflight',games=400,counters=counts,rows=rows,own_diagnostics=own_diagnostics,
  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  limits='Public banned-square geometry only, not global safety or strength. Other enemy moves reset the ban; actor/Flag races and hidden defenders require further proof. Truth is used only for referee replay, immediately masked before predicate.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='rows'},indent=2))


if __name__=='__main__':main()
