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
#if defined(AI_TEMPLATE_PRIOR_Q24) || defined(AI_TEMPLATE_PRIOR_Q24_CACHE)
#include "ai_template.h"
#if defined(AI_BELIEF_PRIORS) || defined(AI_BACKROW_PRIOR) || !defined(AI_MEMORY)
#error Template source prior requires memory and its own numerical interface
#endif
#endif
#include "board.h"
#include "random.h"
#include "rules.h"
#ifdef AI_STUDENT_CONTEXT
#include "ai_student.h"
#endif
#ifdef AI_MEMORY
#include "ai_memory.h"
#endif
#ifdef AI_MISSIONS
#include "ai_mission.h"
#endif
#if defined(AI_BELIEF_PRIORS) && defined(AI_BACKROW_PRIOR)
#error External priors and compact backrow priors are distinct policies
#endif

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
#ifdef AI_EXACT_CONTACT_RISK
static uint8_t exact_hidden_unmoved;
#endif
#ifdef AI_OCCUPANCY_BELIEFS
static uint8_t hidden_moved;
#endif
static int16_t risk[PIECE_TYPES];       // expected loss next to a hidden enemy piece
static uint8_t last_from[2], last_to[2]; // independent history for each army
static uint8_t quiet_turns[2], previous_count[2];
static uint8_t targets[MAX_TARGETS];
/* All private state lives with the code in bank 23 on the X16. Goals are
 * square-indexed, transferred after our chosen move, and validated next turn. */
static uint8_t goals[2][SQUARES];
#ifdef AI_TASK_ASSIGNMENT
/* Per-decision scratch only. Persistent assignments use the ordinary goals.
 * Keep the best existing primary pursuer; reallocate one redundant combat
 * unit to a profitable, previously uncovered, disclosed mobile objective. */
static int16_t task_utility[ARMY_SIZE][ARMY_SIZE], task_base_utility[ARMY_SIZE];
static uint8_t task_column[SQUARES], task_target[ARMY_SIZE], task_source[ARMY_SIZE];
static uint8_t task_goal[ARMY_SIZE], task_primary[ARMY_SIZE];
static uint8_t task_count, task_targets, task_row, task_collecting;
static uint8_t task_reassigned_from, task_reassigned_to;
#endif
#ifdef AI_DIAGNOSTICS
static uint8_t diagnostic_goals[SQUARES];
static void ai_diagnostic_prepare(uint8_t army) {
    memcpy(diagnostic_goals, goals[army ? 1 : 0], SQUARES);
}
void ai_diagnostic_choice(uint8_t army, uint8_t from, uint8_t to) {
    uint8_t index = army ? 1 : 0;
    memcpy(goals[index], diagnostic_goals, SQUARES);
    goals[index][to] = goals[index][from];
    goals[index][from] = NOWHERE;
    last_from[index] = from;
    last_to[index] = to;
}
#endif
static uint8_t distance[SQUARES], queue[SQUARES];
static int16_t worth[PIECE_TYPES];
static int16_t attack[PIECE_TYPES][2];
#ifdef AI_BELIEF_PRIORS
static uint16_t belief_flag[SQUARES], belief_bomb[SQUARES];
/* Zero means disabled; otherwise owner|1 prevents another army from using it. */
static uint8_t belief_owner;
uint8_t ai_belief_priors_set(uint8_t army, const uint16_t* flag_q12, const uint16_t* bomb_q12) {
    unsigned square;
    if((army!=0 && army!=CELL_BLUE) || !flag_q12 || !bomb_q12) return 0;
    for(square=0;square<SQUARES;square++)
        if(flag_q12[square]>AI_BELIEF_ONE || bomb_q12[square]>AI_BELIEF_ONE ||
           flag_q12[square]+bomb_q12[square]>AI_BELIEF_ONE) return 0;
    memcpy(belief_flag,flag_q12,sizeof(belief_flag));
    memcpy(belief_bomb,bomb_q12,sizeof(belief_bomb));
    belief_owner=army|1;
    return 1;
}
void ai_belief_priors_clear(void) {
    memset(belief_flag,0,sizeof(belief_flag));
    memset(belief_bomb,0,sizeof(belief_bomb));
    belief_owner=0;
}
uint8_t ai_belief_priors_valid(void) { return belief_owner!=0; }
#endif
static int16_t combat_gain[PIECE_TYPES][PIECE_TYPES], source_danger;
static uint8_t combat_result[PIECE_TYPES][PIECE_TYPES];
static uint8_t flag_square, flag_danger;
#ifdef AI_PRIORITIES
/* A lexicographic decision: tactical/strategic obligation first; the existing
 * evaluator (including its learned correction) breaks ties within that class.
 * These are per-decision scratch values, not persistent or hidden-rank state. */
static uint8_t candidate_priority;
#endif
#ifdef AI_PURPOSEFUL_PROBES
static uint8_t discovery[SQUARES];
/* Information matters when a nearby friendly piece would attack some possible
 * ranks and avoid others. Cache that decision uncertainty from public counts. */
