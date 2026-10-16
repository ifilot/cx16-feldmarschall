"""Measure current untouched-source baseline beside the isolated hook probe."""
from pathlib import Path
import subprocess,tempfile,shutil,json,re,zipfile
H=Path(__file__).resolve().parent;R=H.parents[3]
flags=['BANKED_AI','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2','AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD']
with tempfile.TemporaryDirectory(prefix='template-port-baseline-') as temp:
 t=Path(temp)/'src';shutil.copytree(R/'src',t,ignore=shutil.ignore_patterns('*.o','*.PRG','*.BIN','*.map','*.sym'))
 inputs=sorted(p.relative_to(t).as_posix() for p in t.glob('*.c'))
 for folder in ('core','ui','scenes'):inputs+=sorted(p.relative_to(t).as_posix() for p in (t/folder).glob('*.c'))
 assembly=[]
 for folder in ('ui','scenes'):assembly+=sorted(p.relative_to(t).as_posix() for p in (t/folder).glob('*.s'))
 cmd=['cl65','-O','-t','cx16','-I','.','-I','core','-I','ui','-I','scenes']+['-D'+f for f in flags]+['--asm-define','AI_MEMORY','-Wl','-D,__STACKSIZE__=0x0400','-C','feldmarschall.cfg','-o','FELDMARS.PRG','-m','FELDMARS.map']+inputs+assembly+['vendor/zsmkit.lib']
 p=subprocess.run(cmd,cwd=t,text=True,capture_output=True);assert p.returncode==0,p.stderr
 text=(t/'FELDMARS.map').read_text().split('Segment list:',1)[1].split('Exports list',1)[0]
 seg={n:dict(start=int(a,16),end=int(b,16),size=int(s,16)) for n,a,b,s in re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})',text,re.M)}
 out=dict(returncode=p.returncode,command=cmd,stdout=p.stdout,stderr=p.stderr,segments=seg)
 out['free_bytes']={bank:8192-sum(seg[n]['size'] for n in names) for bank,names in {'AI':('AICODE','AIRODATA','AIBSS'),'MISSION':('MISSIONCODE','MISSIONRODATA','MISSIONBSS'),'PLAY':('PLAYCODE','PLAYRODATA')}.items()};out['free_bytes']['MAIN']=0x9b00-1-seg['BSS']['end']
 (H/'current-baseline-link.json').write_text(json.dumps(out,indent=2)+'\n');(H/'current-baseline.map').write_bytes((t/'FELDMARS.map').read_bytes());print(out['free_bytes'])
