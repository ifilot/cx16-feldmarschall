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

#include <stdlib.h>
#pragma static-locals (on)

#include "ai.h"
#include "board.h"
#include "rules.h"

#define FLAG_VALUE      2000
#define BACKTRACK       20          // penalty for undoing the previous move

// what each piece is worth to its army
static const int16_t value[PIECE_TYPES] = {
    400, 200, 100, 75, 45, 30, 15, 25, 10, 100, 20, 1000,
};

static uint8_t hidden[PIECE_TYPES];     // Red's unrevealed pieces per rank
static uint8_t hidden_mobile;
static int16_t risk[PIECE_TYPES];       // expected loss next to a hidden red piece
static uint8_t last_from = NOWHERE, last_to = NOWHERE;
static uint8_t targets[MAX_TARGETS];

/**
 * @brief Blue's gain when a piece of type a attacks one of type d
 */
static int16_t gain(uint8_t a, uint8_t d) {
    if(d == PIECE_FLAG) return FLAG_VALUE;
    switch(rules_battle(a, d)) {
        case BATTLE_ATTACKER: return value[d];
        case BATTLE_DEFENDER: return -value[a];
        default:              return value[d] - value[a];
    }
}

/**
 * @brief Count Red's hidden ranks and the risk they pose to each blue rank
 */
static void survey(void) {
    uint8_t sq, cell, a, t;
    int32_t loss;

    for(t=0; t<PIECE_TYPES; t++) hidden[t] = 0;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(IS_PIECE(cell) && !(cell & (CELL_BLUE | CELL_REVEALED))) hidden[PIECE_TYPE(cell)]++;
    }
    hidden_mobile = 0;
    for(t=0; t<PIECE_BOMB; t++) hidden_mobile += hidden[t];
    // a hidden red piece next to blue piece a may attack it
    for(a=0; a<PIECE_BOMB; a++) {
        loss = 0;
        for(t=0; t<PIECE_BOMB; t++) {
            if(rules_battle(t, a) != BATTLE_DEFENDER) loss += (int32_t)hidden[t] * value[a];
        }
        risk[a] = hidden_mobile ? loss / hidden_mobile : 0;
    }
}

/**
 * @brief Expected gain of attacking a hidden red piece
 */
static int16_t expected(uint8_t a, uint8_t moved) {
    int32_t sum = 0;
    uint8_t t, n = 0, last = moved ? PIECE_BOMB : PIECE_TYPES;

    for(t=0; t<last; t++) {
        sum += (int32_t)hidden[t] * gain(a, t);
        n += hidden[t];
    }
    return n ? sum / n : 0;
}

/**
 * @brief The worst loss a blue piece of type a risks on square sq
 */
static int16_t threat(uint8_t sq, uint8_t a) {
    static const int8_t step[4] = {-BOARD_SIZE, 1, BOARD_SIZE, -1};
    int16_t worst = 0, loss;
    uint8_t dir, nb, cell, t, col = SQUARE_COL(sq);

    for(dir=0; dir<4; dir++) {
        if((dir == 1 && col == BOARD_SIZE - 1) || (dir == 3 && col == 0)) continue;
        nb = sq + step[dir];
        if(nb >= SQUARES) continue;
        cell = board[nb];
        if(!IS_PIECE(cell) || (cell & CELL_BLUE)) continue;
        if(cell & CELL_REVEALED) {
            t = PIECE_TYPE(cell);
            switch(rules_battle(t, a)) {
                case BATTLE_ATTACKER: loss = value[a]; break;
                case BATTLE_BOTH:     loss = value[a] - value[t]; break;
                default:              loss = 0;
            }
        } else if(cell & CELL_MOVED) {
            loss = risk[a];
        } else {
            loss = risk[a] >> 1;                // may well be a bomb
        }
        if(loss > worst) worst = loss;
    }
    return worst;
}

static int16_t score(uint8_t from, uint8_t to) {
    uint8_t mover = board[from], target = board[to], a = PIECE_TYPE(mover);
    int16_t s;

    if(target == CELL_EMPTY) {
        // advance towards Red, flee danger, avoid stepping into it
        s = ((int16_t)SQUARE_ROW(to) - SQUARE_ROW(from)) * 4;
        s += threat(from, a) - threat(to, a);
    } else if(target & CELL_REVEALED) {
        s = gain(a, PIECE_TYPE(target)) - (threat(to, a) >> 1);
    } else {
        s = expected(a, target & CELL_MOVED) - (threat(to, a) >> 1);
    }
    if(from == last_to && to == last_from) s -= BACKTRACK;
    return s + (rand() & 7);
}

void ai_move(uint8_t* from, uint8_t* to) {
    uint8_t sq, i, n;
    int16_t s, best = -32767;

    *from = *to = NOWHERE;
    survey();
    for(sq=0; sq<SQUARES; sq++) {
        if(!IS_PIECE(board[sq]) || !(board[sq] & CELL_BLUE)) continue;
        n = rules_targets(sq, targets);
        for(i=0; i<n; i++) {
            s = score(sq, targets[i]);
            if(s > best) {
                best = s;
                *from = sq;
                *to = targets[i];
            }
        }
    }
    last_from = *from;
    last_to = *to;
}
