"""Full current/HEAD/default/opt-in target links in private copied source trees."""
from pathlib import Path
import subprocess,tempfile,shutil,json,re,zipfile,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
BASE=['BANKED_AI','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2','AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD']
existing=['core/ai.c','core/ai_memory.c','core/ai_memory.h','feldmarschall.cfg','ui/sound.c','scenes/play.c']
new=['core/ai_template.c','core/ai_template.h','ui/ai_template_bank.s']
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source={str(p.relative_to(R/'src')):sha(p) for p in (R/'src').rglob('*') if p.is_file()}
records={};artifacts=[]
with tempfile.TemporaryDirectory(prefix='template-actual-link-') as temp:
 for mode in ('head-default','current-default','current-template'):
  t=Path(temp)/mode;shutil.copytree(R/'src',t,ignore=shutil.ignore_patterns('*.o','*.PRG','*.BIN','*.map','*.sym'))
  if mode=='head-default':
   for n in existing:(t/n).write_bytes(subprocess.check_output(['git','show',head+':src/'+n],cwd=R))
   for n in new:(t/n).unlink()
  inputs=sorted(p.relative_to(t).as_posix() for p in t.glob('*.c'))
  for folder in ('core','ui','scenes'):inputs+=sorted(p.relative_to(t).as_posix() for p in (t/folder).glob('*.c'))
  assembly=[]
  for folder in ('ui','scenes'):assembly+=sorted(p.relative_to(t).as_posix() for p in (t/folder).glob('*.s'))
  flags=BASE+(['AI_TEMPLATE_PRIOR_Q24'] if mode=='current-template' else [])
  cmd=['cl65','-O','-t','cx16','-I','.','-I','core','-I','ui','-I','scenes']+['-D'+f for f in flags]+['--asm-define','AI_MEMORY']
  if mode=='current-template':cmd+=['--asm-define','AI_TEMPLATE_PRIOR_Q24']
  cmd+=['-Wl','-D,__STACKSIZE__=0x0400','-C','feldmarschall.cfg','-o','FELDMARS.PRG','-m','FELDMARS.map','-Ln','FELDMARS.sym']+inputs+assembly+['vendor/zsmkit.lib']
  p=subprocess.run(cmd,cwd=t,text=True,capture_output=True)
  out=dict(returncode=p.returncode,command=cmd,stdout=p.stdout,stderr=p.stderr,flags=flags)
  if (t/'FELDMARS.map').exists():
   text=(t/'FELDMARS.map').read_text().split('Segment list:',1)[1].split('Exports list',1)[0]
   seg={n:dict(start=int(a,16),end=int(b,16),size=int(s,16)) for n,a,b,s in re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})',text,re.M)}
   out['segments']=seg;out['free_bytes']={bank:8192-sum(seg.get(n,{}).get('size',0) for n in names) for bank,names in {'AI':('AICODE','AIRODATA','AIBSS'),'MISSION':('MISSIONCODE','MISSIONRODATA','MISSIONBSS'),'PLAY':('PLAYCODE','PLAYRODATA'),'BELIEF':('BELIEFCODE','BELIEFRODATA','BELIEFBSS')}.items()};out['free_bytes']['MAIN']=0x9b00-1-seg['BSS']['end']
  out['binaries_sha256']={n:sha(t/n) for n in ('FELDMARS.PRG','AI.BIN','MISSION.BIN','PLAY.BIN','BELIEF.BIN') if (t/n).exists()}
  for n in ('FELDMARS.map','FELDMARS.sym','FELDMARS.PRG','AI.BIN','MISSION.BIN','PLAY.BIN','BELIEF.BIN'):
   if (t/n).exists():artifacts.append((mode+'/'+n,(t/n).read_bytes()))
  records[mode]=out
for n in ('FELDMARS.PRG','AI.BIN','MISSION.BIN','PLAY.BIN'):
 assert records['head-default']['binaries_sha256'][n]==records['current-default']['binaries_sha256'][n],n
assert source=={str(p.relative_to(R/'src')):sha(p) for p in (R/'src').rglob('*') if p.is_file()}
report=dict(head=head,source_sha256=source,workspace_src_unchanged=True,default_original_binaries_identical=True,builds=records)
with zipfile.ZipFile(H/'target-link-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n,data in artifacts:z.writestr(n,data)
(H/'target-link.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({n:{k:v for k,v in d.items() if k in ('returncode','stderr','free_bytes')} for n,d in records.items()},indent=2))
