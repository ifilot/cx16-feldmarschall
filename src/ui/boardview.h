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

#ifndef _BOARDVIEW_H
#define _BOARDVIEW_H

#include <stdint.h>

/* when set, Blue's pieces are drawn face up (at the end of a game) */
extern uint8_t view_show_all;

/**
 * @brief The token that shows a cell to the player: Blue's pieces show
 *        their back, unless view_show_all is set
 *
 * A blue piece seen in a battle turns face down again afterwards; the
 * player has to remember it, as in the board game.
 */
uint8_t view_token(uint8_t cell);

/**
 * @brief Draw one square on layer 1 as the player sees it
 */
void view_square(uint8_t sq);

/**
 * @brief Draw the piece on a square face up (a defender in a battle)
 */
void view_square_open(uint8_t sq);

/**
 * @brief Draw a square without its piece (while the piece is lifted)
 */
void view_empty(uint8_t sq);

void view_board(void);

/**
 * @brief Show a move-target dot on an empty square
 */
void view_marker(uint8_t sq);

/**
 * @brief The board square under a screen pixel, or NOWHERE
 */
uint8_t view_at(int16_t x, int16_t y);

/**
 * @brief Top-left screen pixel of a board square
 */
int16_t view_x(uint8_t sq);
int16_t view_y(uint8_t sq);

#endif
