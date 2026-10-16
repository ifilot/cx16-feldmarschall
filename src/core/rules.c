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

#include <string.h>
#include "rules.h"
#ifdef AI_MEMORY
#include "ai_memory.h"
#endif
#include "board.h"

uint8_t game_rules;
uint8_t rules_lost[2][PIECE_TYPES];
uint8_t rules_known_lost[2][PIECE_TYPES];
uint8_t rules_rescues[2];
static uint8_t rescued[SQUARES];

static const int8_t step_col[4] = {0, 1, 0, -1};
static const int8_t step_row[4] = {-1, 0, 1, 0};

// per army (0 Red, 1 Blue): its last move and how often in a row its piece
// has gone back and forth between those two squares
static uint8_t shuttle_from[2], shuttle_to[2], shuttle_count[2];

void rules_reset(void) {
    shuttle_count[0] = shuttle_count[1] = 0;
    memset(rescued, 0, sizeof(rescued));
    memset(rules_lost, 0, sizeof(rules_lost));
    memset(rules_known_lost, 0, sizeof(rules_known_lost));
    rules_rescues[0] = rules_rescues[1] = 0;
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
    if(type == PIECE_BOMB && !(game_rules & RULE_MOVING_BOMBS)) return 0;
    if(type == PIECE_FLAG && !(game_rules & RULE_MOVING_FLAG)) return 0;
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
            } else if(IS_PIECE(other) && ((other ^ cell) & CELL_BLUE) && to != banned
                      && type != PIECE_BOMB && type != PIECE_FLAG) {
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
    if(defender == PIECE_BOMB) return attacker == PIECE_MINER ? BATTLE_ATTACKER :
        (game_rules & (RULE_EXPLODING | RULE_MOVING_BOMBS)) ? BATTLE_BOTH : BATTLE_DEFENDER;
    if(attacker == PIECE_SPY && defender == PIECE_MARSHAL) return BATTLE_ATTACKER;
    if(attacker == defender) return (game_rules & RULE_ATTACKER_WINS) ? BATTLE_ATTACKER : BATTLE_BOTH;
    // type numbers rise as the ranks fall, and the spy is last
    return attacker < defender ? BATTLE_ATTACKER : BATTLE_DEFENDER;
}

uint8_t rules_reveal_defender(uint8_t attacker) {
    return !(game_rules & RULE_SILENT) || attacker == PIECE_SCOUT;
}

void rules_reveal_battle(uint8_t from, uint8_t to) {
    board[from] |= CELL_REVEALED;
    if(rules_reveal_defender(PIECE_TYPE(board[from]))) board[to] |= CELL_REVEALED;
}

static void captured(uint8_t cell) {
    uint8_t army = (cell & CELL_BLUE) ? 1 : 0, type = PIECE_TYPE(cell);
    rules_lost[army][type]++;
    if(cell & CELL_REVEALED) rules_known_lost[army][type]++;
}

uint8_t rules_apply(uint8_t from, uint8_t to) {
    uint8_t a = board[from], d = board[to], outcome = BATTLE_QUIET;
    int8_t rows, cols;
    rules_record(from, to);
    if(d == CELL_EMPTY) {
        rows = SQUARE_ROW(from) - SQUARE_ROW(to);
        cols = SQUARE_COL(from) - SQUARE_COL(to);
        if(rows > 1 || rows < -1 || cols > 1 || cols < -1) a |= CELL_REVEALED;
    } else {
        rules_reveal_battle(from, to);
        a = board[from];
        d = board[to];
        outcome = rules_battle(PIECE_TYPE(a), PIECE_TYPE(d));
        if(outcome != BATTLE_ATTACKER) captured(a);
        if(outcome != BATTLE_DEFENDER) captured(d);
    }
#ifdef AI_MEMORY
    ai_memory_observe(from, to, outcome);
#endif
    if(outcome == BATTLE_ATTACKER || outcome == BATTLE_QUIET) {
        board[to] = a | CELL_MOVED;
        rescued[to] = rescued[from];
    } else if(outcome == BATTLE_BOTH) {
        board[to] = CELL_EMPTY;
        rescued[to] = 0;
    }
    board[from] = CELL_EMPTY;
    rescued[from] = 0;
    return outcome;
}

uint8_t rules_flag_arrived(uint8_t sq) {
    if(!(game_rules & RULE_MOVING_FLAG) || !IS_PIECE(board[sq]) || PIECE_TYPE(board[sq]) != PIECE_FLAG) return 0;
    return SQUARE_ROW(sq) == ((board[sq] & CELL_BLUE) ? BOARD_SIZE - 1 : 0);
}

uint8_t rules_can_rescue(uint8_t sq) {
    uint8_t army, type, i, vacant = 0;
    if(!(game_rules & RULE_RESCUE) || sq >= SQUARES || !IS_PIECE(board[sq]) || rescued[sq]) return 0;
    army = (board[sq] & CELL_BLUE) ? 1 : 0;
    type = PIECE_TYPE(board[sq]);
    if(type == PIECE_SCOUT || type == PIECE_BOMB || type == PIECE_FLAG || rules_rescues[army] >= 2) return 0;
    if(SQUARE_ROW(sq) != (army ? BOARD_SIZE - 1 : 0)) return 0;
    for(i=0; i<SQUARES; i++) if(board_home(i, army) && board[i] == CELL_EMPTY) vacant = 1;
    if(!vacant) return 0;
    for(type=0; type<PIECE_BOMB; type++) if(rules_lost[army][type]) return 1;
    return 0;
}

uint8_t rules_rescue(uint8_t sq, uint8_t type, uint8_t destination) {
    uint8_t army, cell;
    if(!rules_can_rescue(sq) || type >= PIECE_BOMB || destination >= SQUARES) return 0;
    army = (board[sq] & CELL_BLUE) ? 1 : 0;
    if(!rules_lost[army][type] || !board_home(destination, army) || board[destination] != CELL_EMPTY) return 0;
    cell = type | (army ? CELL_BLUE : 0);
    if(rules_known_lost[army][type]) {
        rules_known_lost[army][type]--;
        cell |= CELL_REVEALED;
    }
    rules_lost[army][type]--;
    board[destination] = cell;
    rescued[destination] = 0;
    rescued[sq] = 1;
    rules_rescues[army]++;
    return 1;
}

void rules_state_save(uint8_t* out) {
    *out++ = game_rules;
    memcpy(out, rules_lost, sizeof(rules_lost));
    out += sizeof(rules_lost);
    memcpy(out, rules_known_lost, sizeof(rules_known_lost));
    out += sizeof(rules_known_lost);
    memcpy(out, rules_rescues, sizeof(rules_rescues));
    out += sizeof(rules_rescues);
    memcpy(out, rescued, sizeof(rescued));
    out += sizeof(rescued);
    memcpy(out, shuttle_from, 2);
    memcpy(out + 2, shuttle_to, 2);
    memcpy(out + 4, shuttle_count, 2);
}

void rules_state_load(const uint8_t* in) {
    game_rules = *in++;
    memcpy(rules_lost, in, sizeof(rules_lost));
    in += sizeof(rules_lost);
    memcpy(rules_known_lost, in, sizeof(rules_known_lost));
    in += sizeof(rules_known_lost);
    memcpy(rules_rescues, in, sizeof(rules_rescues));
    in += sizeof(rules_rescues);
    memcpy(rescued, in, sizeof(rescued));
    in += sizeof(rescued);
    memcpy(shuttle_from, in, 2);
    memcpy(shuttle_to, in + 2, 2);
    memcpy(shuttle_count, in + 4, 2);
}
