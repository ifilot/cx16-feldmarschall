/* Cooperative miner approach, scouting and route clearing.
 * Enemy input is always the caller's masked view, never the true layout. */
#ifdef AI_MISSIONS
#pragma static-locals (on)
#include <string.h>
#include "ai_mission.h"
#include "board.h"
#include "rules.h"
#ifdef AI_STUDENT
#include "ai_student.h"
#endif
#ifdef AI_MEMORY
#include "ai_memory.h"
#ifdef BANKED_AI
void ai_memory_reset_banked(void);
#endif
#endif
#ifdef BANKED_AI
#pragma code-name ("MISSIONCODE")
#pragma rodata-name ("MISSIONRODATA")
#pragma bss-name ("MISSIONBSS")
#define ai_mission_begin ai_mission_begin_banked
#define ai_mission_score ai_mission_score_banked
#define ai_mission_reset ai_mission_reset_banked
#endif

static uint8_t own, remembered[2];
#ifdef AI_MISSION_PROGRESS
static uint8_t best_work[2], stalled[2], progress_count[2], progress_job[2];
#ifdef AI_SECTOR_MEMORY
#define PROGRESS_STATE_OFFSET 22
#else
#define PROGRESS_STATE_OFFSET 2
#endif
#endif
#ifdef AI_SECTOR_MEMORY
/* Spatial hypotheses from public guard sightings, not concealed identities. */
static uint8_t sector[2][10];
#endif
static uint8_t leader, actor, objective, vacate;
#ifdef AI_MISSION_SCOUT_VALUE
static uint8_t concealed_left;
#endif
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

#ifdef AI_MISSION_EVIDENCE
static uint8_t supported_guard(uint8_t sq) {
    uint8_t dir, nb, cell;
    if(game_rules & RULE_MOVING_FLAG) return 1;
    for(dir=0; dir<4; dir++) {
        nb = neighbor(sq, dir);
        if(nb == NOWHERE) continue;
        cell = board[nb];
        if(enemy(cell) && (((cell & CELL_REVEALED) && PIECE_TYPE(cell) == PIECE_FLAG) ||
                           !(cell & (CELL_REVEALED | CELL_MOVED)))) return 1;
    }
    return 0;
}
#endif

#ifdef AI_MISSION_PRESERVE
static uint8_t preserve_miner(void) {
    uint8_t sq, cell, miners = 0, bombs = 0;
    if(game_rules) return 0;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!IS_PIECE(cell)) continue;
        if(!enemy(cell) && PIECE_TYPE(cell) == PIECE_MINER) miners++;
        if(enemy(cell) && (cell & CELL_REVEALED) && PIECE_TYPE(cell) == PIECE_BOMB) bombs++;
    }
    return miners == 1 && bombs;
}
#endif

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
#ifdef AI_MEMORY
#ifdef BANKED_AI
    ai_memory_reset_banked();
#else
    ai_memory_reset();
#endif
#endif
    remembered[0] = remembered[1] = NOWHERE;
#ifdef AI_MISSION_PROGRESS
    memset(best_work, NOWHERE, sizeof(best_work));
    memset(stalled, 0, sizeof(stalled));
    memset(progress_count, 0, sizeof(progress_count));
    memset(progress_job, NOWHERE, sizeof(progress_job));
#endif
#ifdef AI_SECTOR_MEMORY
    memset(sector, 0, sizeof(sector));
#endif
}

