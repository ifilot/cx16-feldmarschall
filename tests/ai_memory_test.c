/* Public-history identities and rank constraints, including silent battles. */
#include <stdio.h>
#include <string.h>
#include "ai.h"
#include "ai_memory.h"
#include "board.h"
#include "rules.h"

static unsigned checks, failures;
#define CHECK(condition) do { checks++; if(!(condition)) { printf("FAIL line %u\n", (unsigned)__LINE__); failures++; } } while(0)

static void fresh(void) { board_clear(); rules_reset(); game_rules = 0; ai_reset(); }

static void identity(void) {
    uint8_t id, other;
    const ai_piece_history_t* piece;
    fresh(); board[60] = PIECE_SCOUT; board[30] = PIECE_UNKNOWN | CELL_BLUE;
    ai_memory_sync(); id = ai_memory_identity(60); other = ai_memory_identity(30);
    CHECK(id != other && id != NOWHERE);
    CHECK(ai_memory_history(id)->known_rank == PIECE_UNKNOWN); /* private rank is not public */
    rules_apply(60, 50);
    CHECK(ai_memory_identity(50) == id && ai_memory_identity(60) == NOWHERE);
    piece = ai_memory_history(id);
    CHECK(piece->origin == 60 && piece->moves == 1 && piece->known_rank == PIECE_UNKNOWN);
    CHECK(!(piece->candidates & ((uint16_t)1 << PIECE_BOMB)));
    rules_apply(50, 20);
    CHECK(ai_memory_identity(20) == id && ai_memory_history(id)->known_rank == PIECE_SCOUT);
    rules_apply(20, 10);
    CHECK(ai_memory_history(id)->moves == 3 && ai_memory_history(id)->known_rank == PIECE_SCOUT);
}

static void combat(void) {
    uint8_t attacker, defender, mask;
    uint16_t candidates;
    for(mask=0; mask<64; mask++) {
        fresh(); game_rules = mask;
        board[60] = PIECE_MARSHAL; board[50] = PIECE_BOMB | CELL_BLUE;
        ai_memory_sync(); attacker = ai_memory_identity(60); defender = ai_memory_identity(50);
        rules_apply(60, 50);
        CHECK(ai_memory_history(attacker)->battles == 1 && ai_memory_history(defender)->battles == 1);
        CHECK(ai_memory_history(attacker)->known_rank == PIECE_MARSHAL);
        candidates = ai_memory_history(defender)->candidates;
        CHECK(candidates & ((uint16_t)1 << PIECE_BOMB));
        CHECK(ai_memory_history(attacker)->square == NOWHERE);
        if(mask & (RULE_EXPLODING | RULE_MOVING_BOMBS)) CHECK(ai_memory_identity(50) == NOWHERE);
        else CHECK(ai_memory_identity(50) == defender);
        if(!(mask & RULE_SILENT)) CHECK(ai_memory_history(defender)->known_rank == PIECE_BOMB);
    }
    fresh(); game_rules = RULE_SILENT;
    board[60] = PIECE_CAPTAIN; board[50] = PIECE_GENERAL | CELL_BLUE;
    ai_memory_sync(); defender = ai_memory_identity(50); rules_apply(60, 50);
    CHECK(ai_memory_history(defender)->known_rank == PIECE_UNKNOWN);
    CHECK(ai_memory_history(defender)->candidates & ((uint16_t)1 << PIECE_MARSHAL));
    CHECK(ai_memory_history(defender)->candidates & ((uint16_t)1 << PIECE_GENERAL));
    CHECK(!(ai_memory_history(defender)->candidates & ((uint16_t)1 << PIECE_SCOUT)));
}

