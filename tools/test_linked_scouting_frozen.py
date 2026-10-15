"""Compile the cooperation/fairness suite against the candidate's frozen sources."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT, get_policy
from linked_scouting_cycle import BASE


def digest(data):return hashlib.sha256(data).hexdigest()


def check():
    destination=BASE/'checks/frozen-tactics.zip'
    if destination.exists():raise FileExistsError(f'Retained test evidence already exists: {destination}')
    policy=get_policy('linked-scouting-v1-normal')
    archive=ROOT/policy['archive'];assert digest(archive.read_bytes())==policy['source_sha256']
    test_source=(ROOT/'tests/ai_test.c').read_bytes()
    with tempfile.TemporaryDirectory(prefix='linked-scouting-check-',dir=ROOT/'build') as directory:
        folder=Path(directory)
        with zipfile.ZipFile(archive) as bundle:bundle.extractall(folder)
        (folder/'tests/ai_test.c').write_bytes(test_source)
        compiler=shlex.split(os.environ.get('HOSTCC','gcc'))
        command=[*compiler,'-O2','-std=c99','-Wall','-Wno-unknown-pragmas','-DAI_TEST',
                 *['-D'+define for define in policy['defines']],'-Isrc/core','-o','test',
                 'tests/ai_test.c',*[source for source in policy['sources'] if source.startswith('src/core/')]]
        compiled=subprocess.run(command,cwd=folder,capture_output=True,text=True)
        log=' '.join(command)+'\n'+compiled.stdout+compiled.stderr
        compiled.check_returncode()
        executed=subprocess.run(['./test'],cwd=folder,capture_output=True,text=True)
        log+=executed.stdout+executed.stderr
        (BASE/'checks/frozen-tactics.log').write_text(log)
        executed.check_returncode()
        assert 'AI: passed;' in log and 'FAIL' not in log
        provenance=dict(policy=policy,command=command,compiler=subprocess.check_output([*compiler,'--version'],text=True).splitlines()[0],
            test_source_sha256=digest(test_source),test_binary_sha256=digest((folder/'test').read_bytes()),
            log_sha256=digest(log.encode()),scope='Current retained test source compiled against the immutable candidate core, with all candidate defines plus AI_TEST.')
        (BASE/'checks/frozen-tactics-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
            bundle.writestr('tests/ai_test.c',test_source)
            bundle.write(folder/'test','test')
            bundle.writestr('provenance.json',json.dumps(provenance,indent=2)+'\n')
            bundle.writestr('log.txt',log)
    print('Frozen candidate sources pass tactics, diagnostics and full hidden-information checks.')


if __name__=='__main__':check()
