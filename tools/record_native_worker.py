"""Record the native worker's exact executable, sources and build configuration."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    root, binary, compiler, commands = map(Path, sys.argv[1:])
    files = set((root / 'desktop').glob('*.cpp')) | set((root / 'desktop').glob('*.h'))
    files.update((root / 'assets/scripts').glob('*.py'))
    files.update(root / p for p in ('desktop/CMakeLists.txt', 'tools/build_desktop_assets.py',
                                    'tools/record_native_worker.py', 'assets/pieces/prussian.png',
                                    'assets/font/kakuro-ui.png'))
    hashes = {}
    archive = binary.parent / 'worker-sources.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(files):
            name = path.relative_to(root).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data)
            hashes[name] = sha(data)
    receipt = dict(schema=1, referee='classic-openmp-v1', executable_sha256=sha(binary.read_bytes()),
                   source_archive_sha256=sha(archive.read_bytes()), source_sha256=hashes,
                   compiler=subprocess.check_output([str(compiler), '--version'], text=True).splitlines()[0],
                   compile_commands=json.loads(commands.read_text()))
    (binary.parent / 'worker-build.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
