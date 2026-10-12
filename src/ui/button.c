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

#include <string.h>
#pragma static-locals (on)

#include "button.h"
#include "dialog.h"
#include "video.h"

uint8_t button_width(const char* label) {
    return strlen(label) + 4;
}

void button_draw(uint8_t col, uint8_t row, const char* label, uint8_t state) {
    dialog_plate(col, row, button_width(label), BUTTON_HEIGHT);
    video_text_plate(col + 2, row + 1, label,
                     state == BUTTON_HOVER ? TEXT_DEEP_RED :
                     state == BUTTON_DISABLED ? TEXT_BROWN : TEXT_INK);
}

uint8_t button_hit(uint8_t col, uint8_t row, const char* label, int16_t x, int16_t y) {
    return x >= col * 8 && x < (col + button_width(label)) * 8 &&
           y >= row * 8 && y < (row + BUTTON_HEIGHT) * 8;
}
