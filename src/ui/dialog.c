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

#include <string.h>
#pragma static-locals (on)

#include "dialog.h"
#include "video.h"

void dialog_plate(uint8_t col, uint8_t row, uint8_t w, uint8_t h) {
    uint8_t y, tile;

    for(y=0; y<h; y++) {
        // the plate's 3x3 tiles: top edge, middle, bottom edge
        tile = L1_PLATE + (y == 0 ? 0 : (y == h - 1 ? 6 : 3));
        video_tile_row(col, row + y, w, tile, tile + 1, tile + 2);
    }
}

void dialog_centred(uint8_t col, uint8_t w, uint8_t row, const char* s, uint8_t color) {
    video_text_plate(col + ((w - strlen(s)) >> 1), row, s, color);
}
