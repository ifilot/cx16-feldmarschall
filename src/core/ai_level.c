/* Difficulty is public game configuration, separate from the private AI bank. */
#ifdef __CC65__
#include <ascii_charmap.h>
#endif
#include "ai.h"
#include "board.h"

uint8_t ai_difficulty = AI_NORMAL;
const char* const ai_level_names[AI_LEVELS] = {"EASY", "NORMAL", "HARD"};

void ai_mask(uint8_t army) {
    uint8_t sq, cell;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(IS_PIECE(cell) && (cell & CELL_BLUE) != army && !(cell & CELL_REVEALED))
            board[sq] = (cell & ~CELL_TYPE) | PIECE_UNKNOWN;
    }
}
