"""Run existing full UI lifecycle checks against an isolated release runtime.

The emulator/ROM paths stay those of the real checkout. Only the tests' source
and output views are redirected, so production binaries are never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import distribute
import test_ai_levels
import test_flow

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT/'build/ai-release-candidate')
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    names = list(dict.fromkeys(distribute.runtime_files()+['BELIEF.BIN']))
    before = {name: hashlib.sha256((runtime/name).read_bytes()).hexdigest() for name in names}
    with tempfile.TemporaryDirectory(prefix='feldmarschall-release-lifecycle-') as tmp:
        view = Path(tmp)
        (view/'src').mkdir()
        (view/'build/test-shots').mkdir(parents=True)
        for path in (ROOT/'src').iterdir():
            (view/'src'/path.name).symlink_to(path.resolve(), target_is_directory=path.is_dir())
        for path in runtime.iterdir():
            if path.is_file():
                target = view/'src'/path.name
                target.unlink(missing_ok=True)
                target.symlink_to(path)
        # Imported functions retain their defining modules' globals. The emulator
        # start function therefore still resolves the actual emulator and ROM.
        test_flow.ROOT = test_ai_levels.ROOT = view
        test_flow.runtime_files = test_ai_levels.runtime_files = lambda: names
        test_flow.main()
        test_ai_levels.main()
    assert before == {name: hashlib.sha256((runtime/name).read_bytes()).hexdigest() for name in names}
    (runtime/'lifecycle.json').write_text(json.dumps(dict(
        schema='feldmarschall-release-lifecycle-v1', passed=True,
        runtime_sha256=before,
        checks=['setup management and persistent restart', 'save/resume board equality',
                'new game and rematch', 'all difficulty save/load encodings',
                'legacy save defaults to Normal', 'load clears warm public history',
                'real banked Hard AI conceals enemy ranks', 'artwork and palette preserved']), indent=2)+'\n')


if __name__ == '__main__':
    main()
