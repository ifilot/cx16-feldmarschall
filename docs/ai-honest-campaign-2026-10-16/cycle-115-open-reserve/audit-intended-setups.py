"""Verify the frozen open-reserve treatment in every actual saved own army."""
import hashlib,json,re,sqlite3,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
DIRECTORY=Path(__file__).resolve().parent
plan=json.loads((DIRECTORY/'plan.json').read_text())
frozen=json.loads((DIRECTORY/'frozen-policies.json').read_text())
baseline=plan['baseline'];candidate=next(p for p in plan['policies'] if p!=baseline)
with zipfile.ZipFile(ROOT/frozen[baseline]['archive']) as archive:
 text=archive.read('src/core/ai_deploy.c').decode()
row=next(row for row in re.findall(r'\{([\d,]+)\}',text) if len(row.split(','))==40)
base=''.join('123456789SBF'[int(n)] for n in row.split(','))
changed=list(base);changed[28],changed[38]=changed[38],changed[28];changed=''.join(changed)
assert {i for i in range(40) if base[i]!=changed[i]}=={28,38}
mirror=lambda s:''.join(s[r:r+10][::-1] for r in range(0,40,10))
rows={};hashes={}
for policy,expected in ((baseline,base),(candidate,changed)):
 path=DIRECTORY/(policy+'.fmtour');db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 metadata={r['key']:json.loads(r['value']) for r in db.execute('select * from metadata')}
 assert metadata['status']=='complete' and metadata['setup_mode']=='policy-owned-rotated-v1'
 games=[dict(r) for r in db.execute('select id,pair_id,family,red,blue,seed,red_setup,blue_setup from games order by id')];db.close()
 assert len(games)==2*plan['rounds']*len(plan['families'])
 for game in games:
  side='red' if game['red']==policy else 'blue';own=game[side+'_setup']
  assert own==(expected if side=='red' else mirror(expected)),(policy,game['id'])
 rows[policy]=games;hashes[policy]=hashlib.sha256(path.read_bytes()).hexdigest()
for a,b in zip(rows[baseline],rows[candidate]):
 for key in ('id','pair_id','family','seed'):assert a[key]==b[key]
 side='red' if a['red']==baseline else 'blue';other='blue' if side=='red' else 'red'
 assert b[side]==candidate and a[other]==b[other]==plan['opponent']
 assert a[other+'_setup']==b[other+'_setup']
 norm=lambda s:mirror(s) if side=='blue' else s
 assert {i for i,(x,y) in enumerate(zip(norm(a[side+'_setup']),norm(b[side+'_setup']))) if x!=y}=={28,38}
doc=dict(passed=True,attempts=sum(map(len,rows.values())),games_per_arm=len(rows[baseline]),
 treatment='Only own origins28/38 swap; normalize rotated Blue armies before comparison',
 expected_baseline=base,expected_candidate=changed,opponent_armies_seeds_sides_all_matched=True,
 every_actual_own_setup_matches_frozen_treatment=True,tournament_sha256=hashes,
 audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(DIRECTORY/'intended-setups-audit.json').write_text(json.dumps(doc,indent=2)+'\n');print(json.dumps(doc))
