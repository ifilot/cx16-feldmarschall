/* Tactical regressions and legal, non-mutating decisions across rule variants. */
#include <stdio.h>
#include <string.h>
#include "ai.h"
#include "board.h"
#include "rules.h"
#include "setup.h"
#include "random.h"

static int failures;
#define CHECK(c, message) do { if(!(c)) { printf("FAIL level %u move %u->%u: %s\n", ai_difficulty, from, to, message); failures++; } } while(0)
static uint8_t lost[PIECE_TYPES], from, to;

static void fresh(void) {
    board_clear(); rules_reset(); ai_reset(); game_rules = 0;
    memcpy(lost, piece_counts, sizeof(lost));
}

static void decide(uint16_t seed) {
    random_seed(seed);
    ai_move(0, lost, &from, &to);
}

static void tactical(void) {
    uint16_t seed;
    for(seed=1; seed<=32; seed++) {
        fresh();
        board[60] = PIECE_SCOUT; board[50] = PIECE_FLAG | CELL_BLUE | CELL_REVEALED;
        board[70] = PIECE_MARSHAL; board[71] = PIECE_GENERAL | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_FLAG]--; lost[PIECE_GENERAL]--;
        decide(seed);
        CHECK(from == 60 && to == 50, "capture flag before material or positional improvements");

        fresh();
        board[60] = PIECE_SPY; board[50] = PIECE_MARSHAL | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_MARSHAL]--;
        decide(seed);
        CHECK(from == 60 && to == 50, "spy takes revealed marshal");

        fresh();
        board[60] = PIECE_MINER; board[50] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_BOMB]--;
        decide(seed);
        CHECK(ai_difficulty == AI_EASY || (from == 60 && to == 50), "miner clears known bomb");

        fresh();
        board[65] = PIECE_SPY; board[5] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT]--;
        decide(seed);
        CHECK(ai_difficulty == AI_EASY || (from == 65 && (to == 64 || to == 66)), "spy leaves an unobstructed scout ray");

        fresh();
        /* Going sideways is the shortest usable path around the west lake. */
        board[62] = PIECE_MARSHAL; board[32] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT]--;
        decide(seed);
        CHECK(ai_difficulty == AI_EASY || (from == 62 && to == 61), "route follows the passage around a lake");

        fresh();
        /* Taking the general would vacate the only blocker on the flag ray. */
        board[65] = PIECE_MARSHAL; board[95] = PIECE_FLAG;
        board[5] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        board[64] = PIECE_GENERAL | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT]--; lost[PIECE_GENERAL]--;
        decide(seed);
        CHECK(from == 65 && (to == 55 || (ai_difficulty == AI_EASY && to == 75)), "keep a scout ray to our flag blocked instead of taking material");

        fresh();
        board[80] = PIECE_MARSHAL; board[91] = PIECE_FLAG;
        board[90] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        board[70] = PIECE_GENERAL | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT]--; lost[PIECE_GENERAL]--;
        decide(seed);
        CHECK(from == 80 && to == 90, "respond to an immediate threat beside our flag");
    }
}

static unsigned private_inventory_checks;
static uint16_t secret_ranks_checked;

static void reply_tactic(void) {
    uint16_t seed;
    uint8_t level, normal_captures = 0;
    for(seed=1; seed<=32; seed++) for(level=AI_NORMAL; level<=AI_HARD; level++) {
        ai_difficulty = level; fresh();
        board[60] = PIECE_MARSHAL; board[80] = PIECE_SPY; board[99] = PIECE_FLAG;
        board[40] = board[61] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT] -= 2;
        decide(seed);
        if(level == AI_NORMAL && from == 60 && to == 61) normal_captures++;
        CHECK(level != AI_HARD || !(from == 60 && to == 61),
              "Hard checks the reply exposing its spy before taking a scout");
    }
    CHECK(normal_captures > 0, "reply fixture distinguishes Hard from Normal despite score jitter");
}

/* Shuffle identities separately among unmoved and moved concealed pieces,
 * keeping every public bit and the rank inventory unchanged. */
static void shuffle_hidden(uint8_t army, uint8_t moved) {
    uint8_t slots[SQUARES], count = 0, sq, cell, i, a, b, type;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(IS_PIECE(cell) && (cell & CELL_BLUE) != army && !(cell & CELL_REVEALED) &&
           !!(cell & CELL_MOVED) == moved) slots[count++] = sq;
    }
    for(i=0; i<count/2; i++) {
        a = slots[i]; b = slots[count-1-i]; type = PIECE_TYPE(board[a]);
        if(type != PIECE_TYPE(board[b])) secret_ranks_checked |= (1 << type) | (1 << PIECE_TYPE(board[b]));
        board[a] = (board[a] & ~CELL_TYPE) | PIECE_TYPE(board[b]);
        board[b] = (board[b] & ~CELL_TYPE) | type;
    }
}

