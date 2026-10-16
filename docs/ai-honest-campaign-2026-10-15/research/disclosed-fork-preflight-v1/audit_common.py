"""Same first20 public fixtures, common capture response control; no games."""
import json,sys,time
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from certificate_common import certify_common
from certificate import own_moves,successors
from campaign_belief_values import worths
from audit import HERE,sha

def run():
 previous=json.loads((HERE/'certificate-result.json').read_text());rows=[];counts=Counter()
 for row in previous['results']:
  fixture=row['public_fixture'];shuttle={int(k):tuple(v)for k,v in fixture['shuttle'].items()};army=row['army'];cells=fixture['cells']
  args=(cells,army,fixture['lost'],fixture['remaining'],shuttle)
  root_flagwin=any(cells[t]<254 and cells[t]&32 and cells[t]&15==11 for s,t in own_moves(cells,army,shuttle))
  root_flagthreat=any(o['flag_loss']for o in successors(cells,army,fixture['remaining'],shuttle,worths(fixture['lost']),[0,20000]))
  reports={};timing={}
  for name,move in(('fork',row['move']),('native',row['saved_selected'])):
   start=time.perf_counter()
   reports[name]=certify_common(*args,tuple(move))if cells[move[1]]==255 else dict(certified=False,preserve_native_capture=True,enemy_nodes=0)
   timing[name]=1000*(time.perf_counter()-start)
  opportunity=(not root_flagwin and not root_flagthreat and not reports['native'].get('preserve_native_capture')and
               not reports['native']['certified']and reports['fork']['certified']and not reports['native'].get('inconclusive'))
  counts['candidates']+=1;counts['fork_certified']+=reports['fork']['certified'];counts['native_certified']+=reports['native']['certified'];counts['new_certified_opportunities']+=opportunity
  counts['inconclusive_evaluations']+=sum(p.get('inconclusive',False)for p in reports.values())
  rows.append(dict(game=row['game'],army=army,ply=row['ply'],fork=row['move'],native=row['saved_selected'],root_flag_win=root_flagwin,root_flag_threat=root_flagthreat,new_opportunity=opportunity,reports=reports,timing_ms=timing))
 return dict(kind='fixed20-common-public-response-control',strength_evidence=False,counts=dict(counts),new_opportunity_games=len({r['game']for r in rows if r['new_opportunity']}),sources={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),HERE/'certificate_common.py',HERE/'certificate.py',HERE/'CONTROL-PROTOCOL.json',HERE/'certificate-result.json')},results=rows)
if __name__=='__main__':
 result=run();(HERE/'common-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts'],indent=2));print('games',result['new_opportunity_games'])
