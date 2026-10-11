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

#ifndef _AI_H
#define _AI_H

#include <stdint.h>

/**
 * @brief Choose Blue's move
 *
 * A one-move lookahead that only uses what Blue may know: its own pieces,
 * the red pieces that have been revealed, and how many pieces of each rank
 * Red still has hidden. Attacks on a hidden piece are weighed over every
 * rank it could be (a piece that has moved is no bomb or flag). Quiet moves
 * advance, flee threatened squares and avoid stepping next to known danger.
 *
 * @param from set to the square of the piece to move (NOWHERE if none)
 * @param to   set to its destination
 */
void ai_move(uint8_t* from, uint8_t* to);

#endif