static void prepare_discovery(void) {
    uint8_t sq, ally, t, cell, count, wins, other, amount;
    int16_t bonus;
    memset(discovery, 0, sizeof(discovery));
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!IS_PIECE(cell) || (cell & CELL_BLUE) == own || (cell & CELL_REVEALED)) continue;
        for(ally=0; ally<SQUARES; ally++) {
            if(!IS_PIECE(board[ally]) || (board[ally] & CELL_BLUE) != own ||
               PIECE_TYPE(board[ally]) >= PIECE_SCOUT ||
               (ally/10 > sq/10 ? ally/10-sq/10 : sq/10-ally/10) +
               (ally%10 > sq%10 ? ally%10-sq%10 : sq%10-ally%10) > 3) continue;
            count = wins = 0;
            for(t=0; t<PIECE_TYPES; t++) {
                if((cell & CELL_MOVED) &&
                   ((t == PIECE_BOMB && !(game_rules & RULE_MOVING_BOMBS)) ||
                    (t == PIECE_FLAG && !(game_rules & RULE_MOVING_FLAG)))) continue;
                count += hidden[t];
                if(rules_battle(PIECE_TYPE(board[ally]), t) == BATTLE_ATTACKER) wins += hidden[t];
            }
            if(!count) continue;
            other = count-wins; amount = wins < other ? wins : other;
            bonus = (int16_t)amount * value[PIECE_TYPE(board[ally])] / count;
            if(bonus > 80) bonus = 80;
            if(bonus > discovery[sq]) discovery[sq] = bonus;
        }
    }
}
#endif
#define SHORTLIST 6
static uint8_t shortlist_from[SHORTLIST], shortlist_to[SHORTLIST], shortlist_count;
static int16_t shortlist_score[SHORTLIST], shortlist_discount[SHORTLIST], danger_discount, counter_gain[PIECE_TYPES][2];
/* Board geometry is constant; avoid division/modulo in every flood/ray step. */
static const uint8_t neighbors[SQUARES][4] = {
    {255, 1, 10, 255},
    {255, 2, 11, 0},
    {255, 3, 12, 1},
    {255, 4, 13, 2},
    {255, 5, 14, 3},
    {255, 6, 15, 4},
    {255, 7, 16, 5},
    {255, 8, 17, 6},
    {255, 9, 18, 7},
    {255, 255, 19, 8},
    {0, 11, 20, 255},
    {1, 12, 21, 10},
    {2, 13, 22, 11},
    {3, 14, 23, 12},
    {4, 15, 24, 13},
    {5, 16, 25, 14},
    {6, 17, 26, 15},
    {7, 18, 27, 16},
    {8, 19, 28, 17},
    {9, 255, 29, 18},
    {10, 21, 30, 255},
    {11, 22, 31, 20},
    {12, 23, 32, 21},
    {13, 24, 33, 22},
    {14, 25, 34, 23},
    {15, 26, 35, 24},
    {16, 27, 36, 25},
    {17, 28, 37, 26},
    {18, 29, 38, 27},
    {19, 255, 39, 28},
    {20, 31, 40, 255},
    {21, 32, 41, 30},
    {22, 33, 42, 31},
    {23, 34, 43, 32},
    {24, 35, 44, 33},
    {25, 36, 45, 34},
    {26, 37, 46, 35},
    {27, 38, 47, 36},
    {28, 39, 48, 37},
    {29, 255, 49, 38},
    {30, 41, 50, 255},
    {31, 42, 51, 40},
    {32, 43, 52, 41},
    {33, 44, 53, 42},
    {34, 45, 54, 43},
    {35, 46, 55, 44},
    {36, 47, 56, 45},
    {37, 48, 57, 46},
    {38, 49, 58, 47},
    {39, 255, 59, 48},
    {40, 51, 60, 255},
    {41, 52, 61, 50},
    {42, 53, 62, 51},
    {43, 54, 63, 52},
    {44, 55, 64, 53},
    {45, 56, 65, 54},
    {46, 57, 66, 55},
    {47, 58, 67, 56},
    {48, 59, 68, 57},
    {49, 255, 69, 58},
    {50, 61, 70, 255},
    {51, 62, 71, 60},
    {52, 63, 72, 61},
    {53, 64, 73, 62},
    {54, 65, 74, 63},
    {55, 66, 75, 64},
    {56, 67, 76, 65},
    {57, 68, 77, 66},
    {58, 69, 78, 67},
    {59, 255, 79, 68},
    {60, 71, 80, 255},
    {61, 72, 81, 70},
    {62, 73, 82, 71},
    {63, 74, 83, 72},
    {64, 75, 84, 73},
    {65, 76, 85, 74},
    {66, 77, 86, 75},
    {67, 78, 87, 76},
    {68, 79, 88, 77},
    {69, 255, 89, 78},
    {70, 81, 90, 255},
    {71, 82, 91, 80},
    {72, 83, 92, 81},
    {73, 84, 93, 82},
    {74, 85, 94, 83},
    {75, 86, 95, 84},
    {76, 87, 96, 85},
    {77, 88, 97, 86},
    {78, 89, 98, 87},
    {79, 255, 99, 88},
    {80, 91, 255, 255},
    {81, 92, 255, 90},
    {82, 93, 255, 91},
    {83, 94, 255, 92},
    {84, 95, 255, 93},
    {85, 96, 255, 94},
    {86, 97, 255, 95},
    {87, 98, 255, 96},
    {88, 99, 255, 97},
    {89, 255, 255, 98},
};

#define adjacent(sq, dir) neighbors[sq][dir]

#ifdef AI_LINKED_SCOUTING
static int16_t gain(uint8_t a, uint8_t d);
/* A Scout buys a decision, not information for its own sake. Only count
 * surviving defenders: when the Scout wins or exchanges, no follow-up rank
 * decision remains. The other actor must actually be able to attack now;
 * proximity through a lake or another piece is insufficient. This is an
 * opportunity value, not a promise the opponent will leave the target there. */
static uint8_t linked_information[SQUARES];
static void prepare_linked_scouting(void) {
    uint8_t target, cell, dir, ally, type, rank, n, i, total;
    uint8_t options[MAX_TARGETS];
    int16_t payoff, credit;
    int32_t informed, blind;
    memset(linked_information, 0, sizeof(linked_information));
    if(game_rules || ai_difficulty != AI_NORMAL) return;
    for(target=0; target<SQUARES; target++) {
        cell = board[target];
        if(!IS_PIECE(cell) || (cell & CELL_BLUE) == own || (cell & CELL_REVEALED)) continue;
        total = 0;
        for(rank=0; rank<PIECE_TYPES; rank++) {
            if((cell & CELL_MOVED) && rank >= PIECE_BOMB) continue;
            total += hidden[rank];
        }
        if(!total) continue;
        for(dir=0; dir<4; dir++) {
            ally = adjacent(target, dir);
            if(ally == NOWHERE || !IS_PIECE(board[ally]) || (board[ally] & CELL_BLUE) != own) continue;
            type = PIECE_TYPE(board[ally]);
            if(type >= PIECE_BOMB || type == PIECE_SCOUT) continue;
            n = rules_targets(ally, options);
            for(i=0; i<n && options[i] != target; i++);
            if(i == n) continue;
            informed = blind = 0;
            for(rank=0; rank<PIECE_TYPES; rank++) {
                if(((cell & CELL_MOVED) && rank >= PIECE_BOMB) ||
                   combat_result[PIECE_SCOUT][rank] != BATTLE_DEFENDER) continue;
                payoff = gain(type, rank);
                blind += (int32_t)hidden[rank] * payoff;
                if(payoff > 0) informed += (int32_t)hidden[rank] * payoff;
            }
            if(blind < 0) blind = 0;
            credit = (informed - blind) / total;
            if(credit < worth[PIECE_SCOUT]) continue;
            if(credit > 80) credit = 80;
            if(credit > linked_information[target]) linked_information[target] = credit;
        }
    }
}
#ifdef AI_TEST
uint8_t ai_test_linked_information(uint8_t square) { return linked_information[square]; }
#endif
#endif

