"""Package the candidate twice and boot the actual SD-card distribution."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import distribute
import test_dist
from feldmarschall import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,default=ROOT/'build/ai-release-candidate')
    args=parser.parse_args()
    runtime=args.runtime.resolve()
    output=ROOT/'build/ai-release-dist'
    distribute.main(runtime,output)
    archive=output/'FELDMARSCHALL.ZIP'
    first=archive.read_bytes()
    distribute.main(runtime,output)
    assert first==archive.read_bytes(), 'Distribution archive must be reproducible'
    assert (output/'FELDMARSCHALL/BELIEF.BIN').read_bytes()==(runtime/'BELIEF.BIN').read_bytes()
    symbols=(runtime/'FELDMARS.sym').read_text()
    ready=int(re.search(r'al ([0-9A-F]+) \._sound_ready\b',symbols).group(1),16)
    base=test_dist.X16Agent

    class Qualified(base):
        def close(self):
            try:
                assert bytes(self.read_memory(ready,1))==b'\x01', 'AI banks and audio must load from the distribution'
            finally:
                super().close()

    test_dist.X16Agent=Qualified
    test_dist.DIST=output/'FELDMARSCHALL'
    try:
        test_dist.main()
    except SystemExit as result:
        assert result.code==0
    (runtime/'packaging.json').write_text(json.dumps(dict(
        passed=True,autoboot=True,all_ai_banks_and_audio_loaded=True,
        artwork_and_palette=True,belief_bank_present=True,
        reproducible_zip=True,zip_sha256=hashlib.sha256(first).hexdigest()),indent=2)+'\n')


if __name__ == '__main__':
    main()
