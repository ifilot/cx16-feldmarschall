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

#ifndef _BUTTON_H
#define _BUTTON_H

#include <stdint.h>

#define BUTTON_NORMAL       0
#define BUTTON_HOVER        1
#define BUTTON_DISABLED     2

#define BUTTON_HEIGHT       3       // tiles

/**
 * @brief Width in tiles of a button with this label
 */
uint8_t button_width(const char* label);

/**
 * @brief Draw a raised button: a small plate with its label
 */
void button_draw(uint8_t col, uint8_t row, const char* label, uint8_t state);

/**
 * @brief Whether a screen pixel lies on the button
 */
uint8_t button_hit(uint8_t col, uint8_t row, const char* label, int16_t x, int16_t y);

#endif
