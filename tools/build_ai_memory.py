"""Build a disposable banked tracker prototype without replacing production binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import re
import struct

from feldmarschall import ROOT
from distribute import runtime_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--student', action='store_true', help='include the fitted integer capture policy')
    parser.add_argument('--student-model', type=Path, help='generated V2 model header; requires --student')
    parser.add_argument('--coop-guard', action='store_true', help='preserve the cooperation actor quiet priorities')
    args = parser.parse_args()
    if args.student_model and not args.student: parser.error('--student-model requires --student')
    if args.coop_guard and not args.student_model: parser.error('--coop-guard requires --student-model')
    if args.student_model: args.student_model = args.student_model.resolve()
    args.out = (args.out or ROOT/('build/ai-student-x16' if args.student else 'build/ai-memory-x16')).resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    src = ROOT/'src'
    inputs = sorted(src.glob('*.c'))
    for directory in ('core', 'ui', 'scenes'):
        inputs.extend(sorted((src/directory).glob('*.c')))
    assembly = [path for directory in ('ui', 'scenes') for path in sorted((src/directory).glob('*.s'))]
    command = ['cl65', '-O', '-t', 'cx16', '-D', 'BANKED_AI', '-D', 'AI_MISSIONS', '-D', 'AI_MEMORY',
               '--asm-define', 'AI_MEMORY', '-Wl', '-D,__STACKSIZE__=0x0400',
               '-C', str(src/'feldmarschall.cfg'), '-o', 'FELDMARS.PRG',
               '-m', 'FELDMARS.map', '-Ln', 'FELDMARS.sym']
    student_options = ['-D', 'AI_STUDENT'] if args.student else []
    if args.student_model:
        student_options += ['-D', 'AI_STUDENT_V2', '-I', str(args.student_model.parent)]
    if args.coop_guard: student_options += ['-D', 'AI_STUDENT_COOP_GUARD']
    command += student_options
    for directory in ('', 'core', 'ui', 'scenes'):
        command += ['-I', str(src/directory)]
    command += [str(path) for path in inputs+assembly] + [str(src/'vendor/zsmkit.lib')]
    (args.out/'build-attempt.json').write_text(json.dumps({'game_command':command,
        'student_model':str(args.student_model) if args.student_model else None,
        'model_sha256':hashlib.sha256(args.student_model.read_bytes()).hexdigest() if args.student_model else None}, indent=2)+'\n')
    subprocess.run(command, cwd=args.out, check=True)
    bridge = ['cl65', '-O', '-t', 'cx16', '-D', 'AI_MISSIONS', '-D', 'AI_MEMORY',
              '-I', str(src/'core'), '-o', 'BRIDGE.PRG', str(src/'bridge/bridge.c')]
    # cl65 applies options as it encounters files, including bridge.c.
    bridge[1:1] = student_options
    bridge += [str(path) for path in sorted((src/'core').glob('*.c')) if path.name not in ('store.c', 'presets.c')]
    subprocess.run(bridge, cwd=args.out, check=True)
    model_presence = {}
    if args.student:
        fields = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(-?\d+)\s*\}',
                            (args.student_model or src/'core/ai_student_model.h').read_text())
        if not fields: raise ValueError('no model nodes in generated header')
        data = b''.join(struct.pack('<BBBBh', *map(int, row)) for row in fields)
        for name in ('MISSION.BIN', 'BRIDGE.PRG'):
            offset = (args.out/name).read_bytes().find(data)
            if offset < 0: raise ValueError(f'{name}: fitted model is absent')
            model_presence[name] = {'offset': offset, 'bytes': len(data)}
    layout = ['cc65', '-O', '-t', 'cx16', '-D', 'AI_MISSIONS', '-D', 'AI_MEMORY', '-D', 'BANKED_AI',
              '-I', str(src/'core'), '-o', 'memory-layout.s', str(src/'core/ai_memory.c')]
    subprocess.run(layout, cwd=args.out, check=True)
    for name in runtime_files():
        if name not in ('FELDMARS.PRG', 'PLAY.BIN', 'AI.BIN', 'MISSION.BIN'):
            shutil.copy2(src/name, args.out/name)
    retained = set(runtime_files()) | {'BRIDGE.PRG', 'FELDMARS.map', 'FELDMARS.sym', 'memory-layout.s'}
    files = {name: hashlib.sha256((args.out/name).read_bytes()).hexdigest() for name in sorted(retained)}
    extra_sources = [args.student_model] if args.student_model else []
    (args.out/'provenance.json').write_text(json.dumps({'game_command': command, 'bridge_command': bridge,
        'layout_command': layout,
        'model_presence': model_presence,
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in inputs+assembly+list(src.rglob('*.h'))+extra_sources},
        'flags': ['AI_MISSIONS', 'AI_MEMORY']+(['AI_STUDENT'] if args.student else [])+
                 (['AI_STUDENT_V2'] if args.student_model else [])+
                 (['AI_STUDENT_COOP_GUARD'] if args.coop_guard else []), 'files_sha256': files}, indent=2)+'\n')
    print(f'Memory prototype: {args.out}')


if __name__ == '__main__':
    main()