static uint8_t manhattan(uint8_t a, uint8_t b) {
    int16_t r = (int16_t)SQUARE_ROW(a) - SQUARE_ROW(b);
    int16_t c = (int16_t)SQUARE_COL(a) - SQUARE_COL(b);
    return (r < 0 ? -r : r) + (c < 0 ? -c : c);
}

/**
 * @brief The gain when a piece of type a attacks one of type d
 */
static int16_t gain(uint8_t a, uint8_t d) {
    return combat_gain[a][d];
}

static uint8_t enemy(uint8_t cell) {
    return IS_PIECE(cell) && (cell & CELL_BLUE) != own;
}

/**
 * @brief Count the enemy's hidden ranks and the risk they pose to each rank
 */
static void survey(const uint8_t* lost) {
    uint8_t sq, cell, a, t, count = 0, seen[PIECE_TYPES];
    int32_t loss;

    for(t=0; t<PIECE_TYPES; t++) seen[t] = 0;
#ifdef AI_OCCUPANCY_BELIEFS
    hidden_moved = 0;
#endif
#ifdef AI_EXACT_CONTACT_RISK
    exact_hidden_unmoved = 0;
#endif
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(IS_PIECE(cell)) count++;
        if(enemy(cell) && (cell & CELL_REVEALED)) seen[PIECE_TYPE(cell)]++;
#ifdef AI_OCCUPANCY_BELIEFS
        if(enemy(cell) && !(cell & CELL_REVEALED) && (cell & CELL_MOVED)) hidden_moved++;
#endif
#ifdef AI_EXACT_CONTACT_RISK
        if(enemy(cell) && !(cell & (CELL_REVEALED | CELL_MOVED))) exact_hidden_unmoved++;
#endif
    }
    a = own ? 1 : 0;
    if(count != previous_count[a]) quiet_turns[a] = 0;
    else if(quiet_turns[a] < 128) quiet_turns[a]++;
    previous_count[a] = count;
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
#ifdef AI_CAPABILITY_VALUES
    /* A rank that defeats every remaining mobile enemy is a winning resource,
     * even if its printed rank would normally have a modest material value. */
    for(a=PIECE_GENERAL; a<=PIECE_SERGEANT; a++) {
        uint8_t threat_count = 0;
        for(t=0; t<=a; t++) threat_count += hidden[t] + seen[t];
        if(!threat_count) worth[a] = value[PIECE_MARSHAL];
    }
#endif
    flag_square = NOWHERE;
    for(sq=0; sq<SQUARES; sq++) {
        if(IS_PIECE(board[sq]) && (board[sq] & CELL_BLUE) == own &&
           PIECE_TYPE(board[sq]) == PIECE_FLAG) flag_square = sq;
    }
    /* Cache rank matchups once, including the selected combat variants. */
    for(a=0; a<PIECE_TYPES; a++) {
        for(t=0; t<PIECE_TYPES; t++) {
            combat_result[a][t] = rules_battle(a, t);
            combat_gain[a][t] = t == PIECE_FLAG ? FLAG_VALUE :
                combat_result[a][t] == BATTLE_ATTACKER ? worth[t] :
                combat_result[a][t] == BATTLE_DEFENDER ? -worth[a] : worth[t] - worth[a];
        }
    }
    // a hidden enemy piece next to our piece a may attack it
    for(a=0; a<PIECE_TYPES; a++) {
        loss = 0;
        for(t=0; t<PIECE_BOMB; t++) {
            if(combat_result[t][a] != BATTLE_DEFENDER) loss += (int32_t)hidden[t] * worth[a];
        }
        risk[a] = hidden_mobile ? loss / (int32_t)hidden_mobile : 0;
    }
}

#ifdef AI_EXACT_CONTACT_RISK
/* Exact inclusion-exclusion under a uniform remaining-army prior, evaluated
 * with Q22 arithmetic. A contact kind has bit0=far and bit1=publicly moved.
 * Uniform means conditional on rank counts and moved/unmoved status only;
 * behavioral history and narrower candidate masks are not modeled here.
 * The root inventory stays fixed while score() changes candidate occupancy. */
#define CONTACT_ONE 4194304UL
static uint32_t exact_contact_probability(uint8_t a, uint8_t count, const uint8_t* kind) {
    uint8_t mask, i, n, f, b, bits, dangerous = 0, immobile;
    uint32_t p;
    int32_t total = 0;
    if(!count || !hidden_mobile) return 0;
    immobile = hidden[PIECE_BOMB] + hidden[PIECE_FLAG];
    if(exact_hidden_unmoved < immobile) return 0; /* inconsistent diagnostic input */
    for(i=0;i<PIECE_BOMB;i++)
        if(combat_result[i][a] == BATTLE_ATTACKER) dangerous += hidden[i];
    for(mask=1;mask < (1u << count);mask++) {
        n=f=b=bits=0;
        for(i=0;i<count;i++) if(mask & (1u << i)) {
            bits++;
            if(kind[i]&1) f++; else n++;
            if(!(kind[i]&2)) b++;
        }
        if(n+f > hidden_mobile || n+f > dangerous ||
           f > hidden[PIECE_SCOUT] || b > exact_hidden_unmoved-immobile ||
           (f && combat_result[PIECE_SCOUT][a] != BATTLE_ATTACKER)) continue;
        p=CONTACT_ONE;
        for(i=0;i<b;i++)
            p=p*(uint32_t)(exact_hidden_unmoved-immobile-i)/(exact_hidden_unmoved-i);
        for(i=0;i<f;i++)
            p=p*(uint32_t)(hidden[PIECE_SCOUT]-i)/(hidden_mobile-i);
        for(i=0;i<n;i++)
            p=p*(uint32_t)(dangerous-f-i)/(hidden_mobile-f-i);
        if(bits&1) total+=(int32_t)p; else total-=(int32_t)p;
    }
    if(total < 0) return 0;
    if((uint32_t)total > CONTACT_ONE) return CONTACT_ONE;
    return (uint32_t)total;
}

