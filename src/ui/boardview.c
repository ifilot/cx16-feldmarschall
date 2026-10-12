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

#pragma static-locals (on)

#include "boardview.h"
#include "board.h"
#include "video.h"

uint8_t view_show_all;

uint8_t view_token(uint8_t cell) {
    if((cell & CELL_BLUE) && !view_show_all) return TOKEN_HIDDEN;
    return PIECE_TYPE(cell);
}

static void draw(uint8_t sq, uint8_t token) {
    video_token(BOARD_X / 8 + SQUARE_COL(sq) * SQUARE_TILES,
                BOARD_Y / 8 + SQUARE_ROW(sq) * SQUARE_TILES,
                token, (board[sq] & CELL_BLUE) ? ARMY_BLUE : ARMY_RED);
}

void view_square(uint8_t sq) {
    if(IS_PIECE(board[sq])) draw(sq, view_token(board[sq]));
    else view_empty(sq);
}

void view_square_open(uint8_t sq) {
    draw(sq, PIECE_TYPE(board[sq]));
}

void view_empty(uint8_t sq) {
    video_empty_square(SQUARE_COL(sq), SQUARE_ROW(sq));
}

void view_board(void) {
    uint8_t sq;

    for(sq=0; sq<SQUARES; sq++) view_square(sq);
}

void view_marker(uint8_t sq) {
    video_marker(SQUARE_COL(sq), SQUARE_ROW(sq));
}

uint8_t view_at(int16_t x, int16_t y) {
    int16_t col, row;

    if(x < BOARD_X || y < BOARD_Y) return NOWHERE;
    col = (x - BOARD_X) / SQUARE;
    row = (y - BOARD_Y) / SQUARE;
    if(col >= BOARD_SIZE || row >= BOARD_SIZE) return NOWHERE;
    return row * BOARD_SIZE + col;
}

int16_t view_x(uint8_t sq) {
    return BOARD_X + SQUARE_COL(sq) * SQUARE;
}

int16_t view_y(uint8_t sq) {
    return BOARD_Y + SQUARE_ROW(sq) * SQUARE;
}
