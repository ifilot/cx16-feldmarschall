"""Isolated target-link experiment: keep prior helpers in unbanked RAM.

This does not implement a CX16 posterior generator or alter production sources.
"""
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

OUT = ROOT/'docs/ai-honest-campaign-2026-10-15/research/native-belief-main-fit'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relocate(text):
    begin = '#ifdef BANKED_AI\n#pragma code-name (push, "CODE")\n#pragma bss-name (push, "BSS")\n#endif\n'
    end = '#ifdef BANKED_AI\n#pragma bss-name (pop)\n#pragma code-name (pop)\n#endif\n'
    first = 'static uint16_t belief_flag[SQUARES], belief_bomb[SQUARES];'
    last = 'uint8_t ai_belief_priors_valid(void) { return belief_owner!=0; }'
    assert text.count(first) == text.count(last) == 1
    text = text.replace(first, begin+first).replace(last, last+'\n'+end)
    first = 'static int16_t expected_at(uint8_t a, uint8_t square) {'
    last = '    return numerator/((int32_t)AI_BELIEF_ONE*hidden_mobile);\n}'
    assert text.count(first) == text.count(last) == 1
    return text.replace(first, begin+first).replace(last, last+'\n'+end)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    source = ROOT/'src'
    before = {str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file()}
    records = {}
    artifacts = []
    with tempfile.TemporaryDirectory(prefix='native-prior-main-fit-') as tmp:
        for name in ('production-baseline', 'unmodified-priors', 'unbanked-priors'):
            tree = Path(tmp)/name
            shutil.copytree(source, tree, ignore=shutil.ignore_patterns('*.o', '*.PRG', '*.BIN', '*.map', '*.sym'))
            if name == 'unbanked-priors':
                path = tree/'core/ai.c'
                path.write_text(relocate(path.read_text()))
                artifacts.append((name+'/ai.c', path.read_bytes()))
            flags = FLAGS+(['AI_BELIEF_PRIORS'] if name != 'production-baseline' else [])
            prefix = ['-O', '-t', 'cx16', '-I', '.', '-I', 'core', '-I', 'ui', '-I', 'scenes']+['-D'+f for f in flags]
            commands = []

            def run(command):
                result = subprocess.run(command, cwd=tree, text=True, capture_output=True)
                commands.append(dict(command=command, returncode=result.returncode,
                                     stdout=result.stdout, stderr=result.stderr))
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
            command = ['cl65']+prefix+['--asm-define', 'AI_MEMORY', '-Wl', '-D,__STACKSIZE__=0x0400',
                                      '-C', 'feldmarschall.cfg', '-o', 'FELDMARS.PRG',
                                      '-m', 'FELDMARS.map', '-Ln', 'FELDMARS.sym']+inputs+assembly+['vendor/zsmkit.lib']
            result = run(command)
            record = dict(flags=flags, ai_object_segments=segments, commands=commands,
                          link_returncode=result.returncode, ai_source_sha256=sha(tree/'core/ai.c'),
                          input_sha256={p: sha(tree/p) for p in inputs+assembly+['feldmarschall.cfg', 'vendor/zsmkit.lib']})
            if result.returncode == 0:
                text = (tree/'FELDMARS.map').read_text().split('Segment list:', 1)[1].split('Exports list', 1)[0]
                linked = {s: int(size, 16) for s, size in re.findall(r'^(\w+)\s+[0-9A-F]{6}\s+[0-9A-F]{6}\s+([0-9A-F]{6})', text, re.M)}
                record['linked_segments'] = linked
                record['ai_bank_used_bytes'] = sum(linked.get(s, 0) for s in ('AICODE', 'AIRODATA', 'AIBSS'))
                record['ai_bank_free_bytes'] = 8192-record['ai_bank_used_bytes']
                record['prg_bytes'] = (tree/'FELDMARS.PRG').stat().st_size
            for filename in ('ai-feature.s', 'ai-feature.o', 'FELDMARS.map', 'FELDMARS.sym', 'FELDMARS.PRG', 'AI.BIN', 'MISSION.BIN'):
                if (tree/filename).is_file():
                    artifacts.append((name+'/'+filename, (tree/filename).read_bytes()))
            records[name] = record
    assert before == {str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file()}
    assert records['production-baseline']['link_returncode'] == 0
    report = dict(builds=records, script_sha256=sha(Path(__file__)), workspace_src_unchanged=True,
                  scope='Complete isolated CX16 link only. Prior storage, setters and expected-value helper moved to always-visible main memory. No posterior generator, new policy, strength games or hardware runtime claim.',
                  bank_contract='The unbanked expected_at helper reads AI-bank private variables only while called synchronously from the active AI bank. It performs no bank switch. Prior arrays and setter/clear helpers are always visible. Actual banked execution still requires verification.')
    (OUT/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    with zipfile.ZipFile(OUT/'target-build-evidence.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for filename, data in artifacts:
            archive.writestr(filename, data)
    print(json.dumps({k: {n: v for n, v in r.items() if n in ('link_returncode', 'ai_bank_free_bytes', 'ai_object_segments', 'prg_bytes')} for k, r in records.items()}, indent=2))


if __name__ == '__main__':
    main()