void ai_mission_begin(uint8_t army) {
    uint8_t sq, cell, goal = NOWHERE, lead = NOWHERE, candidate, flag, dir, nb;
    uint8_t walk, obstacle = NOWHERE, type, best_actor = NOWHERE;
    int16_t value, best = -32767, cost, best_cost = 32767;
#ifdef AI_MISSION_PROGRESS
    uint8_t count = 0, work, index;
    index = army ? 1 : 0;
#endif
    own = army; leader = actor = objective = NOWHERE; vacate = 0;
#ifdef AI_MISSION_SCOUT_VALUE
    concealed_left = 0;
#endif
#ifdef AI_STUDENT
    ai_student_begin(army);
#endif
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
#ifdef AI_MISSION_SCOUT_VALUE
        if(enemy(cell) && !(cell & CELL_REVEALED)) concealed_left++;
#endif
#ifdef AI_MISSION_PROGRESS
        if(IS_PIECE(cell)) count++;
#endif
        if(!enemy(cell)) continue;
        flag = (cell & CELL_REVEALED) && PIECE_TYPE(cell) == PIECE_FLAG;
        if(flag) value = 1000;
        else if((cell & CELL_REVEALED) && PIECE_TYPE(cell) == PIECE_BOMB && rear(sq)) {
#ifdef AI_MISSION_EVIDENCE
            /* A disclosed rear bomb with no adjacent public flag candidate is
             * a route obstacle, not evidence of a guarded flag at this square. */
            if(!supported_guard(sq)) continue;
#endif
            value = 80;
        }
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
        if(sq == remembered[own ? 1 : 0]) {
#ifdef AI_MISSION_PROGRESS
            if(stalled[index] < 12) value += 12;
            else value -= (int16_t)(stalled[index] > 36 ? 36 : stalled[index]) * 2;
#else
            value += 12;
#endif
        }
        if(value > best) { best = value; goal = sq; lead = candidate; }
    }
    remembered[own ? 1 : 0] = goal;
    if(goal == NOWHERE) {
#ifdef AI_MISSION_PROGRESS
        best_work[index] = NOWHERE; stalled[index] = 0; progress_count[index] = count;
        progress_job[index] = NOWHERE;
#endif
        return;
    }
    leader = lead;
    flood(goal, 1);
    walk = lead;
#ifdef AI_MISSION_PROGRESS
    work = distance[lead];
#endif
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
#ifdef AI_MISSION_PROGRESS
        if(IS_PIECE(board[walk])) work++;
#endif
        if(obstacle == NOWHERE && IS_PIECE(board[walk])) obstacle = walk;
    }
    corridor[goal] = 1;
#ifdef AI_MISSION_PROGRESS
    /* Remaining route length plus occupied corridor squares counts both leader
     * advances and support clearing. It uses only the permitted board. */
    /* Switching between a guard and its adjacent suspected flag is still the
     * same cooperation job when the first obstacle has not changed. */
    if(obstacle != progress_job[index] || count != progress_count[index] || work < best_work[index]) {
        best_work[index] = work; stalled[index] = 0;
    } else if(stalled[index] != 255) stalled[index]++;
    progress_count[index] = count;
    progress_job[index] = obstacle;
#endif
    if(obstacle == NOWHERE) return;
    cell = board[obstacle];
    if(!enemy(cell)) {
        if(immobile(cell)) return;
        actor = obstacle; vacate = 1; return;
    }
    objective = obstacle;
#ifdef AI_MISSION_ESCORT
    /* Clear a disclosed recapture threat beside a bomb before committing the
     * lead miner. Only assign this job if another piece can win that combat. */
    if(!game_rules && (cell & CELL_REVEALED) && PIECE_TYPE(cell) == PIECE_BOMB) {
        for(dir=0; dir<4; dir++) {
            nb = neighbor(obstacle, dir);
            if(nb == NOWHERE || !enemy(board[nb]) || !(board[nb] & CELL_REVEALED) ||
               PIECE_TYPE(board[nb]) >= PIECE_BOMB ||
               rules_battle(PIECE_TYPE(board[nb]), PIECE_MINER) == BATTLE_DEFENDER) continue;
            flood(nb, 0);
            for(sq=0; sq<SQUARES; sq++) {
                type = PIECE_TYPE(board[sq]);
                if(IS_PIECE(board[sq]) && !enemy(board[sq]) && type < PIECE_BOMB &&
                   type != PIECE_MINER && distance[sq] != NOWHERE &&
                   rules_battle(type, PIECE_TYPE(board[nb])) == BATTLE_ATTACKER) break;
            }
            if(sq != SQUARES) { objective = nb; cell = board[nb]; break; }
        }
    }
