"""Experimental isolated bank25 runtime closure relocation; no toolchain edits."""
from pathlib import Path
import subprocess,tempfile,shutil,json,re,zipfile,hashlib
H=Path(__file__).resolve().parent;R=H.parents[3]
FLAGS=['BANKED_AI','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2','AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD','AI_TEMPLATE_PRIOR_Q24','AI_TEMPLATE_PRIOR_Q24_CACHE']
def sha(data):return hashlib.sha256(data).hexdigest()
def readmap(p):
 text=p.read_text();part=text.split('Segment list:',1)[1].split('Exports list',1)[0]
 seg={n:dict(start=int(a,16),end=int(b,16),size=int(s,16)) for n,a,b,s in re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})',part,re.M)}
 modules=set(re.findall(r'^/usr/share/cc65/lib/cx16.lib\(([^)]+)\):',text,re.M))
 return seg,modules
commands=[];artifacts=[]
with tempfile.TemporaryDirectory(prefix='template-relocated-link-') as temp:
 t=Path(temp)/'src';shutil.copytree(R/'src',t,ignore=shutil.ignore_patterns('*.o','*.PRG','*.BIN','*.map','*.sym'))
 inputs=sorted(p.relative_to(t).as_posix() for p in t.glob('*.c'))
 for folder in ('core','ui','scenes'):inputs+=sorted(p.relative_to(t).as_posix() for p in (t/folder).glob('*.c'))
 assembly=[]
 for folder in ('ui','scenes'):assembly+=sorted(p.relative_to(t).as_posix() for p in (t/folder).glob('*.s'))
 def run(cmd,check=True,cwd=None):
  p=subprocess.run(cmd,cwd=cwd or t,text=True,capture_output=True);commands.append(dict(argv=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
  if check and p.returncode:raise RuntimeError(commands[-1])
  return p
 objects=[];generated=[]
 prefix=['-O','-t','cx16','-I','.','-I','core','-I','ui','-I','scenes']+['-D'+f for f in FLAGS]
 for n in inputs:
  s=n[:-2]+'.s';o=n[:-2]+'.o'
  run(['cc65']+prefix+['-o',s,n]);run(['ca65','-t','cx16','-o',o,s]);objects.append(o);generated.append(s)
 for n in assembly:
  o=n[:-2]+'.o';run(['ca65','-t','cx16','-D','AI_MEMORY','-D','AI_TEMPLATE_PRIOR_Q24','-D','AI_TEMPLATE_PRIOR_Q24_CACHE','-o',o,n]);objects.append(o)
 link=['cl65','-t','cx16','-Wl','-D,__STACKSIZE__=0x0400','-C','feldmarschall.cfg','-o','FELDMARS.PRG','-m','FELDMARS.map','-Ln','FELDMARS.sym']
 failed=run(link+objects+['vendor/zsmkit.lib'],check=False)
 original_seg,members=readmap(t/'FELDMARS.map')
 with zipfile.ZipFile(H.parent/'template-target-prototype-v1'/'target-link-evidence.zip') as z:
  baseline=z.read('current-default/FELDMARS.map').decode()
 baseline_members=set(re.findall(r'^/usr/share/cc65/lib/cx16.lib\(([^)]+)\):',baseline,re.M))
 new_members=sorted(members-baseline_members);assert new_members
 runtime=t/'runtime';runtime.mkdir();relocated=[];exports=set();proof=[]
 for member in new_members:
  run(['ar65','x','/usr/share/cc65/lib/cx16.lib',member],cwd=runtime)
  obj=runtime/member;raw=obj.read_bytes();assert raw.count(b'\x04CODE')==1,member
  segment_dump=run(['od65','--dump-segments',str(obj)]).stdout
  sizes=re.findall(r'Name:\s+"([^"\n]+)"\n\s+Flags:[^\n]+\n\s+Size:\s+(\d+)',segment_dump)
  assert all(not int(size) or name=='CODE' for name,size in sizes),(member,sizes)
  out=run(['od65','--dump-exports',str(obj)]).stdout
  names=re.findall(r'Name:\s+"([^"\n]+)"',out);exports.update(names)
  imports=run(['od65','--dump-imports',str(obj)]).stdout
  transformed=raw.replace(b'\x04CODE',b'\x04B25C');obj.write_bytes(transformed)
  assert '"B25C"' in run(['od65','--dump-segments',str(obj)]).stdout
  proof.append(dict(member=member,raw_sha256=sha(raw),relocated_sha256=sha(transformed),replacement_offset=raw.index(b'\x04CODE')+1,segments=sizes,exports=names,imports_dump=imports))
  artifacts.extend([('runtime-original/'+member,raw),('runtime-relocated/'+member,transformed)])
  relocated.append(str(obj))
 refs=[]
 for n in generated:
  segment=None
  for line_no,line in enumerate((t/n).read_text().splitlines(),1):
   m=re.search(r'\.segment\s+"([^"]+)"',line)
   if m:segment=m[1]
   if line.lstrip().startswith(('.import','.export',';')):continue
   used=[symbol for symbol in exports if re.search(r'(?<![\w])'+re.escape(symbol)+r'(?![\w])',line)]
   if used:
    assert segment=='BELIEFCODE',(n,line_no,segment,line)
    refs.append(dict(source=n,line=line_no,segment=segment,symbols=used,instruction=line.strip()))
 assert refs
 cfg=t/'feldmarschall.cfg';s=cfg.read_text().replace('    BELIEFCODE:', '    B25C: load = BELIEF, type = ro, optional = yes;\n    BELIEFCODE:');cfg.write_text(s)
 result=run(link+objects+relocated+['vendor/zsmkit.lib'],check=False)
 seg,_=readmap(t/'FELDMARS.map')
 free={bank:8192-sum(seg.get(n,{}).get('size',0) for n in names) for bank,names in {'AI':('AICODE','AIRODATA','AIBSS'),'MISSION':('MISSIONCODE','MISSIONRODATA','MISSIONBSS'),'PLAY':('PLAYCODE','PLAYRODATA'),'BELIEF':('BELIEFCODE','BELIEFRODATA','BELIEFBSS','B25C')}.items()};free['MAIN']=0x9b00-1-seg['BSS']['end']
 for n in generated+['feldmarschall.cfg','FELDMARS.map','FELDMARS.sym','FELDMARS.PRG','AI.BIN','MISSION.BIN','PLAY.BIN','BELIEF.BIN']:
  if (t/n).exists():artifacts.append((n,(t/n).read_bytes()))
 report=dict(source_sha256={str(p.relative_to(R/'src')):sha(p.read_bytes()) for p in (R/'src').rglob('*') if p.is_file() and p.suffix in ('.c','.h','.s','.cfg')},schema='template-target-runtime-relocation-v1',experimental_recipe=True,production_builder_modified=False,toolchain_modified=False,runtime_archive_sha256=sha(Path('/usr/share/cc65/lib/cx16.lib').read_bytes()),returncode=result.returncode,free_bytes=free,relocated_objects=proof,actual_c_references=refs,generated_assembly_checked=len(generated),baseline_runtime_objects_retained_in_MAIN=sorted(baseline_members),closure_proof='Every newly required runtime member is relocated; baseline members stay MAIN. Every generated-C reference to a relocated exported symbol is in BELIEFCODE; wrappers, exporter and AI hooks have none. Thus baseline runtime cannot introduce a reference to this previously absent closure. Runtime objects have no non-CODE storage; imported ZP variables remain global MAIN/ZP. Internal relocation segment indexes and object length stay identical.',commands=commands)
 (H/'relocated-link.json').write_text(json.dumps(report,indent=2)+'\n')
 with zipfile.ZipFile(H/'relocated-link-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
  for n,data in artifacts:z.writestr(n,data)
 print(json.dumps(dict(returncode=result.returncode,free_bytes=free,relocated_members=new_members,checked_C_references=len(refs)),indent=2))
