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

#ifndef _PIECES_H
#define _PIECES_H

#include <stdint.h>

/*
 * Piece types, strongest first (classic European numbering: 1 = Marshal).
 * Token numbers follow the same order (PIECES in assets/scripts/layout.py).
 */
#define PIECE_MARSHAL       0
#define PIECE_GENERAL       1
#define PIECE_COLONEL       2
#define PIECE_MAJOR         3
#define PIECE_CAPTAIN       4
#define PIECE_LIEUTENANT    5
#define PIECE_SERGEANT      6
#define PIECE_MINER         7
#define PIECE_SCOUT         8
#define PIECE_SPY           9
#define PIECE_BOMB          10
#define PIECE_FLAG          11
#define PIECE_TYPES         12
#define PIECE_UNKNOWN       12      // in a player's view: an enemy piece not yet seen

#define ARMY_SIZE           40

/*
 * A square holds CELL_EMPTY, CELL_LAKE, or a piece: its type in the low
 * nibble plus flags. Values with bit 7 set are never pieces.
 */
#define CELL_EMPTY          0xFF
#define CELL_LAKE           0xFE
#define CELL_TYPE           0x0F
#define CELL_BLUE           0x10    // the piece belongs to Blue (the computer)
#define CELL_REVEALED       0x20    // the opponent has seen what it is (Blue remembers)
#define CELL_MOVED          0x40    // it has moved, so it is no bomb or flag

#define IS_PIECE(cell)      ((cell) < CELL_LAKE)
#define PIECE_TYPE(cell)    ((cell) & CELL_TYPE)

extern const uint8_t piece_counts[PIECE_TYPES];
extern const char piece_glyphs[PIECE_TYPES + 1];
extern const char* const piece_names[PIECE_TYPES];

#endif