static int16_t exact_contact_threat(uint8_t sq, uint8_t a) {
    uint8_t dir, nb, cell, t, range, count=0, kind[4];
    uint32_t probability;
    for(dir=0;dir<4;dir++) {
        nb=sq;
        for(range=1; ;range++) {
            nb=adjacent(nb,dir);
            if(nb == NOWHERE) break;
            cell=board[nb];
            if(cell == CELL_EMPTY) continue;
            if(enemy(cell)) {
                if(cell & CELL_REVEALED) {
                    t=PIECE_TYPE(cell);
                    if(t < PIECE_BOMB && (range == 1 || t == PIECE_SCOUT) &&
                       combat_result[t][a] == BATTLE_ATTACKER) return worth[a];
                } else if(range == 1 || combat_result[PIECE_SCOUT][a] == BATTLE_ATTACKER) {
                    kind[count++]=(range > 1 ? 1 : 0) | (cell & CELL_MOVED ? 2 : 0);
                }
            }
            break;
        }
    }
    probability=exact_contact_probability(a,count,kind);
    /* worth is at most1000 and Q22 keeps this product within uint32_t. */
    return (int16_t)((probability*(uint32_t)worth[a]+CONTACT_ONE/2)/CONTACT_ONE);
}
#endif

/**
 * @brief Expected gain of attacking a hidden enemy piece
 */
static int16_t expected(uint8_t a, uint8_t moved) {
    int32_t sum = 0;
    uint8_t t, n = 0;
#ifdef AI_OCCUPANCY_BELIEFS
    uint16_t weight, total = 0;
    uint8_t mobile, remaining_mobile = hidden_mobile > hidden_moved ? hidden_mobile-hidden_moved : 0;
    if(!moved && hidden_mobile) {
        /* Moved unknown pieces consume mobile ranks. Immobile ranks therefore
         * concentrate in unmoved slots under a uniform consistent assignment. */
        for(t=0; t<PIECE_TYPES; t++) {
            mobile = t < PIECE_BOMB || (t == PIECE_BOMB && (game_rules & RULE_MOVING_BOMBS)) ||
                     (t == PIECE_FLAG && (game_rules & RULE_MOVING_FLAG));
            weight = (uint16_t)hidden[t] * (mobile ? remaining_mobile : hidden_mobile);
            sum += (int32_t)weight * gain(a, t); total += weight;
        }
        if(total) return sum / (int32_t)total;
    }
#endif

    for(t=0; t<PIECE_TYPES; t++) {
        if(moved && t == PIECE_BOMB && !(game_rules & RULE_MOVING_BOMBS)) continue;
        if(moved && t == PIECE_FLAG && !(game_rules & RULE_MOVING_FLAG)) continue;
        sum += (int32_t)hidden[t] * gain(a, t);
        n += hidden[t];
    }
    // cc65 divides a long by an unsigned char without sign: cast the count
    return n ? sum / (int32_t)n : 0;
}

#ifdef AI_TEMPLATE_PRIOR_Q24
#ifdef BANKED_AI
#pragma code-name (push, "CODE")
#endif
static int16_t expected_at(uint8_t a,uint8_t square) {
    uint8_t cell=board[square];
    if(!game_rules && ai_difficulty==AI_NORMAL && ai_template_valid &&
       enemy(cell) && !(cell&(CELL_REVEALED|CELL_MOVED)))
        return ai_template_transfer.row[square];
    return attack[a][!!(cell&CELL_MOVED)];
}
#ifdef BANKED_AI
#pragma code-name (pop)
#endif
#elif defined(AI_BELIEF_PRIORS)
/* Exact Q12 expected gain under per-square Flag/Bomb probabilities. The
 * remaining mobile ranks are exchangeable; encounter likelihoods are not used.
 * Preserve the rational mobile mean until the final signed integer division.
 * All inputs are the mover's permitted view, public inventory and supplied
 * posterior. The hidden type nibble at an undisclosed enemy is never read. */
static int16_t expected_at(uint8_t a, uint8_t square) {
    uint16_t flag,bomb,mobile;
    uint8_t rank;
    int32_t immobile, mobile_gain=0, numerator;
    uint8_t cell=board[square];
    if(game_rules || ai_difficulty!=AI_NORMAL || belief_owner!=(own|1) ||
       !enemy(cell) || (cell&CELL_REVEALED)) return attack[a][!!(cell&CELL_MOVED)];
    if(cell&CELL_MOVED) return attack[a][1];
    flag=belief_flag[square];bomb=belief_bomb[square];
    mobile=AI_BELIEF_ONE-flag-bomb;
    immobile=(int32_t)flag*FLAG_VALUE+(int32_t)bomb*gain(a,PIECE_BOMB);
    if(!hidden_mobile) {
        /* A quantized immobile-only posterior must retain total mass one. */
        if(mobile) return attack[a][0];
        return immobile/(int32_t)AI_BELIEF_ONE;
    }
    for(rank=0;rank<PIECE_BOMB;rank++) mobile_gain+=(int32_t)hidden[rank]*gain(a,rank);
    numerator=immobile*(int32_t)hidden_mobile+(int32_t)mobile*mobile_gain;
    return numerator/((int32_t)AI_BELIEF_ONE*hidden_mobile);
}
#elif defined(AI_BACKROW_PRIOR)
/* Minimal source prior: 99% uniform armies conditional on a back-row Flag,
 * 1% uniform armies. With U unseen unmoved enemies and R on their back row,
 * Flag probability is (397 on that row, 1 elsewhere)/(U+396R).
 * Compute it from permitted occupancy/counts; no private ranks or packet.
 * Helpers remain unbanked while their AI-bank caller stays selected. */
#ifdef BANKED_AI
#pragma code-name (push, "CODE")
#pragma bss-name (push, "BSS")
#endif
static uint8_t backrow_unmoved, backrow_home;
static void prepare_backrow(void) {
    uint8_t square, cell;
    backrow_unmoved=backrow_home=0;
    for(square=0;square<SQUARES;square++) {
        cell=board[square];
        if(enemy(cell) && !(cell&(CELL_REVEALED|CELL_MOVED))) {
            backrow_unmoved++;
            if(own?square>=90:square<10) backrow_home++;
        }
    }
}
static int16_t expected_at(uint8_t a, uint8_t square) {
    uint8_t cell=board[square], nonflag;
    uint16_t flag_weight, total_weight;
    int16_t other_gain=0;
    int32_t sum;
    if(game_rules || ai_difficulty!=AI_NORMAL || !enemy(cell) ||
       (cell&(CELL_REVEALED|CELL_MOVED)) || !backrow_unmoved)
        return attack[a][!!(cell&CELL_MOVED)];
    nonflag=backrow_unmoved-hidden[PIECE_FLAG];
    if(nonflag) {
        sum=(int32_t)hidden[PIECE_BOMB]*gain(a,PIECE_BOMB)+
            (int32_t)(nonflag-hidden[PIECE_BOMB])*attack[a][1];
        other_gain=sum/(int32_t)nonflag;
    }
    if(!hidden[PIECE_FLAG]) return other_gain;
    flag_weight=(own?square>=90:square<10)?397u:1u;
    total_weight=backrow_unmoved+396u*backrow_home;
    sum=(int32_t)flag_weight*FLAG_VALUE+
        (int32_t)(total_weight-flag_weight)*other_gain;
    return sum/(int32_t)total_weight;
}
#ifdef AI_TEST
int16_t ai_test_backrow_value(uint8_t army, const uint8_t* lost, uint8_t rank, uint8_t square) {
    uint8_t r;
    own=army;survey(lost);prepare_backrow();
    for(r=0;r<PIECE_TYPES;r++) {
        attack[r][0]=expected(r,0);attack[r][1]=expected(r,1);
    }
    return expected_at(rank,square);
}
int16_t ai_test_backrow_gain(uint8_t a, uint8_t rank) { return gain(a,rank); }
#endif
#ifdef BANKED_AI
#pragma bss-name (pop)
#pragma code-name (pop)
#endif
#endif

