"""Public-state deduplication of expanded opportunities, without new proofs."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from audit import HERE,COHORT,POLICY,sha
from certificate import record
from feldmarschall import Position,COUNTS,LAKES
from tournament_store import Tournament

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def run():
 data=json.loads((HERE/'all-result.json').read_text());requests={}
 for row in data['results']:
  if row['new_opportunity']:requests.setdefault(row['game'],{})[row['ply']]=row
 rows=[];gamecounts=Counter();kernelcounts=Counter()
 with Tournament(COHORT)as saved:
  for identity,positions in requests.items():
   game=saved.game(identity);army=int(game['blue']==POLICY);p=Position();lost=[[0]*12 for _ in(0,1)]
   for owner in(0,1):p.place(owner,game[('red_setup','blue_setup')[owner]])
   for ply,(source,target)in enumerate(game['moves']):
    if ply in positions:
     row=positions[ply]
     cells=[254 if sq in LAKES else 255 if cell is None else(cell[1]if cell[0]==army or cell[3]else 12)|16*cell[0]|32*cell[3]|64*cell[2]for sq,cell in enumerate(p.cells)]
     seen=Counter(c&15 for c in cells if c<254 and bool(c&16)!=bool(army)and c&32)
     remaining=[n-lost[1-army][r]-seen[r]for r,n in enumerate(COUNTS)]
     def postkey(move):
      s,t=move;after=cells[:];after[t]=after[s]|64;after[s]=255
      return digest([army,after,lost[1-army],remaining,record(p.shuttle,army,s,t)])
     nativekey=postkey(row['native']);gamecounts[identity]+=1
     for fork in row['forks']:
      if not fork['new_opportunity']:continue
      forkkey=postkey(fork['move']);key=digest([forkkey,nativekey]);kernelcounts[key]+=1
      rows.append(dict(game=identity,ply=ply,move=fork['move'],native=row['native'],fork_public_kernel_sha256=forkkey,native_public_kernel_sha256=nativekey,comparison_sha256=key,within_proposed_global_budget=row['within_proposed_global_budget']))
    if ply>=max(positions):break
    attacker,defender=p.cells[source],p.cells[target]
    if defender is None:p.move(source,target)
    else:
     _,fallen=p.fight(source,target,attacker[1],defender[1])
     for owner,rank,*_ in fallen:lost[owner][rank]+=1
 return dict(kind='public-kernel-deduplication-only',new_proof_queries=0,opportunity_roots=sum(gamecounts.values()),opportunity_candidates=len(rows),games=dict(gamecounts),distinct_fork_public_kernels=len({r['fork_public_kernel_sha256']for r in rows}),distinct_fork_vs_native_public_comparisons=len(kernelcounts),largest_repeated_comparison=max(kernelcounts.values(),default=0),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'all-result.json',HERE/'certificate.py')},records=rows)
if __name__=='__main__':
 data=run();(HERE/'unique-result.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items()if k not in('records','sources')},indent=2))
