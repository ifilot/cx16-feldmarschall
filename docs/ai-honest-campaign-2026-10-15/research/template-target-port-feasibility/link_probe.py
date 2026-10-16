"""Full link budget with an explicitly NONFUNCTIONAL inference-bank stub.

Only temporary source copies change. No executable from this probe is run.
"""
from pathlib import Path
import subprocess,json,re,hashlib,shutil,tempfile,zipfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
FLAGS=['BANKED_AI','AI_MISSIONS','AI_MEMORY','AI_STUDENT','AI_STUDENT_V2','AI_STUDENT_PRODUCTION','AI_STUDENT_COOP_GUARD','AI_TEMPLATE_BANK_BUDGET']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(ROOT/'src')):sha(p) for p in (ROOT/'src').rglob('*') if p.is_file()}
with tempfile.TemporaryDirectory(prefix='template-bank-link-') as temp:
 tree=Path(temp)/'src';shutil.copytree(ROOT/'src',tree,ignore=shutil.ignore_patterns('*.o','*.PRG','*.BIN','*.map','*.sym'))
 for name in ('main_transfer.c','mission_export.c'):shutil.copyfile(HERE/name,tree/name)
 shutil.copyfile(HERE/'gateway.s',tree/'ui/template_gateway.s')
 stub='''#include <stdint.h>\n#pragma code-name ("BELIEFCODE")\n#pragma rodata-name ("BELIEFRODATA")\n#pragma bss-name ("BELIEFBSS")\nextern int16_t template_transfer[100];\n/* Space reservations, not an inference implementation. */\nuint8_t template_constants[320]={0};\nuint16_t posterior_q12[200];\nint16_t all_rank_cache[12][100];\nuint8_t inference_scratch[256];\nvoid template_prepare_banked(void) {}\nvoid __fastcall__ template_row_banked(uint8_t rank) {\n uint8_t i;for(i=0;i<100;i++)template_transfer[i]=all_rank_cache[rank][i];\n}\n'''
 # Use const to ensure the320-byte table belongs to the new bank's RO segment.
 stub=stub.replace('uint8_t template_constants','const uint8_t template_constants')
 (tree/'inference_stub.c').write_text(stub)
 p=tree/'core/ai.c';s=p.read_text();s=s.replace('#include <string.h>','#include <string.h>\n#include <stdint.h>\nextern uint8_t template_valid;\nextern int16_t template_transfer[100];\nvoid __fastcall__ template_prepare_main(uint8_t owner);\nvoid __fastcall__ template_row_main(uint8_t rank);',1)
 anchor='#ifdef AI_BELIEF_PRIORS\n/* Exact Q12 expected gain'
 assert s.count(anchor)==1
 helper='''#ifdef AI_TEMPLATE_BANK_BUDGET
#pragma code-name (push, "CODE")
static int16_t expected_at(uint8_t a,uint8_t square) {
 if(!game_rules && ai_difficulty==AI_NORMAL && template_valid)return template_transfer[square];
 return attack[a][!!(board[square]&CELL_MOVED)];
}
#pragma code-name (pop)
#elif defined(AI_BELIEF_PRIORS)
/* Exact Q12 expected gain'''
 s=s.replace(anchor,helper)
 s=s.replace('defined(AI_BELIEF_PRIORS) || defined(AI_BACKROW_PRIOR)','defined(AI_BELIEF_PRIORS) || defined(AI_BACKROW_PRIOR) || defined(AI_TEMPLATE_BANK_BUDGET)')
 anchor='    for(sq=0; sq<PIECE_TYPES; sq++) {\n        attack[sq][0]'
 assert s.count(anchor)==1;s=s.replace(anchor,'    template_prepare_main(army);\n'+anchor)
 anchor='        if(n) {\n            source_danger = threat';assert s.count(anchor)==1
 s=s.replace(anchor,'        if(n) {\n            template_row_main(PIECE_TYPE(cell));\n            source_danger = threat')
 p.write_text(s)
 p=tree/'ui/sound.c';s=p.read_text();anchor='    if(!load_banked("MISSION.BIN", 24)) return 0;';assert s.count(anchor)==1
 p.write_text(s.replace(anchor,anchor+'\n    if(!load_banked("BELIEF.BIN", 25)) return 0;'))
 p=tree/'feldmarschall.cfg';s=p.read_text();s=s.replace('    MISSION:  file = "MISSION.BIN", start = $A000, size = $2000;','    MISSION:  file = "MISSION.BIN", start = $A000, size = $2000;\n    BELIEF: file = "BELIEF.BIN", start = $A000, size = $2000;')
 s=s.replace('    MISSIONCODE: load = MISSION, type = ro;','    BELIEFCODE: load = BELIEF, type = ro;\n    BELIEFRODATA: load = BELIEF, type = ro;\n    BELIEFBSS: load = BELIEF, type = bss;\n    MISSIONCODE: load = MISSION, type = ro;');p.write_text(s)
 inputs=sorted(p.relative_to(tree).as_posix() for p in tree.glob('*.c'))
 for folder in ('core','ui','scenes'):inputs+=sorted(p.relative_to(tree).as_posix() for p in (tree/folder).glob('*.c'))
 assembly=[]
 for folder in ('ui','scenes'):assembly+=sorted(p.relative_to(tree).as_posix() for p in (tree/folder).glob('*.s'))
 command=['cl65','-O','-t','cx16','-I','.','-I','core','-I','ui','-I','scenes']+['-D'+f for f in FLAGS]+['--asm-define','AI_MEMORY','-Wl','-D,__STACKSIZE__=0x0400','-C','feldmarschall.cfg','-o','FELDMARS.PRG','-m','FELDMARS.map','-Ln','FELDMARS.sym']+inputs+assembly+['vendor/zsmkit.lib']
 r=subprocess.run(command,cwd=tree,text=True,capture_output=True)
 out=dict(scope='Budget-only full link with NONFUNCTIONAL inference stub; no executable run and no posterior implementation.',command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,flags=FLAGS,input_sha256={n:sha(tree/n) for n in inputs+assembly+['feldmarschall.cfg']})
 if (tree/'FELDMARS.map').exists():
  text=(tree/'FELDMARS.map').read_text().split('Segment list:',1)[1].split('Exports list',1)[0]
  linked={seg:dict(start=int(start,16),end=int(end,16),size=int(size,16)) for seg,start,end,size in re.findall(r'^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})',text,re.M)}
  out['segments']=linked
  out['free_bytes']={bank:8192-sum(linked.get(n,{}).get('size',0) for n in names) for bank,names in {'AI':('AICODE','AIRODATA','AIBSS'),'MISSION':('MISSIONCODE','MISSIONRODATA','MISSIONBSS'),'BELIEF':('BELIEFCODE','BELIEFRODATA','BELIEFBSS')}.items()}
  out['free_bytes']['MAIN']=0x9b00-1-linked['BSS']['end']
 after={str(p.relative_to(ROOT/'src')):sha(p) for p in (ROOT/'src').rglob('*') if p.is_file()};assert before==after
 out['workspace_src_unchanged']=True
 with zipfile.ZipFile(HERE/'link-budget-evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
  for name in ['core/ai.c','ui/sound.c','feldmarschall.cfg','main_transfer.c','mission_export.c','inference_stub.c','ui/template_gateway.s','FELDMARS.map','FELDMARS.sym']:
   if (tree/name).exists():archive.writestr(name,(tree/name).read_bytes())
 (HERE/'link-budget.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(dict(returncode=r.returncode,stderr=r.stderr,free_bytes=out.get('free_bytes')),indent=2))