static void privacy(void) {
    uint8_t state[AI_MEMORY_STATE_SIZE], other[AI_MEMORY_STATE_SIZE], rank;
    fresh(); board[60] = PIECE_MARSHAL; board[50] = PIECE_GENERAL | CELL_BLUE;
    ai_memory_sync(); ai_memory_save(state);
    for(rank=0; rank<PIECE_TYPES; rank++) {
        fresh(); board[60] = rank; board[50] = (PIECE_TYPES-1-rank) | CELL_BLUE;
        ai_memory_sync(); ai_memory_save(other);
        CHECK(!memcmp(state, other, sizeof(state)));
    }
}

static void silent_outcome_privacy(void) {
    uint8_t states[3][AI_MEMORY_STATE_SIZE], present[3], attacker, defender, mask, outcome;
    uint8_t current[AI_MEMORY_STATE_SIZE], identity;
    for(mask=0; mask<64; mask++) {
        if(!(mask & RULE_SILENT)) continue;
        for(attacker=0; attacker<PIECE_BOMB; attacker++) {
            if(attacker == PIECE_SCOUT) continue; /* scouts disclose the defender */
            memset(present, 0, sizeof(present));
            for(defender=0; defender<PIECE_TYPES; defender++) {
                fresh(); game_rules = mask;
                board[60] = attacker; board[50] = defender | CELL_BLUE;
                ai_memory_sync(); identity = ai_memory_identity(50);
                outcome = rules_apply(60, 50); ai_memory_save(current);
                CHECK(ai_memory_history(identity)->candidates & ((uint16_t)1 << defender));
                if(present[outcome]) CHECK(!memcmp(states[outcome], current, sizeof(current)));
                else { memcpy(states[outcome], current, sizeof(current)); present[outcome] = 1; }
            }
        }
    }
}

static void encounters(void) {
    uint8_t id, prior[PIECE_TYPES], snapshot[AI_TEST_STATE_SIZE];
    uint16_t stronger, weaker;
    fresh(); board[60] = PIECE_SERGEANT; board[51] = PIECE_CAPTAIN | CELL_BLUE | CELL_REVEALED;
    memset(prior, 1, sizeof(prior)); ai_memory_sync(); id = ai_memory_identity(60);
    rules_apply(60, 50);
    CHECK(ai_memory_history(id)->approach_rank == PIECE_CAPTAIN);
    stronger = ai_memory_weight(50, PIECE_GENERAL, prior);
    weaker = ai_memory_weight(50, PIECE_SCOUT, prior);
    CHECK(stronger > weaker && weaker > 0); /* a bluff remains possible */
    rules_apply(50, 40);
    CHECK(ai_memory_history(id)->retreat_rank == PIECE_CAPTAIN);
    ai_test_save(snapshot); ai_reset(); ai_test_load(snapshot);
    CHECK(ai_memory_identity(40) == id && ai_memory_history(id)->moves == 2);
    CHECK(ai_memory_history(id)->approach_rank == PIECE_CAPTAIN);
    CHECK(ai_memory_history(id)->retreat_rank == PIECE_CAPTAIN);
}

static void saturation_and_rescue(void) {
    static const uint8_t loop[4] = {60, 50, 51, 61};
    uint8_t id, newcomer;
    unsigned i;
    fresh(); board[60] = PIECE_CAPTAIN;
    ai_memory_sync(); id = ai_memory_identity(60);
    for(i=0; i<300; i++) rules_apply(loop[i%4], loop[(i+1)%4]);
    CHECK(ai_memory_history(id)->moves == 255);
    CHECK(ai_memory_identity(60) == id);
    board[70] = PIECE_SERGEANT | CELL_REVEALED; /* a newly rescued piece */
    ai_memory_sync(); newcomer = ai_memory_identity(70);
    CHECK(newcomer != id && ai_memory_history(newcomer)->moves == 0);
    CHECK(ai_memory_history(newcomer)->known_rank == PIECE_SERGEANT);
}

int main(void) {
    CHECK(sizeof(ai_piece_history_t) == 10);
    identity(); combat(); privacy(); silent_outcome_privacy(); encounters(); saturation_and_rescue();
    printf("AI memory: %u checks, %u failures\n", checks, failures);
    return failures != 0;
}
