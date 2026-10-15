"""Full banked CX16 link in copied/tmp source trees; never production outputs."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT

OUT=ROOT/'docs/ai-honest-campaign-2026-10-15/research/deployment-double-shell'
FLAGS=['BANKED_AI','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2',
       'AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD','AI_POLICY_DEPLOYMENT','AI_DEPLOY_FORTRESS_ONLY']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    original=ROOT/'src';workspace_hashes={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()}
    records={};saved=[]
    with tempfile.TemporaryDirectory(prefix='double-shell-full-cx16-') as tmp:
        for candidate in (False,True):
            name='double-shell' if candidate else 'fortress';tree=Path(tmp)/name
            shutil.copytree(original,tree,ignore=shutil.ignore_patterns('*.o','*.PRG','*.BIN','*.map','*.sym'))
            # Graphics binary files are runtime-only, not C/asm build inputs.
            # Generated gfx/app_info/music headers and vendor library are copied.
            flags=FLAGS+(['AI_DEPLOY_DOUBLE_SHELL'] if candidate else [])
            inputs=sorted(p.relative_to(tree).as_posix() for p in tree.glob('*.c'))
            for folder in ('core','ui','scenes'):inputs+=sorted(p.relative_to(tree).as_posix() for p in (tree/folder).glob('*.c'))
            assembly=[]
            for folder in ('ui','scenes'):assembly+=sorted(p.relative_to(tree).as_posix() for p in (tree/folder).glob('*.s'))
            command=['cl65','-O','-t','cx16','-I','.','-I','core','-I','ui','-I','scenes']
            command+=['-D'+flag for flag in flags]+['--asm-define','AI_MEMORY','-Wl','-D,__STACKSIZE__=0x0400',
                '-C','feldmarschall.cfg','-o','FELDMARS.PRG','-m','FELDMARS.map','-Ln','FELDMARS.sym']
            command+=inputs+assembly+['vendor/zsmkit.lib']
            result=subprocess.run(command,cwd=tree,text=True,capture_output=True)
            log=f'command: {json.dumps(command)}\nreturncode: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}'
            (OUT/(name+'-full-link.log')).write_text(log)
            record=dict(command=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,flags=flags,
                copied_inputs_sha256={path:sha(tree/path) for path in inputs+assembly+['feldmarschall.cfg','vendor/zsmkit.lib']},
                header_sha256={str(path.relative_to(tree)):sha(path) for path in tree.rglob('*.h')})
            if result.returncode==0:
                maptext=(tree/'FELDMARS.map').read_text();segments={}
                table=maptext.split('Segment list:',1)[1].split('Exports list',1)[0]
                for seg,start,end,size in re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})',table,re.M):
                    segments[seg]=dict(start=int(start,16),end=int(end,16),bytes=int(size,16))
                bank_groups={'PLAY':['PLAYCODE','PLAYRODATA'],'AI':['AICODE','AIRODATA','AIBSS'],
                    'MISSION':['MISSIONCODE','MISSIONRODATA','MISSIONBSS']}
                banks={bank:dict(capacity_bytes=8192,used_bytes=sum(segments.get(seg,{}).get('bytes',0) for seg in names),
                    free_bytes=8192-sum(segments.get(seg,{}).get('bytes',0) for seg in names)) for bank,names in bank_groups.items()}
                record.update(segments=segments,banks=banks,outputs={})
                for filename in ('FELDMARS.PRG','PLAY.BIN','AI.BIN','MISSION.BIN','FELDMARS.map','FELDMARS.sym'):
                    path=tree/filename;record['outputs'][filename]=dict(bytes=path.stat().st_size,sha256=sha(path));saved.append((name+'/'+filename,path.read_bytes()))
                assert all(v['free_bytes']>=0 for v in banks.values())
            records[name]=record
        after={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()}
        assert workspace_hashes==after,'Workspace source/build outputs changed during audit'
        report=dict(passed=all(r['returncode']==0 for r in records.values()),
            scope='Full production banked CX16 link only, no hardware or game-strength validation.',
            toolchain=subprocess.run(['cl65','--version'],capture_output=True,text=True).stderr.strip(),
            source_sha256=sha(original/'core/ai_deploy.c'),script_sha256=sha(Path(__file__)),
            recipe='src/Makefile full C/assembly source set, -O -t cx16, BANKED_AI and all six production AI flags; existing generated headers/vendor library; original linker config and1024byte C stack.',
            workspace_all_file_hashes_unchanged=True,builds=records,
            limitations=['Production artwork/runtime files were not regenerated or installed.',
                'This is a RAM-bank linked program, not a new system ROM. Output sizes are PRG and loadable bank binaries.',
                'Successful static link proves bank capacity for this source tree/toolchain only, not gameplay correctness or emulator/hardware startup.'])
        (OUT/'full-target-link.json').write_text(json.dumps(report,indent=2)+'\n')
        with zipfile.ZipFile(OUT/'full-target-link-build.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for filename,data in saved:archive.writestr(filename,data)
        print(json.dumps(dict(passed=report['passed'],builds={k:dict(returncode=v['returncode'],banks=v.get('banks'),outputs=v.get('outputs')) for k,v in records.items()}),indent=2))

if __name__=='__main__':main()