/**
 * @brief The worst loss a piece of type a risks on square sq
 */
static int16_t threat(uint8_t sq, uint8_t a) {
    int16_t worst = 0, loss;
    uint8_t dir, nb, cell, t, range;

#ifdef AI_EXACT_CONTACT_RISK
    if(!game_rules) return exact_contact_threat(sq,a);
#endif

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
                    switch(combat_result[t][a]) {
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
#ifdef AI_PUBLIC_FLAG_THREATS
            /* In Classic, a public move proves an unknown piece is mobile.
             * Every mobile rank captures a Flag from an adjacent square;
             * its concealed identity is irrelevant to this certain threat.
             * Optional rules can move Bombs/Flags, so keep this Classic-only. */
            else if(!game_rules && enemy(cell) && !(cell & CELL_REVEALED) &&
                    (cell & CELL_MOVED) && range == 1) count++;
#endif
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
#if defined(AI_BELIEF_PRIORS) || defined(AI_BACKROW_PRIOR) || defined(AI_TEMPLATE_PRIOR_Q24)
        g = cell & CELL_REVEALED ? gain(a, PIECE_TYPE(cell)) : expected_at(a,sq);
#else
        g = cell & CELL_REVEALED ? gain(a, PIECE_TYPE(cell)) : attack[a][!!(cell & CELL_MOVED)];
#endif
        utility = 24 + g / 4;
        if(!(cell & CELL_REVEALED) && a >= PIECE_SERGEANT) utility += 12;
#ifdef AI_LINKED_SCOUTING
        if(!game_rules && ai_difficulty == AI_NORMAL && a == PIECE_SCOUT && !(cell & CELL_REVEALED))
            utility += (int16_t)linked_information[sq] / 4 - 12;
#endif
#ifdef AI_PURPOSEFUL_PROBES
        if(a >= PIECE_SERGEANT && a < PIECE_BOMB) utility += discovery[sq] / 4;
#endif
        if(g < -worth[a] / 2) continue;
        if(flag_square != NOWHERE && manhattan(sq, flag_square) <= 2 &&
           (!(cell & CELL_REVEALED) || PIECE_TYPE(cell) < PIECE_BOMB)) utility += 40;
        utility -= (int16_t)distance[sq] * 3;
        if(sq == previous) utility += 8;
#ifdef AI_TASK_ASSIGNMENT
        if(task_collecting && task_column[sq] != NOWHERE)
            task_utility[task_row][task_column[sq]] = utility;
#endif
        if(utility > best_score) { best_score = utility; best = sq; }
    }
    goals[own ? 1 : 0][from] = best;
#ifdef AI_TASK_ASSIGNMENT
    if(task_collecting) {
        task_base_utility[task_row] = best_score;
        task_goal[task_row] = best;
#ifdef AI_TRACE
        ai_trace_plan(from,best,previous,best == NOWHERE ? NOWHERE : distance[best],best_score);
#endif
        return best; /* scoring pass will route to the final assigned goal */
    }
#endif
    if(best != NOWHERE) route(best, from);
    else memset(distance, NOWHERE, sizeof(distance));
#ifdef AI_TRACE
    ai_trace_plan(from, best, previous, distance[from], best_score);
#endif
    return best;
}

#ifdef AI_TASK_ASSIGNMENT
static void task_assignment_prepare(void) {
    uint8_t sq,cell,n,options[MAX_TARGETS],row,col,old,primary,best_row=NOWHERE,best_col=NOWHERE;
    int16_t best_extra=0;
    task_count=task_targets=0; task_reassigned_from=task_reassigned_to=NOWHERE;
    memset(task_column,NOWHERE,sizeof(task_column));
    memset(task_primary,NOWHERE,sizeof(task_primary));
    memset(task_utility,0,sizeof(task_utility));
    /* Concealed enemy low nibbles have no authority in eligibility. */
    for(sq=0;sq<SQUARES;sq++) if(enemy(board[sq]) && (board[sq]&CELL_REVEALED) &&
            PIECE_TYPE(board[sq]) < PIECE_BOMB) {
        task_column[sq]=task_targets; task_target[task_targets++]=sq;
    }
    task_collecting=1;
    for(sq=0;sq<SQUARES;sq++) {
        cell=board[sq];
        if(!IS_PIECE(cell) || (cell&CELL_BLUE)!=own) continue;
        n=rules_targets(sq,options);
        if(!n) continue;
        task_row=task_count; task_source[task_count++]=sq;
        plan(sq);
    }
    task_collecting=0;
    /* Lock the existing highest-utility primary for every served task, with
     * original square scan order breaking ties. Unmatched goals stay intact. */
    for(row=0;row<task_count;row++) {
        old=task_goal[row];
        if(old == NOWHERE || task_column[old] == NOWHERE) continue;
        col=task_column[old]; primary=task_primary[col];
        if(primary == NOWHERE || task_base_utility[row] > task_base_utility[primary])
            task_primary[col]=row;
    }
    for(row=0;row<task_count;row++) {
        old=task_goal[row]; sq=task_source[row];
        if(old == NOWHERE || task_column[old] == NOWHERE || task_base_utility[row] <= 0 ||
           task_primary[task_column[old]] == row ||
           PIECE_TYPE(board[sq]) == PIECE_MINER || PIECE_TYPE(board[sq]) == PIECE_SPY) continue;
        for(col=0;col<task_targets;col++) {
            if(task_primary[col] != NOWHERE || task_utility[row][col] <= best_extra ||
               combat_result[PIECE_TYPE(board[sq])][PIECE_TYPE(board[task_target[col]])] != BATTLE_ATTACKER)
                continue;
            best_extra=task_utility[row][col]; best_row=row; best_col=col;
        }
    }
    if(best_row != NOWHERE) {
        task_reassigned_from=task_source[best_row]; task_reassigned_to=task_target[best_col];
        goals[own ? 1 : 0][task_reassigned_from]=task_reassigned_to;
    }
}
#endif

