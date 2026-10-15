"""Measure unmodified native-belief feature's complete CX16 target fit."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT

OUT=ROOT/'docs/ai-honest-campaign-2026-10-15/research/native-belief-target-fit'
FLAGS=['BANKED_AI','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2','AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True);src=ROOT/'src'
    before={str(p.relative_to(src)):sha(p) for p in src.rglob('*') if p.is_file()};records={};artifacts=[]
    with tempfile.TemporaryDirectory(prefix='native-belief-full-cx16-') as tmp:
        for prior in (False,True):
            name='with-belief-priors' if prior else 'production-baseline';tree=Path(tmp)/name
            shutil.copytree(src,tree,ignore=shutil.ignore_patterns('*.o','*.PRG','*.BIN','*.map','*.sym'))
            flags=FLAGS+(['AI_BELIEF_PRIORS'] if prior else [])
            prefix=['-O','-t','cx16','-I','.','-I','core','-I','ui','-I','scenes']+['-D'+f for f in flags]
            commands=[]
            def run(command):
                result=subprocess.run(command,cwd=tree,text=True,capture_output=True)
                commands.append(dict(command=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr));return result
            result=run(['cc65']+prefix+['-o','ai-feature.s','core/ai.c']);assert result.returncode==0
            result=run(['ca65','-t','cx16','-o','ai-feature.o','ai-feature.s']);assert result.returncode==0
            dump=run(['od65','-S','ai-feature.o']).stdout;segments={k:int(v) for k,v in re.findall(r'^\s+(\w+):\s+(\d+)',dump,re.M)}
            inputs=sorted(p.relative_to(tree).as_posix() for p in tree.glob('*.c'))
            for folder in ('core','ui','scenes'):inputs+=sorted(p.relative_to(tree).as_posix() for p in (tree/folder).glob('*.c'))
            assembly=[]
            for folder in ('ui','scenes'):assembly+=sorted(p.relative_to(tree).as_posix() for p in (tree/folder).glob('*.s'))
            command=['cl65']+prefix+['--asm-define','AI_MEMORY','-Wl','-D,__STACKSIZE__=0x0400','-C','feldmarschall.cfg',
                '-o','FELDMARS.PRG','-m','FELDMARS.map','-Ln','FELDMARS.sym']+inputs+assembly+['vendor/zsmkit.lib']
            result=run(command);record=dict(flags=flags,ai_object_segment_bytes=segments,link_returncode=result.returncode,
                commands=commands,input_sha256={path:sha(tree/path) for path in inputs+assembly+['feldmarschall.cfg','vendor/zsmkit.lib']})
            if result.returncode==0:
                text=(tree/'FELDMARS.map').read_text().split('Segment list:',1)[1].split('Exports list',1)[0]
                linked={seg:int(size,16) for seg,size in re.findall(r'^(\w+)\s+[0-9A-F]{6}\s+[0-9A-F]{6}\s+([0-9A-F]{6})',text,re.M)}
                record['linked_segments']=linked;record['ai_bank_used_bytes']=sum(linked.get(s,0) for s in ('AICODE','AIRODATA','AIBSS'))
                record['ai_bank_free_bytes']=8192-record['ai_bank_used_bytes']
            (OUT/(name+'.log')).write_text(json.dumps(record,indent=2)+'\n')
            for filename in ['ai-feature.s','ai-feature.o','FELDMARS.map','FELDMARS.sym']:
                if (tree/filename).exists():artifacts.append((name+'/'+filename,(tree/filename).read_bytes()))
            records[name]=record
        after={str(p.relative_to(src)):sha(p) for p in src.rglob('*') if p.is_file()};assert before==after
    baseline=records['production-baseline'];candidate=records['with-belief-priors'];assert baseline['link_returncode']==0
    delta={segment:candidate['ai_object_segment_bytes'].get(segment,0)-baseline['ai_object_segment_bytes'].get(segment,0)
        for segment in baseline['ai_object_segment_bytes'].keys()|candidate['ai_object_segment_bytes'].keys()}
    report=dict(audit_completed=True,prototype_full_target_link_passed=candidate['link_returncode']==0,
        source_sha256=sha(src/'core/ai.c'),script_sha256=sha(Path(__file__)),workspace_src_unchanged=True,
        object_segment_deltas=delta,baseline_ai_bank_free_bytes=baseline['ai_bank_free_bytes'],builds=records,
        scope='Target feasibility measurement only. No frozen prototype or source was changed. Desktop protocols and tournament outcomes do not establish CX16 readiness.',
        caveat='This production-game build enables core AI_BELIEF_PRIORS only; desktop engine AI_TEST/AI_DIAGNOSTICS command features are not part of the CX16 UI. No target posterior-computation integration or hardware startup is attempted.')
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(OUT/'target-build-evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for filename,data in artifacts:archive.writestr(filename,data)
    print(json.dumps(dict(prototype_full_target_link_passed=report['prototype_full_target_link_passed'],object_segment_deltas=delta,
        baseline_ai_bank_free_bytes=baseline['ai_bank_free_bytes'],link_diagnostics=candidate['commands'][-1]['stderr']),indent=2))

if __name__=='__main__':main()
