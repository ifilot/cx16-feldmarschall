"""Full banked CX16 link in copied/tmp source trees; never production outputs."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
import ctypes

from ai_registry import ROOT

OUT=ROOT/'docs/ai-honest-campaign-2026-10-16/research/open-reserve'
FLAGS=['BANKED_AI','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2',
       'AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD','AI_POLICY_DEPLOYMENT','AI_DEPLOY_FORTRESS_ONLY']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def banked_fixture(trees,tmp):
    """Execute the production gateway/bank24 setup and compare native bytes/RNG."""
    from distribute import runtime_files
    from test_colors import start
    from test_ai_selection import next_random
    from test_ai_selection_banked import call
    records=[];seed_cases=[1,17,791,65535]+[seed for seed in range(1,65536) if next_random(seed)>65530]
    for name,tree in trees.items():
        library=tmp/(name+'.so')
        sources=[str(tree/'core'/(part+'.c')) for part in ('pieces','board','rules','random','ai_level','setup','ai_deploy')]
        flags=['AI_TEST','AI_DEPLOY_FORTRESS_ONLY']+(['AI_FORTRESS_OPEN_RESERVE'] if name=='open-reserve' else [])
        subprocess.run(['gcc','-shared','-fPIC','-O2','-Wno-unknown-pragmas','-I'+str(tree/'core')]+
            ['-D'+f for f in flags]+sources+['-o',str(library)],check=True,capture_output=True)
        lib=ctypes.CDLL(str(library));cells=(ctypes.c_uint8*100).in_dll(lib,'board')
        level=ctypes.c_uint8.in_dll(lib,'ai_difficulty');rules=ctypes.c_uint8.in_dll(lib,'game_rules')
        lib.random_next.restype=ctypes.c_uint16
        symbols=(tree/'FELDMARS.sym').read_text()
        def symbol(function):return int(re.search(r'al ([0-9A-F]+) \._'+function+r'\b',symbols).group(1),16)
        runtime=tmp/(name+'-runtime');runtime.mkdir()
        for filename in runtime_files():
            source=tree/filename if (tree/filename).exists() else ROOT/'src'/filename
            shutil.copyfile(source,runtime/filename)
        session=start(runtime)
        try:
            session.emu.request('set_registers',ram_bank=22)
            for difficulty in (1,0,2):
                for blue in (0,1):
                    for seed in (seed_cases if difficulty==1 else (1,17)):
                        level.value=difficulty;rules.value=0;lib.board_clear();lib.random_seed(seed);lib.setup_ai(blue)
                        expected=bytes(cells);expected_rng=lib.random_next()
                        session.emu.write_memory(symbol('ai_difficulty'),bytes([difficulty]))
                        session.emu.write_memory(symbol('game_rules'),b'\x00')
                        call(session,'board_clear',0,symbol);call(session,'random_seed',seed,symbol)
                        before=session.emu.request('status');call(session,'setup_ai',blue,symbol);after=session.emu.request('status')
                        actual=bytes(session.emu.read_memory(symbol('board'),100));assert actual==expected,(name,difficulty,blue,seed)
                        for reflected in (False,True):
                            transform=lambda data:b''.join(data[row:row+10][::-1] for row in range(0,100,10))
                            view=transform(actual) if reflected else actual
                            reference=transform(expected) if reflected else expected
                            assert view==reference,(name,difficulty,blue,seed,reflected)
                        call(session,'random_next',0,symbol);state=session.emu.request('status')
                        assert state['a']|state['x']<<8==expected_rng,(name,difficulty,blue,seed,'RNG')
                        records.append(dict(build=name,difficulty=difficulty,army=blue,seed=seed,
                            setup_cycles=after['cycles']-before['cycles'],board_sha256=hashlib.sha256(actual).hexdigest(),
                            board_and_next_rng_match_native=True,canonical_and_reflected_serialization_match=True,caller_bank_restored=after['ram_bank']==22))
        finally:session.emu.close()
    for baseline in [r for r in records if r['build']=='fortress']:
        candidate=next(r for r in records if r['build']=='open-reserve' and all(r[k]==baseline[k] for k in ('difficulty','army','seed')))
        if baseline['difficulty']!=1:assert candidate['board_sha256']==baseline['board_sha256']
    return dict(passed=True,real_banked_setup_calls=len(records),records=records,
        first_draw_rejection_seeds=seed_cases[4:],scope='Ordinary production deployment gateway only; no source-template prior or full-turn AI execution. Horizontal reflection is checked on returned board bytes; rotation belongs to the host tournament runner.',
        timing='Emulator CPU-cycle deltas include real gateway and any interrupts; not isolated instruction costs or hardware latency.')

def main():
    original=ROOT/'src';workspace_hashes={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()}
    OUT.mkdir(parents=True,exist_ok=True)
    frozen_path=next((ROOT/'docs/ai-honest-campaign-2026-10-16').glob('cycle-115*/frozen-policies.json'))
    frozen=json.loads(frozen_path.read_text())
    spec=frozen['student-fortress-open-reserve-template-v1-normal']
    with zipfile.ZipFile(ROOT/spec['archive']) as archive:
        frozen_deploy=archive.read('tools/new_campaign_open_reserve_deploy.c')
    assert hashlib.sha256(frozen_deploy).hexdigest()==sha(ROOT/'tools/new_campaign_open_reserve_deploy.c')
    records={};saved=[];trees={}
    with tempfile.TemporaryDirectory(prefix='open-reserve-full-cx16-') as tmp:
        for candidate in (False,True):
            name='open-reserve' if candidate else 'fortress';tree=Path(tmp)/name
            shutil.copytree(original,tree,ignore=shutil.ignore_patterns('*.o','*.PRG','*.BIN','*.map','*.sym'))
            trees[name]=tree
            if candidate:(tree/'core/ai_deploy.c').write_bytes(frozen_deploy)
            # Graphics binary files are runtime-only, not C/asm build inputs.
            # Generated gfx/app_info/music headers and vendor library are copied.
            flags=FLAGS+(['AI_FORTRESS_OPEN_RESERVE'] if candidate else [])
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
        banked=banked_fixture(trees,Path(tmp)) if all(r['returncode']==0 for r in records.values()) else None
        after={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()}
        assert workspace_hashes==after,'Workspace source/build outputs changed during audit'
        report=dict(passed=all(r['returncode']==0 for r in records.values()),
            scope='Deployment component on ordinary production Classic Student only; excludes desktop public-template adapter and full prior; no strength or hardware qualification.',
            toolchain=subprocess.run(['cl65','--version'],capture_output=True,text=True).stderr.strip(),
            control_source_sha256=sha(original/'core/ai_deploy.c'),candidate_source_sha256=hashlib.sha256(frozen_deploy).hexdigest(),script_sha256=sha(Path(__file__)),
            frozen_policy=spec['id'],frozen_policy_archive_sha256=spec['source_sha256'],banked_fixture=banked,
            recipe='src/Makefile full C/assembly source set, -O -t cx16, BANKED_AI and all six production AI flags; existing generated headers/vendor library; original linker config and1024byte C stack.',
            workspace_all_file_hashes_unchanged=True,builds=records,
            limitations=['Production artwork/runtime files were not regenerated or installed.',
                'This is a RAM-bank linked program, not a new system ROM. Output sizes are PRG and loadable bank binaries.',
                'Successful static link proves bank capacity for this source tree/toolchain only; banked deployment fixture covers setup/gateway/RNG, not full hardware gameplay.'])
        (OUT/'component-target.json').write_text(json.dumps(report,indent=2)+'\n')
        with zipfile.ZipFile(OUT/'component-target-build.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for filename,data in saved:archive.writestr(filename,data)
        print(json.dumps(dict(banked_fixture=banked,passed=report['passed'],builds={k:dict(returncode=v['returncode'],banks=v.get('banks'),outputs=v.get('outputs')) for k,v in records.items()}),indent=2))

if __name__=='__main__':main()
