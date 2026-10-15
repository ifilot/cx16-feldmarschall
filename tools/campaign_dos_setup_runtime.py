"""Freeze, execute and audit private original-DOS deployment generation.

The tournament/referee owns this helper. Only private seed and difficulty cross
its JSON worker boundary; neither enemy setup nor an honest bot is an input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import select
import subprocess
import sys
import tempfile
import zipfile
import zlib

from ai_registry import ROOT, build_policy, receives_opponent_setup
from feldmarschall import valid_setup
from tournament_store import Tournament, mirror_setup

ASSET_ARCHIVE = ROOT/'docs/ai-honest-campaign-2026-10-15/research/dos-deployment-original-v1/generator-assets.zip'
ASSET_SHA256 = '258ca0750bdabff2b4e052ab78c6c5ed28db3140daa8b956366720eef63d1a0c'
PREFIX = 'setup/original-dos-runtime/'
RECORDS_ARTIFACT = 'setup/original-dos-records-v1.json'
WORKER = '''import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
import unicorn
if not Path(unicorn.__file__).resolve().is_relative_to(root/'unicorn'):
    raise RuntimeError('unfrozen Unicorn import')
from generator import generate_setup
print(json.dumps({'ready':True,'unicorn_version':unicorn.__version__}),flush=True)
for line in sys.stdin:
    try:
        request=json.loads(line)
        if not isinstance(request,dict) or set(request)!={'seed','level'}:
            raise ValueError('request accepts only private seed and level')
        setup,audit=generate_setup(root/'assets',request['seed'],request['level'])
        result={'setup':setup,'audit':audit}
    except Exception as error:
        result={'error':type(error).__name__+': '+str(error)}
    print(json.dumps(result,sort_keys=True),flush=True)
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _relative(name):
    if (not isinstance(name,str) or not name or '\\' in name or ':' in name or
            PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts):
        raise ValueError('unsafe frozen runtime path')
    return Path(*PurePosixPath(name).parts)


def _extract_assets(bundle):
    archive=bundle/'generator-assets.zip'
    if sha(archive.read_bytes())!=ASSET_SHA256:
        raise ValueError('frozen original deployment archive integrity failure')
    target=bundle/'assets';target.mkdir()
    with zipfile.ZipFile(archive) as source:
        names=source.namelist()
        if len(names)!=len(set(names)) or sum(row.file_size for row in source.infolist())>4*1024*1024:
            raise ValueError('invalid original asset archive')
        for row in source.infolist():
            path=_relative(row.filename)
            if row.is_dir() or (row.external_attr>>16)&0o170000==0o120000:
                raise ValueError('nonregular original asset archive entry')
            destination=target/path;destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(source.read(row))


class _Worker:
    def __init__(self,bundle):
        self.bundle=Path(bundle)
        _extract_assets(self.bundle)
        env=dict(os.environ)
        for key in ('LD_PRELOAD','LD_LIBRARY_PATH','LIBUNICORN_PATH'):
            env.pop(key,None)
        env['LIBUNICORN_PATH']=str(self.bundle/'unicorn/lib')
        self.process=subprocess.Popen([sys.executable,'-I','-B',str(self.bundle/'worker.py')],
            cwd=self.bundle,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,bufsize=1)
        try:
            ready=self._read()
            if ready!={'ready':True,'unicorn_version':'2.1.4'}:
                raise ValueError('frozen deployment worker failed readiness')
        except BaseException:
            self.close();raise

    def _read(self):
        if not select.select([self.process.stdout],[],[],15)[0]:
            raise RuntimeError('frozen deployment worker timed out')
        line=self.process.stdout.readline()
        if not line:
            raise RuntimeError('frozen deployment worker stopped: '+self.process.stderr.read())
        return json.loads(line)

    def generate(self,seed,level=3):
        if type(seed) is not int or not 0<=seed<=0xffffffff or type(level) is not int or not 1<=level<=5:
            raise ValueError('private unsigned32 seed and difficulty1..5 required')
        self.process.stdin.write(json.dumps(dict(seed=seed,level=level))+'\n');self.process.stdin.flush()
        response=self._read()
        if 'error' in response:
            raise ValueError('original deployment generation failed: '+response['error'])
        if set(response)!={'setup','audit'} or not valid_setup(response['setup']):
            raise ValueError('invalid original deployment worker response')
        return response['setup'],response['audit']

    def close(self):
        if not hasattr(self,'process'):return
        process=self.process
        try:
            if process.stdin and not process.stdin.closed:process.stdin.close()
            process.wait(timeout=5)
        except (OSError,subprocess.TimeoutExpired):
            process.kill();process.wait()
        finally:
            for stream in (process.stdin,process.stdout,process.stderr):
                if stream and not stream.closed:stream.close()


class FrozenDOSSetups:
    """Context manager freezing every worker source, emulator file and asset."""
    def __init__(self,tournament,working):
        self.tournament=tournament;self.bundle=Path(working)/'original-dos-generator'
        self.worker=None

    def __enter__(self):
        self.bundle.mkdir(parents=True,exist_ok=False,mode=0o700)
        executable,receipt=build_policy('msdos-1990-v2-normal')
        source_files={
            'generator.py':ROOT/'tools/campaign_dos_deployment.py',
            'msdos1990.py':ROOT/'tools/msdos1990.py',
            'feldmarschall.py':ROOT/'tools/feldmarschall.py',
            'runtime_helper.py':Path(__file__).resolve(),
            'generator-assets.zip':ASSET_ARCHIVE}
        for name,expected in receipt['runtime_sha256'].items():
            if name.startswith('unicorn/'):
                path=executable.parent/name
                if sha(path.read_bytes())!=expected:raise ValueError('frozen Unicorn runtime changed')
                source_files[name]=path
        files={}
        for name,path in source_files.items():
            data=path.read_bytes();destination=self.bundle/_relative(name)
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
            files[name]=self.tournament.artifact(PREFIX+name,data)
        data=WORKER.encode();(self.bundle/'worker.py').write_bytes(data)
        files['worker.py']=self.tournament.artifact(PREFIX+'worker.py',data)
        descriptor=dict(schema='original-dos-setup-runtime-v1',artifact_prefix=PREFIX,files=files,
            asset_zip_sha256=ASSET_SHA256,emulator_policy='msdos-1990-v2-normal',
            emulator_recipe_sha256=receipt['recipe_sha256'],python_version=sys.version)
        # Commit provenance before the worker imports or executes any generator.
        self.tournament.set_metadata(dict(original_dos_setup_runtime=descriptor))
        self.worker=_Worker(self.bundle)
        return self

    def generate(self,private_seed,level=3):
        if self.worker is None:raise ValueError('enter frozen setup context before generating')
        return self.worker.generate(private_seed,level)

    def __exit__(self,kind,value,tb):
        if self.worker is not None:self.worker.close()


def _artifact(tournament,digest):
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid frozen original-deployment artifact digest')
    row=tournament.db.execute('SELECT data FROM artifacts WHERE sha256=?',(digest,)).fetchone()
    if row is None:raise ValueError('missing frozen original-deployment artifact')
    try:data=zlib.decompress(row['data'])
    except zlib.error as error:raise ValueError('corrupt frozen original-deployment artifact') from error
    if sha(data)!=digest:raise ValueError('frozen original-deployment artifact hash mismatch')
    return data


def audit_original_setups(path):
    """Rerun only embedded sources/assets, then bind records to saved armies."""
    with Tournament(path) as tournament,tempfile.TemporaryDirectory(prefix='audit-original-dos-') as temporary:
        metadata=tournament.metadata();descriptor=metadata.get('original_dos_setup_runtime')
        if metadata.get('rules')!='classic':raise ValueError('original deployment audit supports Classic only')
        if (not isinstance(descriptor,dict) or descriptor.get('schema')!='original-dos-setup-runtime-v1' or
                descriptor.get('artifact_prefix')!=PREFIX or descriptor.get('asset_zip_sha256')!=ASSET_SHA256):
            raise ValueError('missing/invalid frozen original-deployment runtime')
        files=descriptor.get('files')
        required={'generator.py','msdos1990.py','feldmarschall.py','worker.py','runtime_helper.py','generator-assets.zip',
                  'unicorn/__init__.py','unicorn/lib/libunicorn.so.2'}
        if not isinstance(files,dict) or not required<=set(files):raise ValueError('incomplete frozen deployment runtime')
        if metadata.get('original_dos_setup_records_artifact')!=RECORDS_ARTIFACT:
            raise ValueError('missing original-deployment setup records')
        records=json.loads(_artifact(tournament,metadata.get('original_dos_setup_records_sha256')))
        if (not isinstance(records,dict) or records.get('schema')!='original-dos-setups-v1' or
                not isinstance(records.get('records'),list)):
            raise ValueError('invalid original-deployment setup records schema')
        games=[dict(row) for row in tournament.db.execute(
            'SELECT pair_id,family,red,blue,red_setup,blue_setup FROM games ORDER BY id')]
        bypair={}
        for game in games:bypair.setdefault(game['pair_id'],[]).append(game)
        mode=metadata.get('setup_mode','referee')
        if mode not in ('referee','policy-owned','policy-owned-rotated-v1'):raise ValueError('unknown setup mode')
        opponent=None
        if mode in ('policy-owned','policy-owned-rotated-v1'):
            participants=metadata.get('participants',[])
            if len(participants)!=2 or metadata.get('setup_owner')!=participants[0]['policy']['id']:
                raise ValueError('invalid policy-owned original-deployment ownership')
            opponent=participants[1]['policy']['id']
            policy=participants[1]['policy']
            context=metadata.get('original_dos_setup_move_context')
            if policy.get('driver')=='msdos1990':
                if context not in (None,'original-dos-opponent'):
                    raise ValueError('DOS move driver context mismatch')
            elif (context!='honest-opponent-control-v1' or receives_opponent_setup(policy) or
                  'AI_DIAGNOSTIC_TRUTH' in policy.get('defines',[]) or
                  '--diagnostic-truth' in policy.get('driver_args',[])):
                raise ValueError('non-DOS moves require an explicit honest opponent control')
        bundle=Path(temporary)/'bundle';bundle.mkdir()
        for name,digest in files.items():
            destination=bundle/_relative(name);destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(_artifact(tournament,digest))
        worker=_Worker(bundle);seen=set();matched_games=0;regenerated=0
        try:
            for record in records['records']:
                if (not isinstance(record,dict) or type(record.get('pair_id')) is not int or record['pair_id']<1 or
                        record.get('slot') not in ('A','B') or type(record.get('used_in_games')) is not bool or
                        not isinstance(record.get('setup'),str) or not valid_setup(record['setup']) or
                        not isinstance(record.get('audit'),dict)):
                    raise ValueError('invalid original-deployment record')
                key=record['pair_id'],record['slot']
                if key in seen:raise ValueError('duplicate original-deployment pair/slot')
                seen.add(key)
                generated,audit=worker.generate(record.get('private_seed'),record['audit'].get('level'))
                if generated!=record['setup'] or audit!=record['audit']:
                    raise ValueError('frozen original-deployment regeneration mismatch')
                regenerated+=1
                rows=bypair.get(record['pair_id'],[])
                if metadata['status']=='complete' and len(rows)!=2:
                    raise ValueError('original-deployment record lacks completed paired games')
                if not record['used_in_games']:
                    if mode not in ('policy-owned','policy-owned-rotated-v1') or record['slot']!='A':
                        raise ValueError('only overwritten policy-owned slotA may be unused')
                    continue
                if mode in ('policy-owned','policy-owned-rotated-v1') and record['slot']!='B':
                    raise ValueError('policy-owned original DOS army must use slotB')
                for game in rows:
                    if mode=='referee':side='red' if record['slot']=='A' else 'blue'
                    else:
                        if (game['red']==opponent)==(game['blue']==opponent):raise ValueError('DOS opponent identity mismatch')
                        side='red' if game['red']==opponent else 'blue'
                    applied = mirror_setup(generated) if mode=='policy-owned-rotated-v1' and side=='red' else generated
                    if game[side+'_setup']!=applied:
                        raise ValueError('game army differs from original-deployment record')
                    matched_games+=1
            required_slots=('A','B') if mode=='referee' else ('B',)
            for pair,rows in bypair.items():
                if any(game['family']=='original-dos' for game in rows):
                    for slot in required_slots:
                        key=pair,slot
                        if key not in seen:raise ValueError('original-DOS game missing setup slot record')
                        record=next(r for r in records['records'] if (r['pair_id'],r['slot'])==key)
                        if not record['used_in_games']:raise ValueError('original-DOS game has unused required record')
        finally:worker.close()
        return dict(passed=True,regenerated_records=regenerated,matched_game_armies=matched_games,
                    runtime_files=len(files),setup_mode=mode,
                    source='Only frozen embedded generator/emulator/asset bytes executed; all private seeds and audits reproduced.',
                    move_rng_boundary='Existing move adapter reseeds independently; deployment post-RNG is preserved in records.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fmtour',type=Path)
    args=parser.parse_args();print(json.dumps(audit_original_setups(args.fmtour),indent=2))


if __name__=='__main__':main()
