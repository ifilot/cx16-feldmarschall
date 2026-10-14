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
#include "ai.h"
#include "board.h"
#include "random.h"
#include "rules.h"

#ifdef BANKED_AI
#pragma code-name ("AICODE")
#pragma rodata-name ("AIRODATA")
#pragma bss-name ("AIBSS")
#define ai_move ai_move_banked
#define ai_reset ai_reset_banked
#endif

#define FLAG_VALUE      2000
#define BACKTRACK       20          // penalty for undoing the previous move

// what each piece is worth to its army
static const int16_t value[PIECE_TYPES] = {
    400, 200, 100, 75, 45, 30, 15, 25, 10, 100, 20, 1000,
};

static uint8_t own;                     // CELL_BLUE or 0: the army to move
static uint8_t hidden[PIECE_TYPES];     // the enemy's unrevealed pieces per rank
static uint8_t hidden_mobile;
static int16_t risk[PIECE_TYPES];       // expected loss next to a hidden enemy piece
static uint8_t last_from[2], last_to[2]; // independent history for each army
static uint8_t targets[MAX_TARGETS];
/* All private state lives with the code in bank 23 on the X16. Goals are
 * square-indexed, transferred after our chosen move, and validated next turn. */
static uint8_t goals[2][SQUARES];
static uint8_t distance[SQUARES], queue[SQUARES];
static int16_t worth[PIECE_TYPES];
static int16_t attack[PIECE_TYPES][2];
static uint8_t flag_square, flag_danger;
static const int8_t step[4] = {-BOARD_SIZE, 1, BOARD_SIZE, -1};

static uint8_t adjacent(uint8_t sq, uint8_t dir) {
    uint8_t nb;
    if((dir == 1 && SQUARE_COL(sq) == BOARD_SIZE - 1) ||
       (dir == 3 && SQUARE_COL(sq) == 0)) return NOWHERE;
    nb = sq + step[dir];
    return nb < SQUARES ? nb : NOWHERE;
}

static uint8_t manhattan(uint8_t a, uint8_t b) {
    int16_t r = (int16_t)SQUARE_ROW(a) - SQUARE_ROW(b);
    int16_t c = (int16_t)SQUARE_COL(a) - SQUARE_COL(b);
    return (r < 0 ? -r : r) + (c < 0 ? -c : c);
}

/**
 * @brief The gain when a piece of type a attacks one of type d
 */
static int16_t gain(uint8_t a, uint8_t d) {
    if(d == PIECE_FLAG) return FLAG_VALUE;
    switch(rules_battle(a, d)) {
        case BATTLE_ATTACKER: return worth[d];
        case BATTLE_DEFENDER: return -worth[a];
        default:              return worth[d] - worth[a];
    }
}

static uint8_t enemy(uint8_t cell) {
    return IS_PIECE(cell) && (cell & CELL_BLUE) != own;
}

/**
 * @brief Count the enemy's hidden ranks and the risk they pose to each rank
 */
static void survey(const uint8_t* lost) {
    uint8_t sq, cell, a, t, seen[PIECE_TYPES];
    int32_t loss;

    for(t=0; t<PIECE_TYPES; t++) seen[t] = 0;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(enemy(cell) && (cell & CELL_REVEALED)) seen[PIECE_TYPE(cell)]++;
    }
    hidden_mobile = 0;
    for(t=0; t<PIECE_TYPES; t++) {
        hidden[t] = piece_counts[t] > lost[t] + seen[t] ? piece_counts[t] - lost[t] - seen[t] : 0;
        if(t < PIECE_BOMB || (t == PIECE_BOMB && (game_rules & RULE_MOVING_BOMBS)) ||
           (t == PIECE_FLAG && (game_rules & RULE_MOVING_FLAG))) hidden_mobile += hidden[t];
    }
    memcpy(worth, value, sizeof(worth));
    /* Scarce specialists retain their jobs until the opposing threat is gone. */
    if(hidden[PIECE_BOMB] + seen[PIECE_BOMB]) worth[PIECE_MINER] = 40;
    if(!(hidden[PIECE_MARSHAL] + seen[PIECE_MARSHAL])) worth[PIECE_SPY] = 15;
    flag_square = NOWHERE;
    for(sq=0; sq<SQUARES; sq++) {
        if(IS_PIECE(board[sq]) && (board[sq] & CELL_BLUE) == own &&
           PIECE_TYPE(board[sq]) == PIECE_FLAG) flag_square = sq;
    }
    // a hidden enemy piece next to our piece a may attack it
    for(a=0; a<PIECE_TYPES; a++) {
        loss = 0;
        for(t=0; t<PIECE_BOMB; t++) {
            if(rules_battle(t, a) != BATTLE_DEFENDER) loss += (int32_t)hidden[t] * worth[a];
        }
        risk[a] = hidden_mobile ? loss / (int32_t)hidden_mobile : 0;
    }
}

/**
 * @brief Expected gain of attacking a hidden enemy piece
 */
