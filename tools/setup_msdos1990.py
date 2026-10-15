"""Import verified 1990 Stratego AI images and prepare a pinned headless emulator."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 'unpacked/STRATEGO.EXE':'b0812df36607c46a7b78baecebcf5cf85b6e18a4cfb0fb44a61d589102ae7763',
 'extracted/resident-image.bin':'cd8c40e2f305f2bd3656b35aa31e7baa55535db19b745e307d98e43d7ca1904f',
 'extracted/overlays/ovl5.cod':'373cbdcade64489c1e53d618eea0d6f411a0b51e70711098592fcb19ce080510',
 'extracted/overlays/ovl5.rel':'2022c37dd471ec7e7ce1c5d38fec3919f11972365ae0272aef18655ad1192362'}
VERSION='2.1.4'

def prepare(source, package=None):
    data={}
    for name,expected in EXPECTED.items():
        contents=(source/name).read_bytes()
        if hashlib.sha256(contents).hexdigest()!=expected:raise ValueError('Unsupported or changed original input: '+name)
        data[name]=contents
    assets=ROOT/'ai/msdos1990';assets.mkdir(parents=True,exist_ok=True)
    images={'mz-header.bin':data['unpacked/STRATEGO.EXE'][:1024],
            'resident-image.bin':data['extracted/resident-image.bin'],
            'ovl5.cod':data['extracted/overlays/ovl5.cod'],'ovl5.rel':data['extracted/overlays/ovl5.rel']}
    for name,contents in images.items():
        path=assets/name
        if path.exists() and path.read_bytes()!=contents:raise ValueError('Refusing to replace imported image: '+name)
        path.write_bytes(contents)
    manifest=dict(schema=1,game='Stratego, MS-DOS 1990',source_repository='https://github.com/ifilot/stratego-decompilation',source_commit='306e3cb757137f3c28d1224ee3d2c4570f412509',original_sha256=EXPECTED,images={name:dict(size=len(contents),sha256=hashlib.sha256(contents).hexdigest()) for name,contents in images.items()},scope='Unmodified resident image and overlay 5 plus original MZ relocation header. Graphics, audio, UI and DOS startup are omitted. Host supplies a Classic referee and call boundaries; this is original AI execution, not complete DOS operating-system emulation.',emulator=dict(package='unicorn',version=VERSION))
    (assets/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    deps=ROOT/'build/msdos1990/deps';deps.mkdir(parents=True,exist_ok=True)
    if package:
        target=deps/'unicorn'
        if target.exists():shutil.rmtree(target)
        shutil.copytree(package,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.a','include'))
    elif not (deps/'unicorn').is_dir():
        subprocess.run([sys.executable,'-m','pip','install','--no-cache-dir','--target',str(deps),'unicorn=='+VERSION],check=True)
    subprocess.run([sys.executable,'-c',f'import sys;sys.path.insert(0,{str(deps)!r});import unicorn;assert unicorn.__version__=={VERSION!r};print("Unicorn",unicorn.__version__)'],check=True)
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True,help='Local stratego-decompilation checkout')
    parser.add_argument('--unicorn-package',type=Path,help='Use an already installed unicorn package directory')
    args=parser.parse_args();print(json.dumps(prepare(args.source,args.unicorn_package),indent=2))
