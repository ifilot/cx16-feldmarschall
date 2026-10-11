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

#pragma static-locals (on)

#include "drag.h"
#include "video.h"

int16_t drag_cx, drag_cy;
static int16_t grab_x, grab_y;

void drag_begin(uint8_t token, uint8_t army, int16_t x, int16_t y,
                int16_t pointer_x, int16_t pointer_y) {
    grab_x = pointer_x - x;
    grab_y = pointer_y - y;
    video_sprite_token(SPRITE_DRAG, token, army);
    drag_place(x, y);
}

void drag_follow(int16_t pointer_x, int16_t pointer_y) {
    drag_place(pointer_x - grab_x, pointer_y - grab_y);
}

void drag_place(int16_t x, int16_t y) {
    video_sprite_move(SPRITE_DRAG, x, y);
    drag_cx = x + SQUARE / 2;
    drag_cy = y + SQUARE / 2;
}

void drag_end(void) {
    video_sprite_hide(SPRITE_DRAG);
}