static int16_t expected(uint8_t a, uint8_t moved) {
    int32_t sum = 0;
    uint8_t t, n = 0;

    for(t=0; t<PIECE_TYPES; t++) {
        if(moved && t == PIECE_BOMB && !(game_rules & RULE_MOVING_BOMBS)) continue;
        if(moved && t == PIECE_FLAG && !(game_rules & RULE_MOVING_FLAG)) continue;
        sum += (int32_t)hidden[t] * gain(a, t);
        n += hidden[t];
    }
    // cc65 divides a long by an unsigned char without sign: cast the count
    return n ? sum / (int32_t)n : 0;
}

/**
 * @brief The worst loss a piece of type a risks on square sq
 */
static int16_t threat(uint8_t sq, uint8_t a) {
    int16_t worst = 0, loss;
    uint8_t dir, nb, cell, t, range;

    for(dir=0; dir<4; dir++) {
        nb = sq;
        for(range=1; ; range++) {
            nb = adjacent(nb, dir);
            if(nb == NOWHERE) break;
            cell = board[nb];
            if(cell == CELL_EMPTY) continue;
            if(!enemy(cell)) break;
            loss = 0;
            if(cell & CELL_REVEALED) {
                t = PIECE_TYPE(cell);
                /* Only scouts can attack along a clear ray beyond one step.
                 * Moving bombs and flags still cannot attack. */
                if(t < PIECE_BOMB && (range == 1 || t == PIECE_SCOUT)) {
                    switch(rules_battle(t, a)) {
                        case BATTLE_ATTACKER: loss = worth[a]; break;
                        case BATTLE_BOTH: loss = worth[a] - worth[t]; break;
                    }
                }
            } else if(range == 1) {
                loss = cell & CELL_MOVED ? risk[a] : risk[a] / 2;
            }
            if(loss > worst) worst = loss;
            break;
        }
    }
    return worst;
}

/* Count confirmed immediate flag attacks, including long scout rays. Hidden
 * neighbors are handled by the ordinary risk/defence terms, without pretending
 * to know their identities. The two-squares rule may make this conservative. */
static uint8_t flag_threats(void) {
    uint8_t dir, nb, cell, range, count = 0;
    if(flag_square == NOWHERE) return 0;
    for(dir=0; dir<4; dir++) {
        nb = flag_square;
        for(range=1; ; range++) {
            nb = adjacent(nb, dir);
            if(nb == NOWHERE) break;
            cell = board[nb];
            if(cell == CELL_EMPTY) continue;
            if(enemy(cell) && (cell & CELL_REVEALED) && PIECE_TYPE(cell) < PIECE_BOMB &&
               (range == 1 || PIECE_TYPE(cell) == PIECE_SCOUT)) count++;
            break;
        }
    }
    return count;
}

/* Reverse BFS: empty squares are traversable, the enemy goal is an endpoint,
 * and our source is allowed. Other enemies are endpoints, never transit
 * squares; friendly pieces and lakes block the route. */
static void route(uint8_t goal, uint8_t from) {
    uint8_t head = 0, tail = 0, sq, nb, dir;
    memset(distance, NOWHERE, sizeof(distance));
    distance[goal] = 0;
    queue[tail++] = goal;
    while(head < tail) {
        sq = queue[head++];
        if(sq != goal && enemy(board[sq])) continue;
        for(dir=0; dir<4; dir++) {
            nb = adjacent(sq, dir);
            if(nb == NOWHERE || distance[nb] != NOWHERE) continue;
            if(board[nb] != CELL_EMPTY && !enemy(board[nb]) && nb != from) continue;
            distance[nb] = distance[sq] + 1;
            queue[tail++] = nb;
        }
    }
}

/* Goals use public knowledge only. Keep a small persistence bonus, but allow
 * newly revealed valuable targets and threats to our flag to replace them. */
static uint8_t plan(uint8_t from) {
    uint8_t sq, cell, a = PIECE_TYPE(board[from]), best = NOWHERE;
    uint8_t previous = goals[own ? 1 : 0][from];
    int16_t utility, g, best_score = -32767;
    route(from, from);
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!enemy(cell) || distance[sq] == NOWHERE) continue;
        g = cell & CELL_REVEALED ? gain(a, PIECE_TYPE(cell)) : attack[a][!!(cell & CELL_MOVED)];
        utility = 24 + g / 4;
        if(!(cell & CELL_REVEALED) && a >= PIECE_SERGEANT) utility += 12;
        if(g < -worth[a] / 2) continue;
        if(flag_square != NOWHERE && manhattan(sq, flag_square) <= 2 &&
           (!(cell & CELL_REVEALED) || PIECE_TYPE(cell) < PIECE_BOMB)) utility += 40;
        utility -= (int16_t)distance[sq] * 3;
        if(sq == previous) utility += 8;
        if(utility > best_score) { best_score = utility; best = sq; }
    }
    goals[own ? 1 : 0][from] = best;
    if(best != NOWHERE) route(best, from);
    else memset(distance, NOWHERE, sizeof(distance));
    return best;
}

