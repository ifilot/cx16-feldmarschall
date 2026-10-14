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

/*
 * BRIDGE.PRG: the game's computer player on the X16, without graphics,
 * driven through a mailbox in golden RAM. tools/parity.py uses it to check
 * that the 6502 build chooses the same moves as the native engine.
 *
 *   $0400       command: the host writes 1, the bridge answers 2
 *   $0401       army (0 Red, 1 Blue)
 *   $0402-0403  random seed, little-endian
 *   $0404-040F  the enemy's captured pieces per type
 *   $0410-0473  the army's view of the board, as in src/core/board.h
 *   $0474-0475  the chosen move: from and to (255: none)
 *   $0476       difficulty (0 Easy, 1 Normal, 2 Hard)
 *   $0477       rules bitmask (0..63)
 */
#include <string.h>

#include "board.h"
#include "random.h"
#include "ai.h"
#include "rules.h"

#define MAILBOX     ((volatile uint8_t*)0x0400)
#define COMMAND     0
#define ARMY        1
#define SEED        2
#define LOST        4
#define VIEW        16
#define MOVE        116
#define LEVEL       118
#define OPTIONS     119

static uint8_t lost[PIECE_TYPES];

#ifdef AI_TRACE
/* $0480: number of candidates, then from, to and score for each (4 bytes) */
#define TRACE       ((uint8_t*)0x0480)
#define TRACE_MAX   ((0x0800 - 0x0481) / 4)

void ai_trace(uint8_t from, uint8_t to, int16_t score) {
    uint8_t* p;

    if(TRACE[0] >= TRACE_MAX) return;
    p = TRACE + 1 + TRACE[0]++ * 4;
    p[0] = from;
    p[1] = to;
    p[2] = (uint8_t)score;
    p[3] = (uint16_t)score >> 8;
}
#endif

void main(void) {
    uint8_t from, to;

    MAILBOX[COMMAND] = 0;
    for(;;) {
        if(MAILBOX[COMMAND] != 1) continue;
        memcpy(lost, (uint8_t*)MAILBOX + LOST, PIECE_TYPES);
        memcpy(board, (uint8_t*)MAILBOX + VIEW, SQUARES);
        random_seed(MAILBOX[SEED] | (MAILBOX[SEED + 1] << 8));
        ai_reset();
        rules_reset();
        ai_difficulty = MAILBOX[LEVEL] < AI_LEVELS ? MAILBOX[LEVEL] : AI_NORMAL;
        game_rules = MAILBOX[OPTIONS] & 63;
#ifdef AI_TRACE
        TRACE[0] = 0;
#endif
        ai_move(MAILBOX[ARMY] ? CELL_BLUE : 0, lost, &from, &to);
        MAILBOX[MOVE] = from;
        MAILBOX[MOVE + 1] = to;
        MAILBOX[COMMAND] = 2;
    }
}
