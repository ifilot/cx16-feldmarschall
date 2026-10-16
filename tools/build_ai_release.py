"""Build the banked AI release without modifying the installed cc65 library.

The release's long-arithmetic closure executes in bank 25. Generated call sites
and all remaining linked library imports are checked before accepting the link.
All intermediates live outside src; outputs are copied only after every check.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFINES = ['BANKED_AI', 'AI_MISSIONS', 'AI_MEMORY', 'AI_STUDENT', 'AI_STUDENT_V2',
           'AI_STUDENT_PRODUCTION', 'AI_STUDENT_COOP_GUARD',
           'AI_TEMPLATE_PRIOR_Q24', 'AI_TEMPLATE_PRIOR_Q24_CACHE',
           'AI_DEPLOY_FORTRESS_NORMAL']
HELPERS = ['asleax1.o', 'asleax4.o', 'asreax4.o', 'land.o', 'lbneg.o',
           'lcmp.o', 'lge.o', 'lgt.o', 'linc.o', 'lne.o', 'lsave.o',
           'lsub.o', 'lsubeqsp.o', 'steaxsp.o']
OUTPUTS = ['FELDMARS.PRG', 'PLAY.BIN', 'AI.BIN', 'MISSION.BIN', 'BELIEF.BIN',
           'FELDMARS.map', 'FELDMARS.sym']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def symbols(dump):
    return set(re.findall(r'Name:\s+"([^"\n]+)"', dump))


def build(source, destination, library, defines=DEFINES):
    source, destination, library = map(lambda p: Path(p).resolve(), (source, destination, library))
    commands = []
    inputs = sorted([*source.glob('*.c'), *source.glob('core/*.c'),
                     *source.glob('ui/*.c'), *source.glob('scenes/*.c')])
    assembly = sorted([*source.glob('ui/*.s'), *source.glob('scenes/*.s')])
    assert inputs and assembly and library.is_file()
    source_hashes = {str(p.relative_to(source)): sha(p) for p in
                     [*inputs, *assembly, *source.rglob('*.h'),
                      source/'feldmarschall.cfg', source/'vendor/zsmkit.lib']}
    with tempfile.TemporaryDirectory(prefix='feldmarschall-release-') as temporary:
        work = Path(temporary)

        def run(argv, cwd=source):
            result = subprocess.run(list(map(str, argv)), cwd=cwd, text=True, capture_output=True)
            commands.append(dict(argv=list(map(str, argv)), returncode=result.returncode,
                                 stdout=result.stdout, stderr=result.stderr))
            if result.returncode:
                raise RuntimeError(json.dumps(commands[-1], indent=2))
            return result.stdout

        objects, generated = [], []
        flags = ['-O', '-t', 'cx16'] + [item for folder in ('.', 'core', 'ui', 'scenes')
                                      for item in ('-I', str(source/folder))]
        flags += ['-D'+flag for flag in defines]
        for path in inputs:
            stem = work/'objects'/path.relative_to(source).with_suffix('')
            stem.parent.mkdir(parents=True, exist_ok=True)
            asm, obj = stem.with_suffix('.s'), stem.with_suffix('.o')
            run(['cc65', *flags, '-o', asm, path])
            run(['ca65', '-t', 'cx16', '-o', obj, asm])
            objects.append(obj)
            generated.append(asm)
        for path in assembly:
            obj = work/'objects'/path.relative_to(source).with_suffix('.o')
            obj.parent.mkdir(parents=True, exist_ok=True)
            run(['ca65', '-t', 'cx16', *['-D'+f for f in defines], '-o', obj, path])
            objects.append(obj)

        runtime = work/'runtime'
        runtime.mkdir()
        exports, relocated, helper_proof = set(), [], []
        for member in HELPERS:
            run(['ar65', 'x', library, member], cwd=runtime)
            obj = runtime/member
            raw = obj.read_bytes()
            dump = run(['od65', '--dump-segments', obj])
            segments = re.findall(r'Name:\s+"([^"\n]+)"\n\s+Flags:[^\n]+\n\s+Size:\s+(\d+)', dump)
            assert segments and all(name == 'CODE' or int(size) == 0 for name, size in segments), member
            assert raw.count(b'\x04CODE') == 1, member
            exported = symbols(run(['od65', '--dump-exports', obj]))
            exports.update(exported)
            obj.write_bytes(raw.replace(b'\x04CODE', b'\x04B25C'))
            assert '"B25C"' in run(['od65', '--dump-segments', obj])
            relocated.append(obj)
            helper_proof.append(dict(member=member, original_sha256=hashlib.sha256(raw).hexdigest(),
                                     relocated_sha256=sha(obj), exports=sorted(exported)))

        references = []
        for path in [*generated, *assembly]:
            segment = None
            for number, line in enumerate(path.read_text().splitlines(), 1):
                match = re.search(r'\.segment\s+"([^"]+)"', line)
                if match:
                    segment = match[1]
                if line.lstrip().startswith(('.import', '.export', ';')):
                    continue
                used = [symbol for symbol in exports
                        if re.search(r'(?<!\w)'+re.escape(symbol)+r'(?!\w)', line)]
                if used:
                    assert segment == 'BELIEFCODE', (path.name, number, segment, used)
                    references.append(dict(source=path.name, line=number, symbols=sorted(used)))
        assert references
        config = work/'feldmarschall.cfg'
        text = (source/'feldmarschall.cfg').read_text()
        assert text.count('    BELIEFCODE:') == 1
        config.write_text(text.replace('    BELIEFCODE:',
                          '    B25C: load = BELIEF, type = ro, optional = yes;\n    BELIEFCODE:'))
        run(['cl65', '-t', 'cx16', '-Wl', '-D,__STACKSIZE__=0x0400', '-C', config,
             '-o', work/'FELDMARS.PRG', '-m', work/'FELDMARS.map', '-Ln', work/'FELDMARS.sym',
             *objects, *relocated, source/'vendor/zsmkit.lib'], cwd=work)
        mapping = (work/'FELDMARS.map').read_text()
        table = mapping.split('Segment list:', 1)[1].split('Exports list', 1)[0]
        segments = {name: dict(start=int(start, 16), end=int(end, 16), size=int(size, 16))
                    for name, start, end, size in re.findall(
                        r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})', table, re.M)}
        groups = dict(PLAY=['PLAYCODE', 'PLAYRODATA'], AI=['AICODE', 'AIRODATA', 'AIBSS'],
                      MISSION=['MISSIONCODE', 'MISSIONRODATA', 'MISSIONBSS'],
                      BELIEF=['BELIEFCODE', 'BELIEFRODATA', 'BELIEFBSS', 'B25C'])
        free = {bank: 8192-sum(segments.get(name, {}).get('size', 0) for name in names)
                for bank, names in groups.items()}
        free['MAIN'] = 0x9b00-1-segments['BSS']['end']
        assert all(value >= 0 for value in free.values()), free

        # No runtime object left in MAIN may call the bank-local closure.
        linked = set(re.findall(re.escape(str(library))+r'\(([^)]+)\):', mapping))
        for member in sorted(linked):
            run(['ar65', 'x', library, member], cwd=runtime)
            imports = symbols(run(['od65', '--dump-imports', runtime/member]))
            assert not imports & exports, (member, sorted(imports & exports))
        destination.mkdir(parents=True, exist_ok=True)
        # Publish the linked private layout for target qualification; never infer
        # current offsets from an archived research build.
        template_asm = next(p for p in generated if p.name == 'ai_template.s').read_text()
        belief_symbols, offset = {}, 0
        private_layout = re.split(r'\.segment\s+"BELIEFBSS"', template_asm, maxsplit=1)[1]
        private_layout = private_layout.split('.segment', 1)[0]
        for name, length in re.findall(r'_(\w+):\s+\.res\s+(\d+)', private_layout):
            size = int(length)
            belief_symbols[name] = dict(offset=offset, size=size)
            offset += size
        assert 'cache_valid' in belief_symbols and 'history' in belief_symbols
        memory_asm = next(p for p in generated if p.name == 'ai_memory.s').read_text()
        memory_layout = re.split(r'\.segment\s+"MISSIONBSS"', memory_asm, maxsplit=1)[1]
        memory_layout = memory_layout.split('.segment', 1)[0]
        memory_symbols, offset = {}, 0
        for name, length in re.findall(r'_(\w+):\s+\.res\s+(\d+)', memory_layout):
            size = int(length)
            memory_symbols[name] = dict(offset=offset, size=size)
            offset += size
        assert memory_symbols['identities']['size'] == 100
        for name in OUTPUTS:
            shutil.copyfile(work/name, destination/name)
        record = dict(schema='feldmarschall-ai-production-build-v1', defines=list(defines),
                      source_sha256=source_hashes, runtime_library_sha256=sha(library),
                      relocated_helpers=helper_proof, checked_references=references,
                      checked_main_runtime_members=sorted(linked), free_bytes=free,
                      belief_bss_symbols=belief_symbols,
                      memory_bss_symbols=memory_symbols,
                      output_sha256={name: sha(destination/name) for name in OUTPUTS},
                      commands=commands)
        (destination/'ai-build.json').write_text(json.dumps(record, indent=2)+'\n')
        return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'src')
    parser.add_argument('--output', type=Path, default=ROOT/'build/ai-release-candidate')
    parser.add_argument('--library', type=Path, default=Path('/usr/share/cc65/lib/cx16.lib'))
    args = parser.parse_args()
    result = build(args.source, args.output, args.library)
    print(json.dumps(dict(output=str(args.output), free_bytes=result['free_bytes']), indent=2))