static int16_t score(uint8_t from, uint8_t to) {
    uint8_t target = board[to], a = PIECE_TYPE(board[from]);
    int16_t s;

    uint8_t moving = board[from], outcome, saved_flag = flag_square;
    int16_t defence;
    int16_t old_danger = threat(from, a), new_danger;

    /* Winning moves take precedence over every material/positional term. */
    if((target != CELL_EMPTY && (target & CELL_REVEALED) &&
        PIECE_TYPE(target) == PIECE_FLAG) ||
       (a == PIECE_FLAG && (game_rules & RULE_MOVING_FLAG) &&
        SQUARE_ROW(to) == (own ? BOARD_SIZE - 1 : 0))) return 30000;

    /* Evaluate danger on the resulting occupancy: vacating our source can
     * open a scout ray. Do not call rules_apply or alter rule/history state. */
    if(target == CELL_EMPTY) outcome = BATTLE_ATTACKER;
    else if(target & CELL_REVEALED) outcome = rules_battle(a, PIECE_TYPE(target));
    else outcome = BATTLE_ATTACKER; /* survival branch for an uncertain attack */
    board[from] = CELL_EMPTY;
    if(outcome == BATTLE_ATTACKER) board[to] = moving | CELL_MOVED;
    else if(outcome == BATTLE_BOTH) board[to] = CELL_EMPTY;
    new_danger = outcome == BATTLE_ATTACKER ? threat(to, a) : 0;
    if(a == PIECE_FLAG && outcome == BATTLE_ATTACKER) flag_square = to;
    defence = ((int16_t)flag_danger - flag_threats()) * 900;
    flag_square = saved_flag;
    /* Concealed combat is not guaranteed to remove a confirmed threat. */
    if(target != CELL_EMPTY && !(target & CELL_REVEALED)) defence /= 4;
    board[from] = moving;
    board[to] = target;

    if(target == CELL_EMPTY) {
        s = ((int16_t)SQUARE_ROW(to) - SQUARE_ROW(from)) * (own ? 4 : -4);
        s += old_danger - new_danger;
        if(distance[from] != NOWHERE && distance[to] != NOWHERE)
            s += ((int16_t)distance[from] - distance[to]) * 6;
    } else {
        s = target & CELL_REVEALED ? gain(a, PIECE_TYPE(target)) : attack[a][!!(target & CELL_MOVED)];
        s -= new_danger / 2;
        /* Cheap probes purchase useful rank information. */
        if(!(target & CELL_REVEALED) && a >= PIECE_SERGEANT && a < PIECE_BOMB) s += 10;
        if(flag_square != NOWHERE && manhattan(to, flag_square) <= 2 &&
           s >= 0) s += 40;
    }
    s += defence;
    if(a == PIECE_FLAG && (game_rules & RULE_MOVING_FLAG)) {
        if(SQUARE_ROW(to) == (own ? BOARD_SIZE - 1 : 0)) s += FLAG_VALUE;
        else s += ((int16_t)SQUARE_ROW(to) - SQUARE_ROW(from)) * (own ? 12 : -12);
    }
    if((game_rules & RULE_RESCUE) && a < PIECE_BOMB && a != PIECE_SCOUT && rules_rescues[own ? 1 : 0] < 2) {
        uint8_t t;
        for(t=0; t<PIECE_BOMB; t++) {
            if(rules_lost[own ? 1 : 0][t]) {
                s += ((int16_t)SQUARE_ROW(to) - SQUARE_ROW(from)) * (own ? 8 : -8);
                if(SQUARE_ROW(to) == (own ? BOARD_SIZE - 1 : 0)) s += worth[t];
                break;
            }
        }
    }
    if(from == last_to[own ? 1 : 0] && to == last_from[own ? 1 : 0]) s -= BACKTRACK;
    return s + (random_next() & 7);
}

void ai_reset(void) {
    memset(goals, NOWHERE, sizeof(goals));
    last_from[0] = last_from[1] = last_to[0] = last_to[1] = NOWHERE;
}

void ai_move(uint8_t army, const uint8_t* lost, uint8_t* from, uint8_t* to) {
    uint8_t sq, i, n, cell;
    int16_t s, best = -32767;

    own = army;
    *from = *to = NOWHERE;
    survey(lost);
    flag_danger = flag_threats();
    for(sq=0; sq<PIECE_TYPES; sq++) {
        attack[sq][0] = expected(sq, 0);
        attack[sq][1] = expected(sq, 1);
    }
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!IS_PIECE(cell) || (cell & CELL_BLUE) != own) continue;
        n = rules_targets(sq, targets);
        if(n) plan(sq);
        for(i=0; i<n; i++) {
            s = score(sq, targets[i]);
#ifdef AI_TRACE
            ai_trace(sq, targets[i], s);
#endif
            if(s > best) {
                best = s;
                *from = sq;
                *to = targets[i];
            }
        }
    }
    if(*from != NOWHERE) {
        goals[own ? 1 : 0][*to] = goals[own ? 1 : 0][*from];
        goals[own ? 1 : 0][*from] = NOWHERE;
    }
    last_from[own ? 1 : 0] = *from;
    last_to[own ? 1 : 0] = *to;
}