static int16_t score(uint8_t from, uint8_t to) {
    uint8_t target = board[to], a = PIECE_TYPE(board[from]);
    int16_t s;

    uint8_t moving = board[from], outcome, saved_flag = flag_square;
    int16_t defence;
    int16_t old_danger = source_danger, new_danger;

    danger_discount = 0;
#ifdef AI_PRIORITIES
    candidate_priority = 1;
#endif
    /* Winning moves take precedence over every material/positional term. */
    if((target != CELL_EMPTY && (target & CELL_REVEALED) &&
        PIECE_TYPE(target) == PIECE_FLAG) ||
       (a == PIECE_FLAG && (game_rules & RULE_MOVING_FLAG) &&
        SQUARE_ROW(to) == (own ? BOARD_SIZE - 1 : 0))) {
#ifdef AI_PRIORITIES
        candidate_priority = 7;
#endif
        return 30000;
    }

    /* Evaluate danger on the resulting occupancy: vacating our source can
     * open a scout ray. Do not call rules_apply or alter rule/history state. */
    if(target == CELL_EMPTY) outcome = BATTLE_ATTACKER;
    else if(target & CELL_REVEALED) outcome = combat_result[a][PIECE_TYPE(target)];
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
#ifdef AI_PRIORITIES
    if(!game_rules && ai_difficulty == AI_NORMAL) {
        /* Never infer a concealed identity to assign a guaranteed capture or
         * defence category. Uncertain attacks keep ordinary positional scoring. */
        if(defence >= 900) candidate_priority = 6;
        else if(defence >= 0 && target != CELL_EMPTY && (target & CELL_REVEALED) &&
                outcome == BATTLE_ATTACKER && gain(a, PIECE_TYPE(target)) >= new_danger)
            candidate_priority = 5;
        else if(defence >= 0 && target == CELL_EMPTY && old_danger > new_danger)
            candidate_priority = 4;
        else if(defence >= 0 && new_danger <= old_danger &&
                !(target != CELL_EMPTY && (target & CELL_REVEALED) && outcome != BATTLE_ATTACKER) &&
                ai_mission_progress_move(from, to)) candidate_priority = 3;
        else if(defence >= 0 && target == CELL_EMPTY && new_danger <= old_danger &&
                distance[from] != NOWHERE && distance[to] < distance[from]) candidate_priority = 2;
    }
#endif
#ifdef AI_TRAINING
    ai_trace_training(from, to, target == CELL_EMPTY ? 0 : new_danger / 2);
#endif

    if(target == CELL_EMPTY) {
        s = ((int16_t)SQUARE_ROW(to) - SQUARE_ROW(from)) * (own ? 4 : -4);
        s += old_danger - new_danger;
        if(distance[from] != NOWHERE && distance[to] != NOWHERE)
            s += ((int16_t)distance[from] - distance[to]) * 6;
        /* Normal increasingly favors reachable objectives during quiet play.
         * Captures/rescues reset the pressure; Hard retains reply scoring. */
        if(ai_difficulty == AI_NORMAL && distance[from] == NOWHERE)
            s -= 12 + (quiet_turns[own ? 1 : 0] >> 2);
    } else {
#if defined(AI_BELIEF_PRIORS) || defined(AI_BACKROW_PRIOR) || defined(AI_TEMPLATE_PRIOR_Q24)
        s = target & CELL_REVEALED ? gain(a, PIECE_TYPE(target)) : expected_at(a,to);
#else
        s = target & CELL_REVEALED ? gain(a, PIECE_TYPE(target)) : attack[a][!!(target & CELL_MOVED)];
#endif
        s -= new_danger / 2;
        /* Cheap probes purchase useful rank information. */
        if(!(target & CELL_REVEALED) && a >= PIECE_SERGEANT && a < PIECE_BOMB) s += 10;
#ifdef AI_LINKED_SCOUTING
        if(!game_rules && ai_difficulty == AI_NORMAL && a == PIECE_SCOUT && !(target & CELL_REVEALED))
            s += (int16_t)linked_information[to] - 10;
#endif
#ifdef AI_PURPOSEFUL_PROBES
        if(!(target & CELL_REVEALED) && a >= PIECE_SERGEANT && a < PIECE_BOMB) s += discovery[to];
#endif
        if(flag_square != NOWHERE && manhattan(to, flag_square) <= 2 &&
           s >= 0) s += 40;
    }
    danger_discount = target == CELL_EMPTY ? new_danger : new_danger / 2;
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
#ifdef AI_MISSIONS
    if(ai_difficulty != AI_EASY) s += ai_mission_score(from, to);
#endif
    return s + (random_next() & (ai_difficulty == AI_EASY ? 31 : 7));
}

/* A bounded second ply: the opponent's best material capture in this
 * hypothetical position. Known enemies use legal moves and exact combat;
 * unknown enemies use remaining-rank estimates, never the true layout. */
#ifdef AI_LOCAL_EXCHANGES
static uint8_t exchange_focus;
/* Extend only a disclosed capture of the root mover. Concealed identities
 * remain distributions; this prototype never assigns them a guessed rank. */
