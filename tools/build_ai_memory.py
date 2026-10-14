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
    args = parser.parse_args()
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
    if args.student: command += ['-D', 'AI_STUDENT']
    for directory in ('', 'core', 'ui', 'scenes'):
        command += ['-I', str(src/directory)]
    command += [str(path) for path in inputs+assembly] + [str(src/'vendor/zsmkit.lib')]
    subprocess.run(command, cwd=args.out, check=True)
    bridge = ['cl65', '-O', '-t', 'cx16', '-D', 'AI_MISSIONS', '-D', 'AI_MEMORY',
              '-I', str(src/'core'), '-o', 'BRIDGE.PRG', str(src/'bridge/bridge.c')]
    if args.student:
        # cl65 applies options as it encounters files, including bridge.c.
        bridge[1:1] = ['-D', 'AI_STUDENT']
    bridge += [str(path) for path in sorted((src/'core').glob('*.c')) if path.name not in ('store.c', 'presets.c')]
    subprocess.run(bridge, cwd=args.out, check=True)
    model_presence = {}
    if args.student:
        fields = re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(-?\d+)\s*\}',
                            (src/'core/ai_student_model.h').read_text())
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
    (args.out/'provenance.json').write_text(json.dumps({'game_command': command, 'bridge_command': bridge,
        'layout_command': layout,
        'model_presence': model_presence,
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in inputs+assembly+list(src.rglob('*.h'))},
        'flags': ['AI_MISSIONS', 'AI_MEMORY']+(['AI_STUDENT'] if args.student else []), 'files_sha256': files}, indent=2)+'\n')
    print(f'Memory prototype: {args.out}')


if __name__ == '__main__':
    main()
