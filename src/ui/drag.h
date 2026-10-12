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

#ifndef _DRAG_H
#define _DRAG_H

#include <stdint.h>

/* the centre of the lifted token, which decides where it lands */
extern int16_t drag_cx, drag_cy;

/**
 * @brief Lift a token off the square at (x, y), grabbed at the pointer
 *
 * The drag sprite shows the token with a shadow; the caller clears the
 * square underneath.
 */
void drag_begin(uint8_t token, uint8_t army, int16_t x, int16_t y,
                int16_t pointer_x, int16_t pointer_y);

/**
 * @brief Keep the token under the pointer, at the point it was grabbed
 */
void drag_follow(int16_t pointer_x, int16_t pointer_y);

/**
 * @brief Put the lifted token at (x, y) (its square's top-left corner)
 */
void drag_place(int16_t x, int16_t y);

void drag_end(void);

#endif