static unsigned fair_decisions;
static void fair_decide(uint8_t army, uint8_t* observed, uint16_t seed) {
    uint8_t truth[SQUARES], view[SQUARES], before[AI_TEST_STATE_SIZE], after[AI_TEST_STATE_SIZE], other[AI_TEST_STATE_SIZE];
    uint8_t first_from, first_to, enemy = army ? 0 : 1, sq, t, cell;
    uint8_t secret_lost[PIECE_TYPES];
    uint16_t next;
    memcpy(truth, board, SQUARES);
    ai_test_save(before);
    ai_mask(army);
    memcpy(view, board, SQUARES);
    random_seed(seed);
    ai_move(army, observed, &first_from, &first_to);
    next = random_next();
    ai_test_save(after);
    CHECK(!memcmp(view, board, SQUARES), "AI restores its view after hypothetical checks");
    memcpy(board, truth, SQUARES);
    shuffle_hidden(army, 0); shuffle_hidden(army, 1);
    memcpy(secret_lost, rules_lost[enemy], sizeof(secret_lost));
    if(game_rules & RULE_SILENT) {
        /* Exchange an undisclosed casualty with an unmoved hidden piece.
         * This changes the true remaining inventory, but not public knowledge. */
        for(t=0; t<PIECE_TYPES; t++) {
            if(t == PIECE_FLAG || rules_lost[enemy][t] <= rules_known_lost[enemy][t]) continue;
            for(sq=0; sq<SQUARES; sq++) {
                cell = board[sq];
                if(IS_PIECE(cell) && (cell & CELL_BLUE) != army &&
                   !(cell & (CELL_REVEALED | CELL_MOVED)) && PIECE_TYPE(cell) != PIECE_FLAG && PIECE_TYPE(cell) != t) {
                    rules_lost[enemy][t]--;
                    rules_lost[enemy][PIECE_TYPE(cell)]++;
                    board[sq] = (cell & ~CELL_TYPE) | t;
                    private_inventory_checks++;
                    break;
                }
            }
            break;
        }
    }
    ai_mask(army);
    CHECK(!memcmp(view, board, SQUARES), "all secret permutations produce the same public view");
    ai_test_load(before); random_seed(seed);
    ai_move(army, observed, &from, &to);
    ai_test_save(other);
    CHECK(from == first_from && to == first_to, "secret identities cannot change a decision at any difficulty");
    CHECK(next == random_next() && !memcmp(after, other, sizeof(after)),
          "secret identities cannot change random consumption, goals or histories");
    CHECK(!memcmp(view, board, SQUARES), "comparison restores its public board");
    memcpy(board, truth, SQUARES);
    memcpy(rules_lost[enemy], secret_lost, sizeof(secret_lost));
    ai_test_load(after);
    fair_decisions++;
}

static void variants(void) {
    uint8_t mask, turn, army, options[MAX_TARGETS], n, i;
    uint8_t observed[PIECE_TYPES];
    for(mask=0; mask<64; mask++) {
        fresh(); game_rules = mask; random_seed(1234 + mask);
        setup_random(0); setup_random(1);
        for(turn=0; turn<80; turn++) {
            army = turn & 1 ? CELL_BLUE : 0;
            memcpy(observed, rules_known_lost[army ? 0 : 1], sizeof(observed));
            fair_decide(army, observed, (uint16_t)mask*100 + turn + 1);
            if(from == NOWHERE) {
                CHECK(!rules_has_move(army != 0), "no move only when that side is stuck");
                break;
            }
            CHECK(from < SQUARES && to < SQUARES && (board[from] & CELL_BLUE) == army,
                  "AI selects its own piece");
            n = rules_targets(from, options);
            for(i=0; i<n && options[i] != to; i++) {}
            CHECK(i < n, "chosen move is legal under current combined variants and repetition state");
            if(i == n) break;
            if(PIECE_TYPE(board[to]) == PIECE_FLAG && IS_PIECE(board[to])) break;
            rules_apply(from, to);
            if(rules_flag_arrived(to)) break;
        }
    }
}

int main(void) {
    uint8_t level;
    for(level=0; level<AI_LEVELS; level++) {
        ai_difficulty = level;
        tactical();
        variants();
    }
    reply_tactic();
    CHECK(private_inventory_checks > 0, "silent casualties were tested with different true rank inventories");
    CHECK((secret_ranks_checked & ((1 << PIECE_SPY) | (1 << PIECE_MARSHAL) | (1 << PIECE_FLAG))) ==
          ((1 << PIECE_SPY) | (1 << PIECE_MARSHAL) | (1 << PIECE_FLAG)), "Spy, Marshal and Flag identities were each permuted");
    printf("AI: %s; %u hidden-permutation decisions across all levels and 64 rule combinations\n", failures ? "FAILED" : "passed", fair_decisions);
    printf("%u Silent Defense private-inventory comparisons; Spy, Marshal and Flag included\n", private_inventory_checks);
    return failures != 0;
}
