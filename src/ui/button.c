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

static void frame(uint8_t col, uint8_t row, uint8_t width, uint8_t state) {
    uint8_t x, y;
    uint16_t base = state == BUTTON_PRESSED ? L1_BUTTON_PRESSED :
                    state == BUTTON_HOVER ? L1_BUTTON_HOVER : L1_PLATE;
    for(y=0; y<BUTTON_HEIGHT; y++) {
        for(x=0; x<width; x++)
            video_tile(col+x, row+y, base+y*3 + (x == 0 ? 0 : x == width-1 ? 2 : 1));
    }
}

uint8_t button_width(const char* label) {
    return strlen(label) + 4;
}

void button_draw(uint8_t col, uint8_t row, const char* label, uint8_t state) {
    frame(col, row, button_width(label), state);
    video_text_plate(col + 2, row + 1, label,
                     (state == BUTTON_HOVER || state == BUTTON_PRESSED) ? TEXT_DEEP_RED :
                     state == BUTTON_DISABLED ? TEXT_BROWN : TEXT_INK);
}

void button_draw_width(uint8_t col, uint8_t row, uint8_t width,
                       const char* label, uint8_t state) {
    frame(col, row, width, state);
    video_text_plate(col + 3, row + 1, label,
                   (state == BUTTON_HOVER || state == BUTTON_PRESSED) ? TEXT_DEEP_RED :
                   state == BUTTON_DISABLED ? TEXT_BROWN : TEXT_INK);
}

uint8_t button_hit(uint8_t col, uint8_t row, const char* label, int16_t x, int16_t y) {
    return x >= col * 8 && x < (col + button_width(label)) * 8 &&
           y >= row * 8 && y < (row + BUTTON_HEIGHT) * 8;
}

void button_toggle(uint8_t col, uint8_t row, uint8_t enabled) {
    uint8_t x, y;
    uint16_t tile = (enabled ? L1_TOGGLE_ON : L1_TOGGLE_OFF) | (TOGGLE_PALETTE << 12);
    for(y=0; y<3; y++) for(x=0; x<5; x++) video_tile(col+x, row+y, tile++);
}
