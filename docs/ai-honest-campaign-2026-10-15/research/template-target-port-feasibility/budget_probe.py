"""Compile interface-size probes only; not a posterior implementation or policy."""
from pathlib import Path
import subprocess,json,re,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PROBES={
'main_transfer':r'''#include <stdint.h>
/* Lifecycle-disjoint public history packet and one attacker gain row. */
union transfer {uint8_t history[80];int16_t row[100];};
union transfer template_transfer;
uint8_t template_owner,template_valid;
extern uint8_t __fastcall__ template_export(uint8_t owner);
extern void template_prepare(void);
extern void __fastcall__ template_row(uint8_t rank);
void __fastcall__ template_prepare_main(uint8_t owner) {
 template_owner=owner; template_valid=template_export(owner);
 if(template_valid) template_prepare();
}
void __fastcall__ template_row_main(uint8_t rank) {
 if(template_valid) template_row(rank);
}
''',
'mission_export':r'''#include <stdint.h>
#include "ai_memory.h"
#include "board.h"
#pragma code-name ("MISSIONCODE")
#pragma bss-name ("MISSIONBSS")
extern uint8_t template_transfer[200];
static uint8_t id,n,index;static const ai_piece_history_t* p;
uint8_t __fastcall__ template_export_banked(uint8_t owner) {
 n=0;
 for(id=0;id<AI_MEMORY_PIECES;id++) {
  p=ai_memory_history(id);if(!p)break;
  if(p->owner==owner)continue;
  if(p->origin>=60)index=p->origin-60;
  else if(p->origin<40)index=(3-p->origin/10)*10+p->origin%10;
  else return 0;
  template_transfer[index]=p->known_rank|(p->moves?128:0);
  template_transfer[40+index]=p->square;n++;
 }
 return n==40;
}
/* Separate measured scan; actual validity must be sticky from first sync. */
uint8_t template_initial_board_probe(void) {
 n=0;
 for(id=0;id<100;id++)if(IS_PIECE(board[id])) {
  if(board[id]&(CELL_MOVED|CELL_REVEALED))return 0;n++;
 }
 return n==80;
}
''',
'gateway':r'''.export _template_prepare, _template_row, _template_export
.import _template_prepare_banked, _template_row_banked, _template_export_banked
.bss
saved_template: .res 1
saved_export: .res 1
.code
.proc _template_prepare
 lda $00
 sta saved_template
 lda #25
 sta $00
 jsr _template_prepare_banked
 lda saved_template
 sta $00
 rts
.endproc
.proc _template_row
 pha
 lda $00
 sta saved_template
 lda #25
 sta $00
 pla
 jsr _template_row_banked
 lda saved_template
 sta $00
 rts
.endproc
.proc _template_export
 pha
 lda $00
 sta saved_export
 lda #24
 sta $00
 pla
 jsr _template_export_banked
 pha
 lda saved_export
 sta $00
 pla
 rts
.endproc
'''}
records={}
for name,source in PROBES.items():
 ext='.s' if name=='gateway' else '.c';path=HERE/(name+ext);path.write_text(source)
 commands=[]
 if ext=='.c':commands.append(['cc65','-O','-t','cx16','-I',str(ROOT/'src/core'),'-o',str(HERE/(name+'.s')),str(path)])
 commands.extend([['ca65','-t','cx16','-o',str(HERE/(name+'.o')),str(HERE/(name+'.s'))],['od65','-S',str(HERE/(name+'.o'))]])
 outputs=[]
 for command in commands:
  r=subprocess.run(command,text=True,capture_output=True);outputs.append(dict(argv=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
  if r.returncode:raise RuntimeError(outputs)
 segments={s:int(n) for s,n in re.findall(r'^\s+(\w+):\s+(\d+)',outputs[-1]['stdout'],re.M)}
 records[name]=dict(segments=segments,commands=outputs,source_sha256=hashlib.sha256(source.encode()).hexdigest())
report=dict(scope='Interface object-size probes only; not linked into game, no inference algorithm implemented or port-fit claim.',probes=records)
(HERE/'budget-probes.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({n:r['segments'] for n,r in records.items()},indent=2))
