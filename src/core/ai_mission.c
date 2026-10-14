/* Cooperative miner approach, scouting and route clearing.
 * Enemy input is always the caller's masked view, never the true layout. */
#ifdef AI_MISSIONS
#pragma static-locals (on)
#include <string.h>
#include "ai_mission.h"
#include "board.h"
#include "rules.h"
#ifdef BANKED_AI
#pragma code-name ("MISSIONCODE")
#pragma rodata-name ("MISSIONRODATA")
#pragma bss-name ("MISSIONBSS")
#define ai_mission_begin ai_mission_begin_banked
#define ai_mission_score ai_mission_score_banked
#define ai_mission_reset ai_mission_reset_banked
#endif

static uint8_t own, remembered[2];
#ifdef AI_SECTOR_MEMORY
/* Spatial hypotheses from public guard sightings, not concealed identities. */
static uint8_t sector[2][10];
#endif
static uint8_t leader, actor, objective, vacate;
static uint8_t distance[SQUARES], queue[SQUARES], corridor[SQUARES];

static uint8_t enemy(uint8_t cell) {
    return IS_PIECE(cell) && (cell & CELL_BLUE) != own;
}

static uint8_t neighbor(uint8_t sq, uint8_t dir) {
    static const int8_t step[4] = {-10, 1, 10, -1};
    uint8_t nb = sq + step[dir];
    if(nb >= SQUARES || (dir == 1 && sq % 10 == 9) ||
       (dir == 3 && sq % 10 == 0) || board[nb] == CELL_LAKE) return NOWHERE;
    return nb;
}

static uint8_t immobile(uint8_t cell) {
    return (PIECE_TYPE(cell) == PIECE_BOMB && !(game_rules & RULE_MOVING_BOMBS)) ||
           (PIECE_TYPE(cell) == PIECE_FLAG && !(game_rules & RULE_MOVING_FLAG));
}

static uint8_t rear(uint8_t sq) {
    return own ? sq >= 80 : sq < 20;
}

/* Relaxed routes can contain future jobs. Strict routes allow occupied
 * endpoints, but never transit through another piece. */
static void flood(uint8_t goal, uint8_t relaxed) {
    uint8_t head = 0, tail = 0, sq, nb, dir, cell;
    memset(distance, NOWHERE, sizeof(distance));
    distance[goal] = 0; queue[tail++] = goal;
    while(head < tail) {
        sq = queue[head++]; cell = board[sq];
        if(sq != goal && IS_PIECE(cell) &&
           (!relaxed || (!enemy(cell) && immobile(cell)))) continue;
        for(dir=0; dir<4; dir++) {
            nb = neighbor(sq, dir);
            if(nb == NOWHERE || distance[nb] != NOWHERE) continue;
            distance[nb] = distance[sq] + 1;
            queue[tail++] = nb;
        }
    }
}

/* Choose a lead miner; a scout can investigate a target when no miner remains.
 * Other mobile pieces can pursue a disclosed flag, subject to tactical safety. */
static uint8_t choose_leader(uint8_t flag) {
    uint8_t sq, cell, best = NOWHERE, best_cost = 255, cost;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!IS_PIECE(cell) || enemy(cell) || PIECE_TYPE(cell) >= PIECE_BOMB ||
           distance[sq] == NOWHERE) continue;
        cost = distance[sq];
        if(PIECE_TYPE(cell) != PIECE_MINER) {
            if(!flag && PIECE_TYPE(cell) != PIECE_SCOUT) continue;
            cost += 100;
        }
        if(cost < best_cost) { best = sq; best_cost = cost; }
    }
    return best;
}

void ai_mission_reset(void) {
    remembered[0] = remembered[1] = NOWHERE;
#ifdef AI_SECTOR_MEMORY
    memset(sector, 0, sizeof(sector));
#endif
}

