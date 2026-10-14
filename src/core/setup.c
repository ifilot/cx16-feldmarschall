/**************************************************************************
 *                                                                        *
 *   Author: Ivo Filot <ivo@ivofilot.nl>                                  *
 *                                                                        *
 *   CX16-FELDMARSCHALL is free software:                                 *
 *   you can redistribute it and/or modify it under the terms of the      *
 *   GNU General Public License as published by the Free Software         *
 *   Foundation, either version 3 of the License, or (at your option)     *
 *   any later version.                                                   *
 *                                                                        *
 *   CX16-FELDMARSCHALL is distributed in the hope that it will be        *
 *   useful, but WITHOUT ANY WARRANTY; without even the implied           *
 *   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     *
 *   See the GNU General Public License for more details.                 *
 *                                                                        *
 *   You should have received a copy of the GNU General Public License    *
 *   along with this program.  If not, see http://www.gnu.org/licenses/.  *
 *                                                                        *
 **************************************************************************/

#include <string.h>
#pragma static-locals (on)

#include "setup.h"
#include "board.h"
#include "random.h"

static uint8_t saved[ARMY_SIZE];    // Red's home rows, top row first
static uint8_t saved_valid;

#if defined(BANKED_AI) && defined(AI_MEMORY)
/* The tracker/student needs main RAM. Random deployment runs wholly in bank
 * 24, including its work pool; stored player deployments stay in main RAM. */
#pragma code-name ("MISSIONCODE")
#pragma rodata-name ("MISSIONRODATA")
#pragma bss-name ("MISSIONBSS")
#define setup_random setup_random_banked
#endif
static uint8_t pool[ARMY_SIZE];

/**
 * @brief Put a bomb on a home square if it is free
 */
static uint8_t bomb(uint8_t sq, uint8_t army) {
    if(board[sq] != CELL_EMPTY) return 0;
    board[sq] = PIECE_BOMB | army;
    return 1;
}

void setup_random(uint8_t blue) {
    uint8_t i, j, k, n, type, sq, flag, bombs = 0;
    uint8_t first = blue ? BLUE_HOME0 : RED_HOME0;
    uint8_t army = blue ? CELL_BLUE : 0;

    for(i=0; i<ARMY_SIZE; i++) board[first + i] = CELL_EMPTY;

    // the flag on the back row, guarded by bombs
    flag = (blue ? 0 : (BOARD_SIZE - 1) * BOARD_SIZE) + random_next() % BOARD_SIZE;
    board[flag] = PIECE_FLAG | army;
    if(SQUARE_COL(flag) > 0) bombs += bomb(flag - 1, army);
    if(SQUARE_COL(flag) < BOARD_SIZE - 1) bombs += bomb(flag + 1, army);
    bombs += bomb(blue ? flag + BOARD_SIZE : flag - BOARD_SIZE, army);

    // shuffle the other pieces over the free home squares
    n = 0;
    for(type=0; type<PIECE_TYPES; type++) {
        k = piece_counts[type];
        if(type == PIECE_FLAG) k = 0;
        if(type == PIECE_BOMB) k -= bombs;
        while(k--) pool[n++] = type;
    }
    for(i=n-1; i>0; i--) {
        j = random_next() % (i + 1);
        k = pool[i];
        pool[i] = pool[j];
        pool[j] = k;
    }
    j = 0;
    for(i=0; i<ARMY_SIZE; i++) {
        sq = first + i;
        if(board[sq] == CELL_EMPTY) board[sq] = pool[j++] | army;
    }
}

#if defined(BANKED_AI) && defined(AI_MEMORY)
#pragma code-name ("CODE")
#pragma rodata-name ("RODATA")
#pragma bss-name ("BSS")
#endif
void setup_store(void) {
    memcpy(saved, board + RED_HOME0, ARMY_SIZE);
    saved_valid = 1;
}

void setup_load(void) {
    if(saved_valid) memcpy(board + RED_HOME0, saved, ARMY_SIZE);
}

uint8_t setup_complete(void) {
    uint8_t i;

    if(!saved_valid) return 0;
    for(i=0; i<ARMY_SIZE; i++) {
        if(!IS_PIECE(saved[i])) return 0;
    }
    return 1;
}
