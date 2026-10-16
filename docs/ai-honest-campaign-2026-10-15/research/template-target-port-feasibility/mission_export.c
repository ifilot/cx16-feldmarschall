#include <stdint.h>
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
