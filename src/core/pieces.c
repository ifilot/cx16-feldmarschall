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
