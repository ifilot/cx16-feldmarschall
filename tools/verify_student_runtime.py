"""Bind the fitted student to the banked runtime and local browser package."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

from distribute import ROOT, runtime_files


def verify(runtime, model):
    nodes=json.loads(model.read_text())['nodes']
    data=b''.join(struct.pack('<BBBBh',*(n[k] for k in ('feature','threshold','left','right','value'))) for n in nodes)
    header=(ROOT/'src/core/ai_student_model_production.h').read_text()
    fields=re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(-?\d+)\s*\}',header)
    assert data==b''.join(struct.pack('<BBBBh',*map(int,n)) for n in fields)
    presence={name:(runtime/name).read_bytes().find(data) for name in ('MISSION.BIN','BRIDGE.PRG')}
    assert all(offset>=0 for offset in presence.values())
    mapping=(runtime/'FELDMARS.map').read_text();symbols=(runtime/'FELDMARS.sym').read_text()
    def end(segment): return int(re.search(r'^'+segment+r'\s+[0-9A-F]+\s+([0-9A-F]+)',mapping,re.M).group(1),16)+1
    def constant(name):return int(re.search(r'al ([0-9A-F]+) \.'+re.escape(name)+r'\b',symbols).group(1),16)
    stack=constant('__STACKSIZE__'); free=constant('__HIMEM__')-stack-end('BSS')
    tactical=end('AIBSS')-0xa000;mission=end('MISSIONBSS')-0xa000
    assert stack==1024 and free>=0 and max(tactical,mission)<=8192
    resources=json.loads((ROOT/'build/site/game/manifest.json').read_text())['resources']
    assert set(resources)==set(runtime_files())
    distribution=ROOT/'build/dist/FELDMARSCHALL.ZIP'
    assert (ROOT/'build/site/FELDMARSCHALL.ZIP').read_bytes()==distribution.read_bytes()
    with zipfile.ZipFile(distribution) as archive:
        for name in resources:
            actual=(runtime/name).read_bytes()
            assert actual==(ROOT/'src'/name).read_bytes()
            assert actual==(ROOT/'build/site/game'/name).read_bytes()
            assert actual==archive.read('FELDMARSCHALL/'+name)
    return {'model_payload_sha256':hashlib.sha256(data).hexdigest(),'model_bytes':len(data),
            'model_presence_offsets':presence,'main_free_before_reserved_stack':free,
            'reserved_stack_bytes':stack,'tactical_bank_bytes':tactical,'mission_bank_bytes':mission,
            'browser_runtime_files_matching':len(resources),'browser_download_matches_distribution':True,
            'distribution_sha256':hashlib.sha256(distribution.read_bytes()).hexdigest()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=verify(args.runtime,args.model)
    with args.out.open('x') as output:output.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
