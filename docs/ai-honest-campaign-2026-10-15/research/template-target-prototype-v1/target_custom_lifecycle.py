"""Actual target custom-position resume gateway rejects fabricated origins."""
from pathlib import Path
import tempfile,shutil,re,json
from test_colors import start,choose
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
runtime=Path('/tmp/template-target-runtime-signed')
symbols=(runtime/'FELDMARS.sym').read_text()
def sym(n):return int(re.search(r'al ([0-9A-F]+) \._'+n+r'\b',symbols)[1],16)
with tempfile.TemporaryDirectory(prefix='template-custom-lifecycle-') as t:
 for p in runtime.iterdir():
  if p.is_file():shutil.copy2(p,Path(t)/p.name)
 session=start(Path(t))
 try:
  for key in 'DEV':choose(session,key)
  session.emu.request('breakpoint',address=sym('ai_template_forget'))
  choose(session,'1')
  before=session.emu.request('status');assert before['pc']==sym('ai_template_forget')
  assert before['ram_bank']==22
  session.emu.request('breakpoint',action='remove',address=sym('ai_template_forget'))
  session.emu.request('breakpoint',address=sym('ai_move'))
  assert session.emu.advance(600)['reason']=='breakpoint'
  session.emu.request('breakpoint',action='remove',address=sym('ai_move'))
  session.emu.request('breakpoint',address=sym('ai_move')+6)
  assert session.emu.advance(600)['reason']=='breakpoint'
  status=session.emu.read_memory(sym('ai_template_status'),1)[0]
  valid=session.emu.read_memory(sym('ai_template_valid'),1)[0]
  assert valid==0 and status==1,(valid,status)
  record=dict(success=True,real_developer_custom_position=True,shared_load_resume_path='play_resume after begin()',entry_bank=before['ram_bank'],next_ai_entry_bank=session.emu.request('status')['ram_bank'],prior_status=status,prior_valid=valid,save_format_unchanged=True)
  (OUT/'target-custom-lifecycle.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
 finally:session.emu.close()