static uint8_t can_recapture(uint8_t from, uint8_t to) {
    uint8_t moving = board[from], target = board[to], sq, n, i, found = 0;
    uint8_t targets[MAX_TARGETS];
    board[from] = CELL_EMPTY; board[to] = moving | CELL_MOVED;
    for(sq=0; sq<SQUARES && !found; sq++) {
        if(!IS_PIECE(board[sq]) || enemy(board[sq]) ||
           rules_battle(PIECE_TYPE(board[sq]), PIECE_TYPE(moving)) != BATTLE_ATTACKER) continue;
        n = rules_targets(sq, targets);
        for(i=0; i<n; i++) if(targets[i] == to) { found = 1; break; }
    }
    board[from] = moving; board[to] = target;
    return found;
}
#endif
static int16_t reply_loss(void) {
    uint8_t sq, i, n, cell, victim, a, d;
    static uint8_t replies[MAX_TARGETS];
    int16_t cost, worst = 0;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!enemy(cell)) continue;
        n = rules_targets(sq, replies);
        for(i=0; i<n; i++) {
            if((cell & CELL_REVEALED) && PIECE_TYPE(cell) == PIECE_FLAG &&
               (game_rules & RULE_MOVING_FLAG) &&
               SQUARE_ROW(replies[i]) == ((cell & CELL_BLUE) ? BOARD_SIZE-1 : 0)) return 6000;
            victim = board[replies[i]];
            if(!IS_PIECE(victim) || (victim & CELL_BLUE) != own) continue;
            d = PIECE_TYPE(victim);
            if(cell & CELL_REVEALED) {
                a = PIECE_TYPE(cell);
                cost = d == PIECE_FLAG ? 6000 : gain(a, d);
#ifdef AI_LOCAL_EXCHANGES
                if(d != PIECE_FLAG && replies[i] == exchange_focus && cost > worst &&
                   combat_result[a][d] == BATTLE_ATTACKER && can_recapture(sq, replies[i]))
                    cost -= worth[a];
#endif
            } else cost = counter_gain[d][!!(cell & CELL_MOVED)];
            if(cost > worst) worst = cost;
        }
    }
    return worst;
}

static int16_t replies_after(uint8_t from, uint8_t to, uint8_t outcome) {
    uint8_t moving = board[from], target = board[to], saved_flag = flag_square;
    int16_t cost;
    board[from] = CELL_EMPTY;
    if(outcome == BATTLE_ATTACKER) board[to] = moving | CELL_MOVED;
    else if(outcome == BATTLE_BOTH) board[to] = CELL_EMPTY;
    if(PIECE_TYPE(moving) == PIECE_FLAG && outcome == BATTLE_ATTACKER) flag_square = to;
    cost = reply_loss();
    flag_square = saved_flag;
    board[from] = moving;
    board[to] = target;
    return cost;
}

static int16_t reply_penalty(uint8_t from, uint8_t to) {
    uint8_t target = board[to], a = PIECE_TYPE(board[from]), t, outcome, count = 0;
    static uint8_t outcomes[3];
    int32_t sum = 0;
#ifdef AI_LOCAL_EXCHANGES
    exchange_focus = to;
#endif
    if(target == CELL_EMPTY) return replies_after(from, to, BATTLE_ATTACKER);
    if(target & CELL_REVEALED) return replies_after(from, to, combat_result[a][PIECE_TYPE(target)]);
    /* For concealed combat, weight all possible occupancy outcomes. Never
     * assume that an unknown attack succeeded in order to avoid a reply. */
    memset(outcomes, 0, sizeof(outcomes));
    for(t=0; t<PIECE_TYPES; t++) {
        if((target & CELL_MOVED) &&
           ((t == PIECE_BOMB && !(game_rules & RULE_MOVING_BOMBS)) ||
            (t == PIECE_FLAG && !(game_rules & RULE_MOVING_FLAG)))) continue;
        outcomes[combat_result[a][t]] += hidden[t];
        count += hidden[t];
    }
    for(outcome=0; outcome<3; outcome++) {
        if(outcomes[outcome]) sum += (int32_t)outcomes[outcome] * replies_after(from, to, outcome);
    }
    return count ? sum / (int32_t)count : reply_loss();
}

static void retain(uint8_t from, uint8_t to, int16_t score) {
    uint8_t i = 0, j;
    while(i < shortlist_count && score <= shortlist_score[i]) i++;
    if(i == SHORTLIST) return;
    if(shortlist_count < SHORTLIST) shortlist_count++;
    for(j=shortlist_count-1; j>i; j--) {
        shortlist_score[j] = shortlist_score[j-1];
        shortlist_discount[j] = shortlist_discount[j-1];
        shortlist_from[j] = shortlist_from[j-1];
        shortlist_to[j] = shortlist_to[j-1];
    }
    shortlist_score[i] = score; shortlist_from[i] = from; shortlist_to[i] = to;
    shortlist_discount[i] = danger_discount;
}

void ai_reset(void) {
#ifdef AI_TEMPLATE_PRIOR_Q24_CACHE
    ai_template_cache_reset();
#endif
#ifdef AI_TEMPLATE_PRIOR_Q24
    ai_template_valid=0;
#endif
#ifdef AI_TASK_ASSIGNMENT
    task_collecting=0; task_reassigned_from=task_reassigned_to=NOWHERE;
#endif
#ifdef AI_BELIEF_PRIORS
    ai_belief_priors_clear();
#endif
#if defined(AI_MEMORY) && !defined(AI_MISSIONS)
    ai_memory_reset();
#endif
#ifdef AI_MISSIONS
    ai_mission_reset();
#endif
    memset(goals, NOWHERE, sizeof(goals));
    memset(quiet_turns, 0, sizeof(quiet_turns));
    memset(previous_count, 0, sizeof(previous_count));
    last_from[0] = last_from[1] = last_to[0] = last_to[1] = NOWHERE;
}

