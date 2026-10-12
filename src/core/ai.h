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

#ifndef _AI_H
#define _AI_H

#include <stdint.h>

/**
 * @brief Choose a move for one army, from what that army knows
 *
 * The board must hold the army's view: its own pieces, and the enemy's
 * pieces with their true type only once revealed (CELL_REVEALED); every
 * other enemy piece has type PIECE_UNKNOWN. The caller keeps the truth.
 *
 * A one-move lookahead. Attacks on a hidden piece are weighed over every
 * rank it could be: the starting army, minus the pieces captured (`lost`)
 * and those revealed on the board. A piece that has moved is no bomb or
 * flag. Quiet moves advance, flee threatened squares and avoid stepping
 * next to known danger; a little randomness (random.h) breaks ties.
 *
 * @param army CELL_BLUE for Blue, 0 for Red
 * @param lost the enemy's captured pieces, per type
 * @param from set to the square of the piece to move (NOWHERE if none)
 * @param to   set to its destination
 */
void ai_move(uint8_t army, const uint8_t* lost, uint8_t* from, uint8_t* to);

/**
 * @brief Forget the previous move (at the start of a game)
 */
void ai_reset(void);

#ifdef AI_TRACE
/* supplied by a test build: called with the score of every candidate move */
void ai_trace(uint8_t from, uint8_t to, int16_t score);
#endif

#endif
