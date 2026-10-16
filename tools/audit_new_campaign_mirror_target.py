"""Frozen mirror deployment only: production links and real bank-24 gateway.

No policy, original source, prior target receipts or production outputs mutate.
"""
import ctypes
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT,get_policy
from audit_new_campaign_open_reserve_target import FLAGS
from feldmarschall import GLYPHS,setup_squares,valid_setup
from tournament_store import mirror_setup

OUT=ROOT/'docs/ai-honest-campaign-2026-10-16/research/mirror-deployment/target'
MODES={'fortress':None,'fixed-mirror':'AI_FORTRESS_MIRROR_ONLY','ticket-mixture':'AI_FORTRESS_MIRROR_MIX'}
POLICIES=('student-fortress-mirror-template-v1-normal','student-fortress-mirror-mixture-template-v1-normal')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def accepted(seed):
 from test_ai_selection import next_random
 draw=next_random(seed)
 while draw>65530:draw=next_random(draw)
 return draw,(draw-1)%10

def fixture(trees,tmp,base):
 from distribute import runtime_files
 from test_colors import start
 from test_ai_selection import next_random
 from test_ai_selection_banked import call
 tickets={};rejected=[]
 for seed in range(1,65536):
  draw=next_random(seed)
  if draw>65530:rejected.append(seed)
  else:tickets.setdefault((draw-1)%10,seed)
 assert len(tickets)==10 and len(rejected)==5
 seeds=[tickets[t]for t in range(10)]+rejected;records=[]
 for name,tree in trees.items():
  library=tmp/(name+'.so');sources=[str(tree/'core'/(part+'.c'))for part in('pieces','board','rules','random','ai_level','setup','ai_deploy')]
  flags=['AI_TEST','AI_DEPLOY_FORTRESS_ONLY']+([MODES[name]]if MODES[name]else[])
  subprocess.run(['gcc','-shared','-fPIC','-O2','-Wno-unknown-pragmas','-I'+str(tree/'core'),*['-D'+f for f in flags],*sources,'-o',str(library)],check=True,capture_output=True)
  lib=ctypes.CDLL(str(library));cells=(ctypes.c_uint8*100).in_dll(lib,'board');level=ctypes.c_uint8.in_dll(lib,'ai_difficulty');rules=ctypes.c_uint8.in_dll(lib,'game_rules');lib.random_next.restype=ctypes.c_uint16
  symtext=(tree/'FELDMARS.sym').read_text()
  def symbol(function):return int(re.search(r'al ([0-9A-F]+) \._'+function+r'\b',symtext).group(1),16)
  software_sp=int(re.search(r'al ([0-9A-F]+) \.sp\b',symtext).group(1),16)
  himem=int(re.search(r'al ([0-9A-F]+) \.__HIMEM__\b',symtext).group(1),16);stacksize=int(re.search(r'al ([0-9A-F]+) \.__STACKSIZE__\b',symtext).group(1),16);assert stacksize==1024
  runtime=tmp/(name+'-runtime');runtime.mkdir()
  for filename in runtime_files():
   source=tree/filename if(tree/filename).exists()else ROOT/'src'/filename
   shutil.copyfile(source,runtime/filename)
  session=start(runtime)
  try:
   session.emu.request('set_registers',ram_bank=22)
   for difficulty in(1,0,2):
    for army in(0,1):
     for seed in seeds:
      level.value=difficulty;rules.value=0;lib.board_clear();lib.random_seed(seed);lib.setup_ai(army);expected=bytes(cells);expected_rng=lib.random_next()
      session.emu.write_memory(symbol('ai_difficulty'),bytes([difficulty]));session.emu.write_memory(symbol('game_rules'),b'\x00')
      call(session,'board_clear',0,symbol);call(session,'random_seed',seed,symbol)
      canary=bytes((17*i+name.count('r'))&255 for i in range(16));session.emu.write_memory(himem-stacksize,canary)
      before=session.emu.request('status');sp_before=bytes(session.emu.read_memory(software_sp,2));call(session,'setup_ai',army,symbol);after=session.emu.request('status');sp_after=bytes(session.emu.read_memory(software_sp,2))
      actual=bytes(session.emu.read_memory(symbol('board'),100));assert actual==expected,(name,difficulty,army,seed,'board')
      assert after['sp']==before['sp']and after['ram_bank']==before['ram_bank']==22,(name,difficulty,army,seed,'hardware stack/bank')
      assert sp_after==sp_before,(name,difficulty,army,seed,'software stack balance')
      assert bytes(session.emu.read_memory(himem-stacksize,16))==canary,(name,difficulty,army,seed,'stack bottom canary')
      canonical=''.join(GLYPHS[actual[s]&15]for s in setup_squares(army));native_canonical=''.join(GLYPHS[expected[s]&15]for s in setup_squares(army));assert valid_setup(canonical)and canonical==native_canonical
      reflected=mirror_setup(canonical);assert mirror_setup(reflected)==canonical
      draw,ticket=accepted(seed);want_reflection=difficulty==1 and(name=='fixed-mirror'or(name=='ticket-mixture'and ticket>=5))
      if difficulty in(1,2):
       assert canonical==(mirror_setup(base)if want_reflection else base),(name,difficulty,army,seed,'independent formation oracle')
       assert reflected==(base if want_reflection else mirror_setup(base)),(name,difficulty,army,seed,'reflected serialization')
      call(session,'random_next',0,symbol);state=session.emu.request('status');actual_rng=state['a']|(state['x']<<8);assert actual_rng==expected_rng
      records.append(dict(build=name,difficulty=difficulty,army=army,seed=seed,first_draw_rejected=seed in rejected,accepted_ticket=ticket if difficulty!=0 else None,
       setup_cycles=after['cycles']-before['cycles'],canonical=canonical,reflected=reflected,board_sha256=hashlib.sha256(actual).hexdigest(),next_rng=actual_rng,
       board_and_next_rng_match_native=True,independent_canonical_and_reflected_serialization=True,caller_bank_before=before['ram_bank'],caller_bank_after=after['ram_bank'],hardware_stack_before=before['sp'],hardware_stack_after=after['sp'],software_stack_before=int.from_bytes(sp_before,'little'),software_stack_after=int.from_bytes(sp_after,'little'),software_stack_bottom_canary_untouched=True))
  finally:session.emu.close()
 for control in(r for r in records if r['build']=='fortress'):
  for mode in('fixed-mirror','ticket-mixture'):
   row=next(r for r in records if r['build']==mode and all(r[k]==control[k]for k in('difficulty','army','seed')))
   assert row['next_rng']==control['next_rng']
   if control['difficulty']!=1:assert row['board_sha256']==control['board_sha256']
 assert len(records)==270
 return dict(passed=True,real_banked_setup_calls=len(records),first_draw_rejection_seeds=rejected,ticket_representative_seeds=tickets,records=records,
  scope='Real production setup gateway, bank24 payload, software/hardware stack balance and bottom-canary integrity, board serialization and RNG only. No full AI turn/source-template inference qualification.',
  timing='Emulator CPU-cycle deltas include gateway and possible interrupts, not hardware latency or isolated instruction counts.',stack_limit='A 16-byte bottom canary does not measure complete stack high-water usage.')