void ai_move(uint8_t army, const uint8_t* lost, uint8_t* from, uint8_t* to) {
    uint8_t sq, i, n, cell, a, t, moved, count;
    int16_t s, cost, best = -32767;
    int32_t sum;
#ifdef AI_PRIORITIES
    uint8_t best_priority = 0;
#endif

    own = army;
    *from = *to = NOWHERE;
    shortlist_count = 0;
    survey(lost);
#ifdef AI_BACKROW_PRIOR
    prepare_backrow();
#endif
#ifdef AI_LINKED_SCOUTING
    prepare_linked_scouting();
#endif
#ifdef AI_PURPOSEFUL_PROBES
    if(ai_difficulty != AI_EASY) prepare_discovery();
    else memset(discovery, 0, sizeof(discovery));
#endif
    flag_danger = flag_threats();
#ifdef AI_STUDENT_CONTEXT
    ai_student_inventory(lost);
#endif
#ifdef AI_MISSIONS
    if(ai_difficulty != AI_EASY) ai_mission_begin(army);
#endif
#ifdef AI_TEMPLATE_PRIOR_Q24
    ai_template_begin(army);
#endif
    for(sq=0; sq<PIECE_TYPES; sq++) {
        attack[sq][0] = expected(sq, 0);
        attack[sq][1] = expected(sq, 1);
    }
    if(ai_difficulty == AI_HARD) {
        for(a=0; a<PIECE_TYPES; a++) for(moved=0; moved<2; moved++) {
            sum = 0; count = 0;
            for(t=0; t<PIECE_TYPES; t++) {
                if(moved && ((t == PIECE_BOMB && !(game_rules & RULE_MOVING_BOMBS)) ||
                   (t == PIECE_FLAG && !(game_rules & RULE_MOVING_FLAG)))) continue;
                count += hidden[t];
                if(t >= PIECE_BOMB) continue; /* neither can attack */
                cost = a == PIECE_FLAG ? 6000 : gain(t, a);
                if(cost > 0) sum += (int32_t)hidden[t] * cost;
            }
            counter_gain[a][moved] = count ? sum / (int32_t)count : 0;
        }
    }
#ifdef AI_TASK_ASSIGNMENT
    if(!game_rules && ai_difficulty == AI_NORMAL) task_assignment_prepare();
#endif
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!IS_PIECE(cell) || (cell & CELL_BLUE) != own) continue;
        n = rules_targets(sq, targets);
        if(n) {
#ifdef AI_TEMPLATE_PRIOR_Q24
            ai_template_actor(PIECE_TYPE(cell));
#endif
            source_danger = threat(sq, PIECE_TYPE(cell));
            if(ai_difficulty == AI_EASY) {
                memset(distance, NOWHERE, sizeof(distance));
                goals[own ? 1 : 0][sq] = NOWHERE;
            }
#ifdef AI_TASK_ASSIGNMENT
            else if(!game_rules && ai_difficulty == AI_NORMAL) {
                if(goals[own ? 1 : 0][sq] != NOWHERE) route(goals[own ? 1 : 0][sq],sq);
                else memset(distance,NOWHERE,sizeof(distance));
            }
#endif
            else plan(sq);
        }
        for(i=0; i<n; i++) {
            s = score(sq, targets[i]);
            if(ai_difficulty == AI_HARD) retain(sq, targets[i], s);
#ifdef AI_TRACE
            ai_trace(sq, targets[i], s);
#endif
            if(
#ifdef AI_PRIORITIES
               ((!game_rules && ai_difficulty == AI_NORMAL) && candidate_priority > best_priority) ||
               ((game_rules || ai_difficulty != AI_NORMAL || candidate_priority == best_priority) &&
#endif
               s > best
#ifdef AI_PRIORITIES
               )
#endif
               ) {
                best = s;
#ifdef AI_PRIORITIES
                best_priority = candidate_priority;
#endif
                *from = sq;
                *to = targets[i];
            }
        }
    }
    if(ai_difficulty == AI_HARD) {
        best = -32767;
        for(i=0; i<shortlist_count; i++) {
            s = shortlist_score[i];
            if(s < 30000) s += shortlist_discount[i] - reply_penalty(shortlist_from[i], shortlist_to[i]);
            if(s > best) {
                best = s; *from = shortlist_from[i]; *to = shortlist_to[i];
            }
        }
    }
#ifdef AI_DIAGNOSTICS
    ai_diagnostic_prepare(own);
#endif
    if(*from != NOWHERE) {
        goals[own ? 1 : 0][*to] = goals[own ? 1 : 0][*from];
        goals[own ? 1 : 0][*from] = NOWHERE;
    }
    last_from[own ? 1 : 0] = *from;
    last_to[own ? 1 : 0] = *to;
}

#ifdef AI_TEST
#ifdef AI_OCCUPANCY_BELIEFS
int16_t ai_test_expected(uint8_t rank, uint8_t moved) {
    return expected(rank, moved);
}
#endif
#ifdef AI_PURPOSEFUL_PROBES
uint8_t ai_test_discovery(uint8_t square) {
    return discovery[square];
}
#endif
#ifdef AI_LOCAL_EXCHANGES
int16_t ai_test_reply(uint8_t from, uint8_t to) {
    return reply_penalty(from, to);
}
#endif
uint8_t ai_test_quiet(uint8_t army) {
    return quiet_turns[army ? 1 : 0];
}
/* Test-only snapshots let hidden-layout comparisons start from identical
 * persistent goals and histories. This code is absent from game builds. */
void ai_test_save(uint8_t* out) {
#ifdef AI_MEMORY
#ifdef AI_BELIEF_PRIORS
    ai_memory_save(out + AI_TEST_PRIOR_OFFSET - AI_MEMORY_STATE_SIZE);
#else
    ai_memory_save(out + AI_TEST_STATE_SIZE - AI_MEMORY_STATE_SIZE);
#endif
#endif
    memcpy(out, goals, sizeof(goals));
    memcpy(out + sizeof(goals), last_from, sizeof(last_from));
    memcpy(out + sizeof(goals) + sizeof(last_from), last_to, sizeof(last_to));
    memcpy(out + 204, quiet_turns, sizeof(quiet_turns));
    memcpy(out + 206, previous_count, sizeof(previous_count));
#ifdef AI_MISSIONS
    ai_mission_save(out + 208);
#endif
#ifdef AI_BELIEF_PRIORS
    out[AI_TEST_PRIOR_OFFSET]=belief_owner;
    memcpy(out+AI_TEST_PRIOR_OFFSET+1,belief_flag,sizeof(belief_flag));
    memcpy(out+AI_TEST_PRIOR_OFFSET+1+sizeof(belief_flag),belief_bomb,sizeof(belief_bomb));
#endif
}
void ai_test_load(const uint8_t* in) {
#ifdef AI_MEMORY
#ifdef AI_BELIEF_PRIORS
    ai_memory_load(in + AI_TEST_PRIOR_OFFSET - AI_MEMORY_STATE_SIZE);
#else
    ai_memory_load(in + AI_TEST_STATE_SIZE - AI_MEMORY_STATE_SIZE);
#endif
#endif
    memcpy(goals, in, sizeof(goals));
    memcpy(last_from, in + sizeof(goals), sizeof(last_from));
    memcpy(last_to, in + sizeof(goals) + sizeof(last_from), sizeof(last_to));
    memcpy(quiet_turns, in + 204, sizeof(quiet_turns));
    memcpy(previous_count, in + 206, sizeof(previous_count));
#ifdef AI_MISSIONS
    ai_mission_load(in + 208);
#endif
#ifdef AI_BELIEF_PRIORS
    belief_owner=in[AI_TEST_PRIOR_OFFSET];
    memcpy(belief_flag,in+AI_TEST_PRIOR_OFFSET+1,sizeof(belief_flag));
    memcpy(belief_bomb,in+AI_TEST_PRIOR_OFFSET+1+sizeof(belief_flag),sizeof(belief_bomb));
#endif
}
#endif
