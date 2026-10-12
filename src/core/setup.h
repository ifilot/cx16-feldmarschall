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

#ifndef _SETUP_H
#define _SETUP_H

#include <stdint.h>

/**
 * @brief Deploy an army at random on its home rows
 *
 * The flag goes on the back row with bombs beside and in front of it; the
 * other pieces are shuffled over the remaining home squares.
 */
void setup_random(uint8_t blue);

/**
 * @brief Keep the player's deployment (Red's home rows) for later scenes
 */
void setup_store(void);

/**
 * @brief Put the kept deployment back on Red's home rows
 */
void setup_load(void);

/**
 * @brief Whether the kept deployment holds all 40 pieces
 */
uint8_t setup_complete(void);

#endif
