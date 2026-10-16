"""Full isolated CX16 link and default-binary parity for compact priors."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT
from audit_native_belief_target_fit import FLAGS
from distribute import runtime_files

OUT = ROOT/'docs/ai-honest-campaign-2026-10-15/research/compact-backrow-native-v1'
RUNTIME = ROOT/'build/ai-compact-backrow-x16'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (OUT/'target-audit.json').exists()
    source = ROOT/'src'
    before = {str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file()}
    records = {}
    artifacts = []
    with tempfile.TemporaryDirectory(prefix='compact-backrow-full-target-') as tmp:
        for name in ('production-baseline', 'compact-backrow'):
            tree = Path(tmp)/name
            shutil.copytree(source, tree, ignore=shutil.ignore_patterns('*.o', '*.PRG', '*.BIN', '*.map', '*.sym'))
            flags = FLAGS+(['AI_BACKROW_PRIOR'] if name == 'compact-backrow' else [])
            prefix = ['-O', '-t', 'cx16', '-I', '.', '-I', 'core', '-I', 'ui', '-I', 'scenes']+['-D'+f for f in flags]
            commands = []

            def run(command):
                result = subprocess.run(command, cwd=tree, text=True, capture_output=True)
                commands.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
                return result

            assert run(['cc65']+prefix+['-o', 'ai-feature.s', 'core/ai.c']).returncode == 0
            assert run(['ca65', '-t', 'cx16', '-o', 'ai-feature.o', 'ai-feature.s']).returncode == 0
            dump = run(['od65', '-S', 'ai-feature.o']).stdout
            segments = {k: int(v) for k, v in re.findall(r'^\s+(\w+):\s+(\d+)', dump, re.M)}
            inputs = sorted(p.relative_to(tree).as_posix() for p in tree.glob('*.c'))
            assembly = []
            for folder in ('core', 'ui', 'scenes'):
                inputs += sorted(p.relative_to(tree).as_posix() for p in (tree/folder).glob('*.c'))
            for folder in ('ui', 'scenes'):
                assembly += sorted(p.relative_to(tree).as_posix() for p in (tree/folder).glob('*.s'))
            result = run(['cl65']+prefix+['--asm-define', 'AI_MEMORY', '-Wl', '-D,__STACKSIZE__=0x0400',
                         '-C', 'feldmarschall.cfg', '-o', 'FELDMARS.PRG', '-m', 'FELDMARS.map', '-Ln', 'FELDMARS.sym']+
                         inputs+assembly+['vendor/zsmkit.lib'])
            record = dict(flags=flags, ai_object_segments=segments, commands=commands,
                          link_returncode=result.returncode, input_sha256={p: sha(tree/p) for p in inputs+assembly+['feldmarschall.cfg', 'vendor/zsmkit.lib']})
            if result.returncode == 0:
                text = (tree/'FELDMARS.map').read_text().split('Segment list:', 1)[1].split('Exports list', 1)[0]
                linked = {s: dict(start=int(start, 16), size=int(size, 16)) for s, start, size in
                          re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+[0-9A-F]{6}\s+([0-9A-F]{6})', text, re.M)}
                record['linked_segments'] = linked
                record['ai_bank_free_bytes'] = 8192-sum(linked[s]['size'] for s in ('AICODE', 'AIRODATA', 'AIBSS'))
                record['main_free_below_1024_byte_stack'] = 0x9b00-linked['BSS']['start']-linked['BSS']['size']
                record['prg_bytes'] = (tree/'FELDMARS.PRG').stat().st_size
                if name == 'production-baseline':
                    reference = OUT.parent/'native-belief-main-fit/target-build-evidence.zip'
                    with zipfile.ZipFile(reference) as archive:
                        record['unchanged_default_outputs'] = {f: archive.read('production-baseline/'+f) == (tree/f).read_bytes()
                                                               for f in ('FELDMARS.PRG', 'AI.BIN', 'MISSION.BIN')}
                    assert all(record['unchanged_default_outputs'].values())
                else:
                    RUNTIME.mkdir(exist_ok=False)
                    for filename in runtime_files()+['FELDMARS.map', 'FELDMARS.sym']:
                        origin = tree/filename if (tree/filename).exists() else source/filename
                        shutil.copyfile(origin, RUNTIME/filename)
                    (RUNTIME/'provenance.json').write_text(json.dumps(dict(source_sha256=sha(source/'core/ai.c'),
                        flags=flags, outputs={p.name: sha(p) for p in RUNTIME.iterdir() if p.is_file()}), indent=2)+'\n')
                    record['isolated_runtime'] = str(RUNTIME.relative_to(ROOT))
            for filename in ('core/ai.c', 'core/ai.h', 'ai-feature.s', 'ai-feature.o', 'FELDMARS.map', 'FELDMARS.sym', 'FELDMARS.PRG', 'AI.BIN', 'MISSION.BIN', 'PLAY.BIN'):
                if (tree/filename).exists():
                    artifacts.append((name+'/'+filename, (tree/filename).read_bytes()))
            records[name] = record
    assert before == {str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file()}
    report = dict(builds=records, workspace_src_unchanged_during_audit=True, script_sha256=sha(Path(__file__)),
                  scope='Complete target link/default byte parity; banked execution and strength require separate evidence. No production outputs changed.')
    (OUT/'target-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    with zipfile.ZipFile(OUT/'target-build-evidence.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for filename, data in artifacts:
            archive.writestr(filename, data)
    print(json.dumps({k: {f: v for f, v in r.items() if f in ('link_returncode', 'ai_object_segments', 'ai_bank_free_bytes', 'main_free_below_1024_byte_stack', 'prg_bytes', 'unchanged_default_outputs')} for k, r in records.items()}, indent=2))


if __name__ == '__main__':
    main()
