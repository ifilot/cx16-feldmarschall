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

#ifndef _RANDOM_H
#define _RANDOM_H

#include <stdint.h>

/*
 * The game's own random numbers: a 16-bit xorshift generator, so that the
 * X16 and the native build (src/native) make the same choices from the
 * same seed.
 */

/**
 * @brief Start the sequence from a seed (0 counts as 1)
 */
void random_seed(uint16_t seed);

/**
 * @brief The next number of the sequence, 1 to 65535
 */
uint16_t random_next(void);

#endif
