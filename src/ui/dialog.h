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

#ifndef _DIALOG_H
#define _DIALOG_H

#include <stdint.h>

/**
 * @brief Draw a light grey plate on layer 1, floating over the screen
 *
 * @param w, h size in tiles (at least 2 x 2)
 */
void dialog_plate(uint8_t col, uint8_t row, uint8_t w, uint8_t h);

/**
 * @brief Write text on a plate, centred between two columns
 */
void dialog_centred(uint8_t col, uint8_t w, uint8_t row, const char* s, uint8_t color);

#endif
