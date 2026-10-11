/**************************************************************************
 *                                                                        *
 *   Author: Ivo Filot <ivo@ivofilot.nl>                                  *
 *                                                                        *
 *   CX16-STRATEGO is free software:                                      *
 *   you can redistribute it and/or modify it under the terms of the      *
 *   GNU General Public License as published by the Free Software         *
 *   Foundation, either version 3 of the License, or (at your option)     *
 *   any later version.                                                   *
 *                                                                        *
 *   CX16-STRATEGO is distributed in the hope that it will be useful,     *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty          *
 *   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.              *
 *   See the GNU General Public License for more details.                 *
 *                                                                        *
 *   You should have received a copy of the GNU General Public License    *
 *   along with this program.  If not, see http://www.gnu.org/licenses/.  *
 *                                                                        *
 **************************************************************************/

#pragma static-locals (on)

#include "board.h"

uint8_t board[SQUARES];

void board_clear(void) {
    uint8_t sq;

    for(sq=0; sq<SQUARES; sq++) board[sq] = CELL_EMPTY;
    // the lakes: C5-D6 and G5-H6 (LAKES in assets/scripts/layout.py)
    board[42] = board[43] = board[52] = board[53] = CELL_LAKE;
    board[46] = board[47] = board[56] = board[57] = CELL_LAKE;
}

uint8_t board_count(uint8_t type, uint8_t blue) {
    uint8_t sq, cell, n = 0;

    blue = blue ? CELL_BLUE : 0;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(IS_PIECE(cell) && PIECE_TYPE(cell) == type && (cell & CELL_BLUE) == blue) n++;
    }
    return n;
}

uint8_t board_home(uint8_t sq, uint8_t blue) {
    return blue ? sq < BLUE_HOME0 + ARMY_SIZE : sq >= RED_HOME0;
}
