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

#ifdef __CC65__
#include <ascii_charmap.h>              // strings in ASCII, as the font expects
#endif

#include "pieces.h"

const uint8_t piece_counts[PIECE_TYPES] = {1, 1, 2, 3, 4, 4, 4, 5, 8, 1, 6, 1};

const char piece_glyphs[PIECE_TYPES + 1] = "123456789SBF";

const char* const piece_names[PIECE_TYPES] = {
    "MARSHAL", "GENERAL", "COLONEL", "MAJOR", "CAPTAIN", "LIEUTENANT",
    "SERGEANT", "MINER", "SCOUT", "SPY", "BOMB", "FLAG",
};

uint8_t piece_ranking;

static const char* const numbers[10] = {"10", "9", "8", "7", "6", "5", "4", "3", "2", "1"};

const char* piece_rank(uint8_t type) {
    if(type >= PIECE_BOMB) return "";
    if(piece_ranking == RANKING_MODERN) return numbers[type];
    if(type == PIECE_SPY) return "S";
    return numbers[9 - type];
}

uint8_t piece_rank_key(uint8_t key) {
    if(key == 'S' || key == 's' || key == 0xD3) return PIECE_SPY;
    if(piece_ranking == RANKING_MODERN) {
        if(key == '0') return PIECE_MARSHAL;
        if(key >= '1' && key <= '9') return '0' + 10 - key;
    } else if(key >= '1' && key <= '9') {
        return key - '1';
    }
    return PIECE_TYPES;
}
