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

#pragma static-locals (on)

#include "rules.h"
#include "board.h"

static const int8_t step_col[4] = {0, 1, 0, -1};
static const int8_t step_row[4] = {-1, 0, 1, 0};

// per army (0 Red, 1 Blue): its last move and how often in a row its piece
// has gone back and forth between those two squares
static uint8_t shuttle_from[2], shuttle_to[2], shuttle_count[2];

void rules_reset(void) {
    shuttle_count[0] = shuttle_count[1] = 0;
}

void rules_record(uint8_t from, uint8_t to) {
    uint8_t army = (board[from] & CELL_BLUE) ? 1 : 0;

    if(shuttle_count[army] && from == shuttle_to[army] && to == shuttle_from[army]) {
        shuttle_count[army]++;
    } else {
        shuttle_count[army] = 1;
    }
    shuttle_from[army] = from;
    shuttle_to[army] = to;
}

uint8_t rules_targets(uint8_t sq, uint8_t* out) {
    uint8_t cell = board[sq], type, dir, col, row, to, other, army, banned = NOWHERE, n = 0;

    if(!IS_PIECE(cell)) return 0;
    type = PIECE_TYPE(cell);
    if(type == PIECE_BOMB || type == PIECE_FLAG) return 0;
    // the two-squares rule: this piece may not go back once more
    army = (cell & CELL_BLUE) ? 1 : 0;
    if(sq == shuttle_to[army] && shuttle_count[army] >= TWO_SQUARES) banned = shuttle_from[army];
    for(dir=0; dir<4; dir++) {
        col = SQUARE_COL(sq);
        row = SQUARE_ROW(sq);
        for(;;) {
            col += step_col[dir];               // leaving the board wraps past 9
            row += step_row[dir];
            if(col >= BOARD_SIZE || row >= BOARD_SIZE) break;
            to = row * BOARD_SIZE + col;
            other = board[to];
            if(other == CELL_EMPTY) {
                if(to != banned) out[n++] = to;
                if(type == PIECE_SCOUT) continue;
            } else if(IS_PIECE(other) && ((other ^ cell) & CELL_BLUE) && to != banned) {
                out[n++] = to;                  // an enemy: attack it
            }
            break;
        }
    }
    return n;
}

uint8_t rules_has_move(uint8_t blue) {
    static uint8_t targets[MAX_TARGETS];
    uint8_t sq, cell;

    blue = blue ? CELL_BLUE : 0;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(IS_PIECE(cell) && (cell & CELL_BLUE) == blue && rules_targets(sq, targets)) return 1;
    }
    return 0;
}

uint8_t rules_battle(uint8_t attacker, uint8_t defender) {
    if(defender == PIECE_FLAG) return BATTLE_ATTACKER;
    if(defender == PIECE_BOMB) return attacker == PIECE_MINER ? BATTLE_ATTACKER : BATTLE_DEFENDER;
    if(attacker == PIECE_SPY && defender == PIECE_MARSHAL) return BATTLE_ATTACKER;
    if(attacker == defender) return BATTLE_BOTH;
    // type numbers rise as the ranks fall, and the spy is last
    return attacker < defender ? BATTLE_ATTACKER : BATTLE_DEFENDER;
}
