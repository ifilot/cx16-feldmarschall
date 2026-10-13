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

#include <ascii_charmap.h>
#pragma static-locals (on)

#include "dev.h"
#include "board.h"
#include "rules.h"
#include "scene.h"
#include "play.h"

/*
 * A scenario: its rule options, whether Blue moves first, then the pieces
 * as (square, cell) pairs up to END. Square 0 is a10, 99 is j1; a red cell
 * is its type, plus CELL_MOVED (0x40) and CELL_REVEALED (0x20) when Blue
 * knows it has moved or what it is; a blue cell adds CELL_BLUE (0x10).
 * Red's flag sits on j1 behind bombs on i1 and j2; Blue's on a10, behind
 * bombs on b10 and a9. Every other piece has fallen.
 */
#define END             0xFF
#define RED_FLAG        99, 0x0B, 98, 0x0A, 89, 0x0A
#define BLUE_FLAG       0, 0x1B, 1, 0x1A, 10, 0x1A

const char* const dev_names[DEV_SCENARIOS] = {
    "LOSE: LAST PIECE TAKEN",
    "WIN: LAST ENEMY TAKEN",
    "DRAW: NO ONE CAN MOVE",
    "WIN: CAPTURE THE FLAG",
    "LOSE: FLAG CAPTURED",
    "RESCUE A PIECE",
};

// Blue's marshal on e5 takes the known sergeant on e4, Red's last mover
static const uint8_t last_taken[] = {0, 1, RED_FLAG, BLUE_FLAG, 64, 0x66, 54, 0x10, END};
// Red's marshal on e4 takes the sergeant on e5, Blue's last mover
static const uint8_t last_enemy[] = {0, 0, RED_FLAG, BLUE_FLAG, 64, 0x40, 54, 0x16, END};
// the last movers, both sergeants, fall together
static const uint8_t no_one[] = {0, 0, RED_FLAG, BLUE_FLAG, 64, 0x46, 54, 0x16, END};
// Red's captain on a9 takes the flag on a10
static const uint8_t take_flag[] = {0, 0, RED_FLAG, 0, 0x1B, 1, 0x1A, 10, 0x44, 54, 0x16, END};
// Blue's captain on j2 takes Red's flag, which it has seen
static const uint8_t lose_flag[] = {0, 1, 99, 0x2B, 98, 0x0A, 89, 0x14, BLUE_FLAG, 90, 0x46, END};
// Red's major reaches e10, Blue's back row, with the rescue rule
static const uint8_t rescue[] = {RULE_RESCUE, 0, RED_FLAG, BLUE_FLAG, 14, 0x43, 9, 0x18, END};

static const uint8_t* const scenarios[DEV_SCENARIOS] = {
    last_taken, last_enemy, no_one, take_flag, lose_flag, rescue,
};

uint8_t dev_start(uint8_t n) {
    const uint8_t* p = scenarios[n];

    board_clear();
    game_rules = *p++;
    n = *p++;
    for(; *p != END; p += 2) board[p[0]] = p[1];
    play_position(n);
    return SCENE_RESUME;
}