void ai_mission_begin(uint8_t army) {
    uint8_t sq, cell, goal = NOWHERE, lead = NOWHERE, candidate, flag, dir, nb;
    uint8_t walk, obstacle = NOWHERE, type, best_actor = NOWHERE;
    int16_t value, best = -32767, cost, best_cost = 32767;
    own = army; leader = actor = objective = NOWHERE; vacate = 0;
    memset(corridor, 0, sizeof(corridor));
#ifdef AI_SECTOR_MEMORY
    /* Discard a hypothesis when public movement or disclosure contradicts it. */
    for(sq=0; sq<10; sq++) {
        cell = board[own ? 90+sq : sq];
        if(!enemy(cell) || (cell & CELL_MOVED) ||
           ((cell & CELL_REVEALED) && PIECE_TYPE(cell) != PIECE_FLAG))
            sector[own ? 1 : 0][sq] = 0;
    }
#endif
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!enemy(cell)) continue;
        flag = (cell & CELL_REVEALED) && PIECE_TYPE(cell) == PIECE_FLAG;
        if(flag) value = 1000;
        else if((cell & CELL_REVEALED) && PIECE_TYPE(cell) == PIECE_BOMB && rear(sq)) value = 80;
        else if(!(cell & (CELL_REVEALED | CELL_MOVED)) &&
                ((own && sq >= 90) || (!own && sq < 10))) {
            /* A guessed flag sector needs observable evidence of fortification.
             * Merely being on the back row does not justify an army mission. */
            value = 0;
            for(dir=0; dir<4; dir++) {
                nb = neighbor(sq, dir);
                if(nb != NOWHERE && enemy(board[nb]) && (board[nb] & CELL_REVEALED) &&
                   PIECE_TYPE(board[nb]) == PIECE_BOMB) value += 30;
            }
#ifdef AI_SECTOR_MEMORY
            if(value) sector[own ? 1 : 0][sq % 10] = 1;
            else if(sector[own ? 1 : 0][sq % 10]) value = 30;
#endif
            if(!value) continue;
            value += 40;
        }
        else continue;
        flood(sq, 1);
        candidate = choose_leader(flag);
        if(candidate == NOWHERE) continue;
        value -= (int16_t)distance[candidate] * 3;
        if(sq == remembered[own ? 1 : 0]) value += 12;
        if(value > best) { best = value; goal = sq; lead = candidate; }
    }
    remembered[own ? 1 : 0] = goal;
    if(goal == NOWHERE) return;
    leader = lead;
    flood(goal, 1);
    walk = lead;
    /* The corridor identifies cooperation jobs, not a legal multi-move attack. */
    while(walk != goal) {
        corridor[walk] = 1;
        for(dir=0; dir<4; dir++) {
            nb = neighbor(walk, dir);
            if(nb != NOWHERE && distance[nb] + 1 == distance[walk] &&
               !(IS_PIECE(board[nb]) && !enemy(board[nb]) && immobile(board[nb]))) break;
        }
        if(dir == 4) return;
        walk = nb;
        if(obstacle == NOWHERE && IS_PIECE(board[walk])) obstacle = walk;
    }
    corridor[goal] = 1;
    if(obstacle == NOWHERE) return;
    cell = board[obstacle];
    if(!enemy(cell)) {
        if(immobile(cell)) return;
        actor = obstacle; vacate = 1; return;
    }
    objective = obstacle;
    flood(objective, 0);
    if(!(cell & CELL_REVEALED)) {
        for(sq=0; sq<SQUARES; sq++) {
            if(IS_PIECE(board[sq]) && !enemy(board[sq]) &&
               PIECE_TYPE(board[sq]) == PIECE_SCOUT && distance[sq] != NOWHERE &&
               distance[sq] < best_cost) {
                best_cost = distance[sq]; best_actor = sq;
            }
        }
        actor = best_actor == NOWHERE ? lead : best_actor;
    } else {
        for(sq=0; sq<SQUARES; sq++) {
            type = PIECE_TYPE(board[sq]);
            if(!IS_PIECE(board[sq]) || enemy(board[sq]) || type >= PIECE_BOMB ||
               distance[sq] == NOWHERE || rules_battle(type, PIECE_TYPE(cell)) != BATTLE_ATTACKER) continue;
            cost = (int16_t)distance[sq] * 4 + (type == PIECE_SPY ? 30 : (10-type) * 3);
            if(cost < best_cost) { best_cost = cost; best_actor = sq; }
        }
        actor = best_actor;
    }
}

int16_t ai_mission_score(uint8_t from, uint8_t to) {
    if(from != actor) return 0;
    if(vacate) return board[to] == CELL_EMPTY && !corridor[to] ? 36 : 0;
    if(to == objective) return 30;
    if(distance[from] != NOWHERE && distance[to] != NOWHERE && distance[to] < distance[from])
        return 20 + ((int16_t)distance[from] - distance[to]) * 10;
    return 0;
}

#ifdef AI_TEST
void ai_mission_save(uint8_t* out) {
    memcpy(out, remembered, 2);
#ifdef AI_SECTOR_MEMORY
    memcpy(out + 2, sector, sizeof(sector));
#endif
}
void ai_mission_load(const uint8_t* in) {
    memcpy(remembered, in, 2);
#ifdef AI_SECTOR_MEMORY
    memcpy(sector, in + 2, sizeof(sector));
#endif
}
uint8_t ai_mission_test_target(uint8_t army) { return remembered[army ? 1 : 0]; }
#endif
#endif
