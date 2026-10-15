"""Preserve duplicate benchmark runtimes once in a lossless standard archive."""
from pathlib import Path
import hashlib
import json
import lzma
import tarfile

base=Path(__file__).resolve().parents[1]
files=sorted(base.glob('benchmark/*.fmtour'))+sorted(base.glob('pooled-benchmark/*.fmtour'))+[base/'failed-stress-v2.fmtour']
expected={p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
archive=base/'benchmark-evidence.tar.xz'
filters=[dict(id=lzma.FILTER_LZMA2,dict_size=32*1024*1024,mode=lzma.MODE_FAST,nice_len=32,mf=lzma.MF_HC3)]
with archive.open('xb') as output,lzma.LZMAFile(output,'w',filters=filters) as compressed,tarfile.open(fileobj=compressed,mode='w|') as bundle:
    for p in files:bundle.add(p,arcname=p.relative_to(base).as_posix(),recursive=False)
with tarfile.open(archive,'r:xz') as bundle:
    for name,sha in expected.items():assert hashlib.sha256(bundle.extractfile(name).read()).hexdigest()==sha
manifest=dict(archive=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),bytes=archive.stat().st_size,uncompressed_fmtour_bytes=sum(p.stat().st_size for p in files),files=expected,scope='Every original benchmark and failed-run SQLite file is preserved byte-for-byte. The direct reference.fmtour remains outside this archive for immediate Qt review.')
(base/'benchmark-archive.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Lossless verification above precedes removing duplicate loose copies.
for p in files:p.unlink()
print(json.dumps(manifest,indent=2))