#endif
    flood(objective, 0);
    if(!(cell & CELL_REVEALED)) {
        for(sq=0; sq<SQUARES; sq++) {
            if(IS_PIECE(board[sq]) && !enemy(board[sq]) &&
               PIECE_TYPE(board[sq]) == PIECE_SCOUT && distance[sq] != NOWHERE &&
               distance[sq] < best_cost) {
                best_cost = distance[sq]; best_actor = sq;
            }
        }
#ifdef AI_MISSION_PRESERVE
        if(best_actor == NOWHERE && preserve_miner()) {
            for(sq=0; sq<SQUARES; sq++) {
                type = PIECE_TYPE(board[sq]);
                if(!IS_PIECE(board[sq]) || enemy(board[sq]) || type >= PIECE_BOMB ||
                   type == PIECE_MINER || distance[sq] == NOWHERE) continue;
                cost = (int16_t)distance[sq] * 4 + (type == PIECE_SPY ? 30 : (10-type) * 3);
                if(cost < best_cost) { best_cost = cost; best_actor = sq; }
            }
        }
#endif
        actor = best_actor == NOWHERE ? lead : best_actor;
    } else {
        for(sq=0; sq<SQUARES; sq++) {
            type = PIECE_TYPE(board[sq]);
            if(!IS_PIECE(board[sq]) || enemy(board[sq]) || type >= PIECE_BOMB ||
               distance[sq] == NOWHERE || rules_battle(type, PIECE_TYPE(cell)) != BATTLE_ATTACKER) continue;
            cost = (int16_t)distance[sq] * 4 + (type == PIECE_SPY ? 30 : (10-type) * 3);
#ifdef AI_MISSION_PRESERVE
            if(type == PIECE_MINER && PIECE_TYPE(cell) != PIECE_BOMB && preserve_miner()) cost += 80;
#endif
            if(cost < best_cost) { best_cost = cost; best_actor = sq; }
        }
        actor = best_actor;
    }
}

#if defined(AI_STUDENT) || defined(AI_MISSION_SCOUT_VALUE)
static int16_t mission_base_score(uint8_t from, uint8_t to)
#else
int16_t ai_mission_score(uint8_t from, uint8_t to)
#endif
{
#ifdef AI_MISSION_PROGRESS
    if(stalled[own ? 1 : 0] >= 24) return 0;
#endif
    if(from != actor) return 0;
    if(vacate) return board[to] == CELL_EMPTY && !corridor[to] ? 36 : 0;
    if(to == objective) return 30;
    if(distance[from] != NOWHERE && distance[to] != NOWHERE && distance[to] < distance[from])
        return 20 + ((int16_t)distance[from] - distance[to]) * 10;
    return 0;
}

#if defined(AI_STUDENT) || defined(AI_MISSION_SCOUT_VALUE)
int16_t ai_mission_score(uint8_t from, uint8_t to) {
    int16_t result = mission_base_score(from, to);
#ifdef AI_MISSION_SCOUT_VALUE
    /* Retain reconnaissance pieces while ranks remain concealed.
     * A loss against a disclosed defender buys no new rank information.
     * Immediate flag defence/victory still dominates in the tactical caller. */
    if(!game_rules && concealed_left &&
       PIECE_TYPE(board[from]) == PIECE_SCOUT && enemy(board[to]) &&
       (board[to] & CELL_REVEALED) &&
       rules_battle(PIECE_SCOUT, PIECE_TYPE(board[to])) == BATTLE_DEFENDER) result -= 24;
#endif
#ifdef AI_STUDENT
#ifdef AI_STUDENT_COOP_GUARD
    /* Rollout futures start cold. Preserve the assigned cooperation actor's
     * quiet priorities while learning other quiet moves and all captures. */
    if(from==actor && !IS_PIECE(board[to])) return result;
#endif
    result += ai_student_score(from, to);
#endif
    return result;
}
#endif

#ifdef AI_TEST
void ai_mission_save(uint8_t* out) {
    memcpy(out, remembered, 2);
#ifdef AI_MISSION_PROGRESS
    memcpy(out + PROGRESS_STATE_OFFSET, best_work, 2);
    memcpy(out + PROGRESS_STATE_OFFSET + 2, stalled, 2);
    memcpy(out + PROGRESS_STATE_OFFSET + 4, progress_count, 2);
    memcpy(out + PROGRESS_STATE_OFFSET + 6, progress_job, 2);
#endif
#ifdef AI_SECTOR_MEMORY
    memcpy(out + 2, sector, sizeof(sector));
#endif
}
void ai_mission_load(const uint8_t* in) {
    memcpy(remembered, in, 2);
#ifdef AI_MISSION_PROGRESS
    memcpy(best_work, in + PROGRESS_STATE_OFFSET, 2);
    memcpy(stalled, in + PROGRESS_STATE_OFFSET + 2, 2);
    memcpy(progress_count, in + PROGRESS_STATE_OFFSET + 4, 2);
    memcpy(progress_job, in + PROGRESS_STATE_OFFSET + 6, 2);
#endif
#ifdef AI_SECTOR_MEMORY
    memcpy(sector, in + 2, sizeof(sector));
#endif
}
uint8_t ai_mission_test_target(uint8_t army) { return remembered[army ? 1 : 0]; }
#ifdef AI_MISSION_PROGRESS
uint8_t ai_mission_test_stalled(uint8_t army) { return stalled[army ? 1 : 0]; }
#endif
#endif
#endif
