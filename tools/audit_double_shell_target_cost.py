"""Isolated cc65 target cost audit; no production outputs or frozen edits."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT

OUT=ROOT/'docs/ai-honest-campaign-2026-10-15/research/deployment-double-shell'
FLAGS=['AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2','AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD','AI_POLICY_DEPLOYMENT']
VARIANTS={'mixture':[],'fortress':['AI_DEPLOY_FORTRESS_ONLY'],
          'double-shell':['AI_DEPLOY_FORTRESS_ONLY','AI_DEPLOY_DOUBLE_SHELL']}

HARNESS='''#include <stdint.h>
#include <stdio.h>
#include "board.h"
#include "ai.h"
#include "setup.h"
uint8_t board[SQUARES], game_rules=0, ai_difficulty=AI_NORMAL;
static uint16_t calls;
uint16_t random_next(void) { ++calls; return 123u; }
void setup_random(uint8_t blue) { (void)blue; }
int main(int argc, char **argv) {
 uint16_t n,sum=0;uint8_t i,blue=(argc>1 && argv[1][0]=='1');
 for(n=0;n<1000u;++n) setup_ai(blue);
 for(i=0;i<100u;++i) sum+=board[i];
 printf("%u %u\\n",calls,sum);
 return 0;
}
'''

def main():
    records=[];results={};sim={}
    def run(command,folder):
        result=subprocess.run(command,cwd=folder,capture_output=True,text=True)
        records.append(dict(command=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
        if result.returncode:raise RuntimeError(records[-1])
        return result.stdout+result.stderr
    with tempfile.TemporaryDirectory(prefix='double-shell-cc65-') as tmp:
        folder=Path(tmp);harness=folder/'cost-harness.c';harness.write_text(HARNESS)
        versions={tool:run([tool,'--version'],tmp).strip() for tool in ['cc65','ca65','cl65','sim65']}
        for banked in (False,True):
            for variant,extra in VARIANTS.items():
                name=('banked-' if banked else 'plain-')+variant
                flags=FLAGS+extra+(['BANKED_AI'] if banked else [])
                assembly=folder/(name+'.s');obj=folder/(name+'.o')
                run(['cc65','-O','-t','cx16','-I',str(ROOT/'src/core')]+['-D'+f for f in flags]+[
                    '-o',str(assembly),str(ROOT/'src/core/ai_deploy.c')],tmp)
                run(['ca65','-t','cx16','-o',str(obj),str(assembly)],tmp)
                dump=run(['od65','-S',str(obj)],tmp);(folder/(name+'-segments.txt')).write_text(dump)
                segments={k:int(v) for k,v in re.findall(r'^\s+(\w+):\s+(\d+)',dump,re.M)}
                assert segments, dump
                results[name]=dict(segments=segments,object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),
                    assembly_sha256=hashlib.sha256(assembly.read_bytes()).hexdigest(),flags=flags)
        for variant,extra in VARIANTS.items():
            # cc65/cl65 write object files beside source files unless explicitly
            # compiled separately. Copy both inputs into/tmp before using cl65.
            source=folder/'ai_deploy.c';source.write_bytes((ROOT/'src/core/ai_deploy.c').read_bytes())
            program=folder/('sim-'+variant)
            run(['cl65','-O','-t','sim65c02','-I',str(ROOT/'src/core')]+['-D'+f for f in FLAGS+extra]+[
                '-o',str(program),str(harness),str(source)],tmp)
            sim[variant]={}
            for side in (0,1):
                output=run(['sim65','-c',str(program),str(side)],tmp)
                cycles=re.search(r'(\d+)\s+cycles',output,re.I)
                assert cycles,output
                sim[variant][str(side)]=dict(total_cycles=int(cycles[1]),calls=1000,output=output)
        deltas={}
        for bank in ('plain','banked'):
            control=results[bank+'-fortress']['segments'];candidate=results[bank+'-double-shell']['segments']
            delta={segment:candidate.get(segment,0)-control.get(segment,0) for segment in control.keys()|candidate.keys()}
            assert all(delta.get(segment,0)==0 for segment in ('BSS','DATA','RODATA','MISSIONBSS','MISSIONRODATA'))
            deltas[bank]=delta
        cycle_deltas={side:(sim['double-shell'][side]['total_cycles']-sim['fortress'][side]['total_cycles'])/1000 for side in ('0','1')}
        report=dict(passed=True,source_sha256=hashlib.sha256((ROOT/'src/core/ai_deploy.c').read_bytes()).hexdigest(),
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),versions=versions,
            recipe='src/Makefile CFLAGS -O -t cx16; same production AI flags; isolated compile and assemble of ai_deploy.c only.',
            target_objects=results,candidate_minus_fortress_segment_bytes=deltas,
            sim65c02=sim,candidate_minus_fortress_cycles_per_setup=cycle_deltas,
            limitations=['Object size is exact for this cc65 recipe; full CX16 image linking/bank capacity was not tested.',
                'sim65c02 cycle differences use nonbanked real setup_ai with deterministic RNG stub and1000 calls. Full hardware runtime and bank gateway were not measured.',
                'Whole simulator harness delta may include small code-placement/page-crossing effects; not an instruction-by-instruction cycle proof.',
                'No production object/executable, core source, registry or frozen archive was changed.'],commands=records)
        (OUT/'target-cost.json').write_text(json.dumps(report,indent=2)+'\n')
        with zipfile.ZipFile(OUT/'target-cost-build.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(folder.iterdir()):
                if path.is_file():archive.write(path,path.name)
        print(json.dumps(dict(passed=True,deltas=deltas,cycles=cycle_deltas),indent=2))

if __name__=='__main__':main()