def main():
 original=ROOT/'src';before={str(p.relative_to(original)):sha(p)for p in original.rglob('*')if p.is_file()};OUT.mkdir(parents=True,exist_ok=True)
 specs=[get_policy(p)for p in POLICIES];deployments=[]
 for spec in specs:
  archive=ROOT/spec['archive'];assert sha(archive)==spec['source_sha256']
  with zipfile.ZipFile(archive)as bundle:
   deployments.append(bundle.read('tools/new_campaign_mirror_deploy.c'));assert bundle.read('src/core/ai_deploy.c')==(original/'core/ai_deploy.c').read_bytes()
 assert deployments[0]==deployments[1];frozen=deployments[0];assert hashlib.sha256(frozen).hexdigest()==sha(ROOT/'tools/new_campaign_mirror_deploy.c')
 arrays=re.findall(r'\{([\d,]+)\}',(original/'core/ai_deploy.c').read_text());base=''.join(GLYPHS[int(n)]for n in next(a for a in arrays if len(a.split(','))==40).split(','))
 records={};saved=[];trees={}
 with tempfile.TemporaryDirectory(prefix='mirror-production-target-')as text:
  tmp=Path(text)
  for name,macro in MODES.items():
   tree=tmp/name;shutil.copytree(original,tree,ignore=shutil.ignore_patterns('*.o','*.PRG','*.BIN','*.map','*.sym'));trees[name]=tree
   if macro:(tree/'core/ai_deploy.c').write_bytes(frozen)
   flags=FLAGS+([macro]if macro else[])
   inputs=sorted(p.relative_to(tree).as_posix()for p in tree.glob('*.c'))
   for directory in('core','ui','scenes'):inputs+=sorted(p.relative_to(tree).as_posix()for p in(tree/directory).glob('*.c'))
   assembly=[]
   for directory in('ui','scenes'):assembly+=sorted(p.relative_to(tree).as_posix()for p in(tree/directory).glob('*.s'))
   command=['cl65','-O','-t','cx16','-I','.','-I','core','-I','ui','-I','scenes',*['-D'+flag for flag in flags],'--asm-define','AI_MEMORY','-Wl','-D,__STACKSIZE__=0x0400','-C','feldmarschall.cfg','-o','FELDMARS.PRG','-m','FELDMARS.map','-Ln','FELDMARS.sym',*inputs,*assembly,'vendor/zsmkit.lib']
   result=subprocess.run(command,cwd=tree,text=True,capture_output=True);(OUT/(name+'-full-link.log')).write_text('command: '+json.dumps(command)+'\nreturncode: '+str(result.returncode)+'\nstdout:\n'+result.stdout+'\nstderr:\n'+result.stderr)
   record=dict(command=command,returncode=result.returncode,flags=flags,stdout=result.stdout,stderr=result.stderr,copied_inputs_sha256={p:sha(tree/p)for p in inputs+assembly+['feldmarschall.cfg','vendor/zsmkit.lib']},header_sha256={str(p.relative_to(tree)):sha(p)for p in tree.rglob('*.h')})
   if result.returncode==0:
    table=(tree/'FELDMARS.map').read_text().split('Segment list:',1)[1].split('Exports list',1)[0];segments={seg:dict(start=int(start,16),end=int(end,16),bytes=int(size,16))for seg,start,end,size in re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})',table,re.M)}
    groups={'PLAY':['PLAYCODE','PLAYRODATA'],'AI':['AICODE','AIRODATA','AIBSS'],'MISSION':['MISSIONCODE','MISSIONRODATA','MISSIONBSS']}
    banks={bank:dict(capacity_bytes=8192,used_bytes=sum(segments.get(s,{}).get('bytes',0)for s in names),free_bytes=8192-sum(segments.get(s,{}).get('bytes',0)for s in names))for bank,names in groups.items()};assert all(r['free_bytes']>=0 for r in banks.values())
    record.update(segments=segments,banks=banks,outputs={})
    for filename in('FELDMARS.PRG','PLAY.BIN','AI.BIN','MISSION.BIN','FELDMARS.map','FELDMARS.sym'):
     path=tree/filename;record['outputs'][filename]=dict(bytes=path.stat().st_size,sha256=sha(path));saved.append((name+'/'+filename,path.read_bytes()))
   records[name]=record
  assert all(r['returncode']==0 for r in records.values()),'A copied target link failed; preserved per-mode logs'
  # Ordinary production control must be exactly the already-qualified basis.
  prior=json.loads((ROOT/'docs/ai-honest-campaign-2026-10-16/research/open-reserve/component-target.json').read_text())['builds']['fortress']
  assert records['fortress']['flags']==prior['flags']
  assert records['fortress']['copied_inputs_sha256']==prior['copied_inputs_sha256']and records['fortress']['header_sha256']==prior['header_sha256']
  assert records['fortress']['outputs']==prior['outputs']
  banked=fixture(trees,tmp,base)
  assert before=={str(p.relative_to(original)):sha(p)for p in original.rglob('*')if p.is_file()},'Workspace source/runtime files changed'
  report=dict(passed=True,scope='Ordinary production deployment component only. Excludes desktop template adapter, inference banks, full-turn gameplay and hardware qualification.',
   policies={s['id']:dict(archive=s['archive'],source_sha256=s['source_sha256'])for s in specs},source_sha256=hashlib.sha256(frozen).hexdigest(),script_sha256=sha(Path(__file__)),control_matches_prior_production_inputs_headers_outputs=True,
   software_stack_reserved_bytes=1024,workspace_source_and_runtime_files_unchanged=True,toolchain=subprocess.run(['cl65','--version'],text=True,capture_output=True).stderr.strip(),builds=records,banked_fixture=banked,
   limitations=['No production installation or artwork regeneration.','Three PRG and RAM-bank binaries; not system ROM images.','Software/hardware stack balance and a bottom canary are tested, not full stack high-water/hardware timing.','A deployment component link does not qualify the full template-inference policy on CX16.'])
  (OUT/'component-target.json').write_text(json.dumps(report,indent=2)+'\n')
  with zipfile.ZipFile(OUT/'component-target-build.zip','w',zipfile.ZIP_DEFLATED)as bundle:
   for name,data in saved:bundle.writestr(name,data)
   bundle.writestr('inputs/mirror-deployment.c',frozen)
   # Preserve the common build source bytes once; candidate trees differ only in ai_deploy.c/macros.
   for path in sorted(trees['fortress'].rglob('*')):
    if path.is_file()and path.suffix in('.c','.h','.s','.inc','.cfg','.lib'):bundle.writestr('inputs/common/'+str(path.relative_to(trees['fortress'])),path.read_bytes())
  manifest={p.name:dict(sha256=sha(p),bytes=p.stat().st_size)for p in sorted(OUT.iterdir())if p.is_file()and p.name!='manifest.json'};(OUT/'manifest.json').write_text(json.dumps(dict(files=manifest),indent=2)+'\n')
  print(json.dumps(dict(passed=True,real_banked_setup_calls=banked['real_banked_setup_calls'],first_draw_rejection_seeds=banked['first_draw_rejection_seeds'],builds={n:dict(banks=r['banks'],outputs=r['outputs'])for n,r in records.items()}),indent=2))

if __name__=='__main__':main()
