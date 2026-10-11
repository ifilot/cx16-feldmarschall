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

#include <ascii_charmap.h>
#pragma static-locals (on)

#include "presets.h"
#include "board.h"

/*
 * Ten deployments in classic styles. Each is 40 rank glyphs, Red's front
 * row (rank 4) first and its back row last, columns A to J. Every one holds
 * exactly the army of piece_counts (checked by tools/check_presets.py).
 */
const char* const preset_names[PRESETS] = {
    "CORNER FORTRESS",
    "CENTRE KEEP",
    "LAKE SHADOW",
    "SCOUT SCREEN",
    "BOMB WALL",
    "FALSE CORNER",
    "LEFT HOOK",
    "RIGHT HOOK",
    "TURTLE",
    "BLITZ",
};

static const char* const presets[PRESETS] = {
    /* CORNER FORTRESS */
    "9495996949"
    "6271358975"
    "B869753SB8"
    "FB8B748B6B",
    /* CENTRE KEEP */
    "9596949595"
    "7381257368"
    "48967B9S8B"
    "76B8BFB49B",
    /* LAKE SHADOW */
    "9945BB5999"
    "6328716957"
    "48S97B6B85"
    "73BFB86984",
    /* SCOUT SCREEN */
    "9999599998"
    "4637215846"
    "57B8S3B678"
    "B4FB6B8B57",
    /* BOMB WALL */
    "9899695949"
    "B71B32B685"
    "68S9B74587"
    "394B6F8B57",
    /* FALSE CORNER */
    "9549962949"
    "7351B88976"
    "B86S97B385"
    "BB4B8957F6",
    /* LEFT HOOK */
    "1294959969"
    "3S94768597"
    "48B6B39758"
    "6B7FB8B8B5",
    /* RIGHT HOOK */
    "9699594921"
    "79586749S3"
    "85793B6B84"
    "5B8B8BF7B6",
    /* TURTLE */
    "B95B996984"
    "7426138957"
    "986S9B7B85"
    "34B8F6B795",
    /* BLITZ */
    "1S29995969"
    "6935479584"
    "7B8B637B85"
    "88BFB64B97",
};

void preset_load(uint8_t i) {
    const char* p = presets[i];
    uint8_t sq, type;

    for(sq=RED_HOME0; sq<SQUARES; sq++, p++) {
        for(type=0; piece_glyphs[type] != *p; type++);
        board[sq] = type;
    }
}
